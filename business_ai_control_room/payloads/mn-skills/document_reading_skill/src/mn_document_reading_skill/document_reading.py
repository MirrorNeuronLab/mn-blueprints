from __future__ import annotations

import csv
import html
import json
import re
from io import StringIO
from pathlib import Path
from typing import Any


HEADING_PATTERN = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")


def detect_document_format(source_name: str | None = None, text: str | None = None) -> str:
    """Identify a common document format from a file name and/or text sample."""

    suffix = Path(source_name or "").suffix.lower().lstrip(".")
    if suffix in {"md", "markdown", "txt", "html", "htm", "csv", "json", "pdf", "docx"}:
        return "markdown" if suffix in {"md", "markdown"} else suffix

    sample = (text or "").lstrip()[:4000]
    lowered = sample.lower()
    if re.search(r"<\s*(html|body|article|section|p|h[1-6])\b", lowered):
        return "html"
    if sample.startswith(("{", "[")):
        return "json"
    if re.search(r"^\s*#{1,6}\s+\S+", sample, re.MULTILINE):
        return "markdown"
    if "," in sample and "\n" in sample:
        try:
            dialect = csv.Sniffer().sniff(sample)
            if dialect.delimiter:
                return "csv"
        except csv.Error:
            pass
    return "text"


def normalize_document_text(content: str | bytes, *, source_name: str | None = None) -> str:
    """Convert common document-like payloads into readable plain text."""

    if isinstance(content, bytes):
        text = content.decode("utf-8", errors="replace")
    else:
        text = str(content)

    text_format = detect_document_format(source_name, text)
    if text_format in {"html", "htm"}:
        text = _html_to_text(text)
    elif text_format == "json":
        text = _json_to_text(text)
    elif text_format == "csv":
        text = _csv_to_text(text)

    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_document(
    source: str | bytes | Path,
    *,
    source_name: str | None = None,
    chunk_words: int = 800,
    overlap_words: int = 80,
) -> dict[str, Any]:
    """Read text or a local path into normalized text, outline, and chunks."""

    inferred_name = source_name
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        path = Path(source)
        raw: str | bytes = path.read_bytes()
        inferred_name = source_name or path.name
    else:
        raw = source

    text = normalize_document_text(raw, source_name=inferred_name)
    chunks = chunk_document(text, max_words=chunk_words, overlap_words=overlap_words)
    return {
        "source_name": inferred_name or "inline",
        "format": detect_document_format(inferred_name, text),
        "text": text,
        "outline": extract_outline(text),
        "chunks": chunks,
        "word_count": len(text.split()),
    }


def extract_outline(text: str, *, max_items: int = 40) -> list[dict[str, Any]]:
    """Extract Markdown-style or numbered headings as a lightweight outline."""

    outline: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        heading = HEADING_PATTERN.match(line)
        if heading:
            outline.append(
                {
                    "level": len(heading.group(1)),
                    "title": heading.group(2).strip(),
                    "line_number": line_number,
                }
            )
        else:
            numbered = re.match(r"^\s*(\d+(?:\.\d+)*)[.)]\s+(.+)$", line)
            if numbered:
                outline.append(
                    {
                        "level": numbered.group(1).count(".") + 1,
                        "title": numbered.group(2).strip(),
                        "line_number": line_number,
                    }
                )
        if len(outline) >= max_items:
            break
    return outline


def chunk_document(
    text: str,
    *,
    max_words: int = 800,
    overlap_words: int = 80,
) -> list[dict[str, Any]]:
    """Split a document into word chunks while preserving a local heading hint."""

    if max_words <= 0:
        raise ValueError("max_words must be greater than 0")
    if overlap_words < 0:
        raise ValueError("overlap_words must be greater than or equal to 0")
    if overlap_words >= max_words:
        raise ValueError("overlap_words must be smaller than max_words")

    words = text.split()
    if not words:
        return []

    chunks: list[dict[str, Any]] = []
    start = 0
    headings = extract_outline(text)
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append(
            {
                "index": len(chunks),
                "text": chunk_text,
                "word_count": end - start,
                "heading_hint": _heading_hint_for_chunk(chunk_text, headings),
            }
        )
        if end == len(words):
            break
        start = end - overlap_words
    return chunks


def _html_to_text(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?i)</(p|div|section|article|h[1-6]|li|tr)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def _json_to_text(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(data, indent=2, sort_keys=True)


def _csv_to_text(text: str) -> str:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        return text
    lines = [" | ".join(reader.fieldnames)]
    for index, row in enumerate(reader, start=1):
        values = [str(row.get(field, "")).strip() for field in reader.fieldnames]
        lines.append(f"{index}. " + " | ".join(values))
    return "\n".join(lines)


def _heading_hint_for_chunk(chunk_text: str, headings: list[dict[str, Any]]) -> str:
    for heading in reversed(headings):
        if heading["title"] in chunk_text:
            return str(heading["title"])
    return ""
