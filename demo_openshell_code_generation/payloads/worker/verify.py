"""Offline structural validation; browser interaction checks are a separate gate."""

import hashlib
from html.parser import HTMLParser
from pathlib import Path


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = set()
        self.external = []
        self.lang = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.add(tag)
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag in {"script", "img", "link", "iframe"}:
            url = attrs.get("src") or attrs.get("href") or ""
            if url and not url.startswith(("data:", "#")):
                self.external.append(url)


def verify_page(path):
    path = Path(path)
    raw = path.read_bytes()
    if not 1000 <= len(raw) <= 250_000:
        raise ValueError("Generated HTML must be between 1 KB and 250 KB")
    page = raw.decode("utf-8")
    parser = PageParser()
    parser.feed(page)
    if "<!doctype html>" not in page.lower():
        raise ValueError("Missing HTML5 doctype")
    if not {"html", "title", "main", "button", "input", "script", "style"}.issubset(parser.tags):
        raise ValueError("Missing semantic or interactive page elements")
    if not parser.lang or "pizza" not in page.lower():
        raise ValueError("Missing language or pizza content")
    if parser.external:
        raise ValueError("Generated page depends on external assets")
    return {"status": "passed", "scope": "offline_structure",
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "external_assets": parser.external}
