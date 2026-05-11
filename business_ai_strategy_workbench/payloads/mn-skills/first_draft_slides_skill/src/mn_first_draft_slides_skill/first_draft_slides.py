from __future__ import annotations

import re
from typing import Any


DEFAULT_STORYLINE = (
    ("Context", "Set up the audience's current situation."),
    ("Key Observations", "Summarize what the evidence shows."),
    ("Implications", "Explain why the observations matter."),
    ("Recommendation", "State the preferred path."),
    ("Next Steps", "Make the first actions concrete."),
)


def build_slide_outline(
    brief: str,
    *,
    sections: list[str | dict[str, Any]] | None = None,
    audience: str = "",
    max_slides: int = 8,
) -> list[dict[str, Any]]:
    """Create a compact first-draft slide outline from a brief and optional sections."""

    if max_slides < 1:
        raise ValueError("max_slides must be at least 1")

    slides = [
        normalize_slide(
            {
                "title": _title_from_brief(brief),
                "takeaway": _clean_sentence(brief)[:160] or "Draft narrative for review.",
                "bullets": [f"Audience: {audience}"] if audience else [],
                "layout": "title",
            },
            index=0,
        )
    ]

    source_sections = sections or [
        {"title": title, "takeaway": takeaway, "bullets": []}
        for title, takeaway in DEFAULT_STORYLINE
    ]
    for index, section in enumerate(source_sections, start=1):
        if len(slides) >= max_slides:
            break
        slides.append(normalize_slide(section, index=index))
    return slides


def normalize_slide(slide: str | dict[str, Any], *, index: int = 0) -> dict[str, Any]:
    """Normalize a slide-like object into title, takeaway, bullets, and speaker notes."""

    if isinstance(slide, str):
        title, bullets = _split_section_text(slide)
        data: dict[str, Any] = {"title": title, "bullets": bullets}
    else:
        data = dict(slide)

    title = _clean_sentence(data.get("title") or data.get("heading") or f"Slide {index + 1}")
    takeaway = _clean_sentence(data.get("takeaway") or data.get("subtitle") or "")
    bullets = data.get("bullets") or data.get("body") or []
    if isinstance(bullets, str):
        bullets = [item.strip(" -") for item in bullets.splitlines() if item.strip(" -")]

    return {
        "slide_number": index + 1,
        "title": title,
        "takeaway": takeaway or title,
        "bullets": [_clean_sentence(str(bullet)) for bullet in bullets if str(bullet).strip()][:6],
        "layout": str(data.get("layout") or "title_and_bullets"),
        "speaker_notes": _clean_sentence(data.get("speaker_notes") or data.get("notes") or ""),
    }


def render_deck_markdown(slides: list[dict[str, Any]]) -> str:
    """Render a slide outline as Markdown separated by slide numbers."""

    blocks: list[str] = []
    for slide in slides:
        lines = [f"## {slide.get('slide_number')}. {slide.get('title')}"]
        takeaway = slide.get("takeaway")
        if takeaway:
            lines.append(f"**Takeaway:** {takeaway}")
        for bullet in slide.get("bullets") or []:
            lines.append(f"- {bullet}")
        notes = slide.get("speaker_notes")
        if notes:
            lines.extend(["", f"Notes: {notes}"])
        blocks.append("\n".join(lines).strip())
    return "\n\n".join(blocks).strip() + "\n"


def review_slide_outline(slides: list[dict[str, Any]]) -> dict[str, Any]:
    """Flag common first-draft deck issues without judging content strategy."""

    issues: list[str] = []
    if not slides:
        issues.append("No slides provided.")
    for slide in slides:
        if not slide.get("title"):
            issues.append(f"Slide {slide.get('slide_number', '?')} is missing a title.")
        if len(slide.get("bullets") or []) > 6:
            issues.append(f"Slide {slide.get('slide_number', '?')} has more than six bullets.")
        if len(str(slide.get("takeaway") or "")) > 180:
            issues.append(f"Slide {slide.get('slide_number', '?')} takeaway is long.")
    return {"approved": not issues, "issues": issues, "slide_count": len(slides)}


def _title_from_brief(brief: str) -> str:
    first_sentence = re.split(r"[.?!]\s+", brief.strip(), maxsplit=1)[0]
    words = first_sentence.split()[:8]
    return " ".join(words).strip().title() or "Draft Deck"


def _split_section_text(section: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    if not lines:
        return "Untitled", []
    title = lines[0].strip("# ")
    bullets = [line.strip(" -") for line in lines[1:]]
    return title, bullets


def _clean_sentence(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" -")
