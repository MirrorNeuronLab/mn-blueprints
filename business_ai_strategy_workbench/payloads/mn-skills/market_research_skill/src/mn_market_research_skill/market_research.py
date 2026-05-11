from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any


DEFAULT_RESEARCH_QUESTIONS = (
    "What customer problem is changing?",
    "Which buyer segments are most affected?",
    "What alternatives or competitors are visible?",
    "What adoption barriers or risks appear repeatedly?",
    "What evidence would change the recommendation?",
)
STOP_WORDS = {
    "about",
    "after",
    "against",
    "also",
    "and",
    "are",
    "because",
    "from",
    "that",
    "their",
    "this",
    "with",
}


def build_research_brief(
    topic: str,
    *,
    audience: str = "",
    competitors: list[str] | None = None,
    questions: list[str] | None = None,
) -> dict[str, Any]:
    """Create a reusable market research brief scaffold."""

    return {
        "topic": _clean(topic),
        "audience": _clean(audience),
        "competitors": [_clean(competitor) for competitor in competitors or [] if _clean(competitor)],
        "questions": questions or list(DEFAULT_RESEARCH_QUESTIONS),
        "deliverables": [
            "market snapshot",
            "buyer and user needs",
            "competitive landscape",
            "opportunities and risks",
            "recommended next research",
        ],
    }


def normalize_source_note(note: str | dict[str, Any], *, index: int = 0) -> dict[str, Any]:
    """Normalize one market source note into source, title, claims, and url fields."""

    if isinstance(note, str):
        return {
            "source": f"source-{index + 1}",
            "title": "",
            "claims": [_clean(part) for part in re.split(r"\n+|;\s*", note) if _clean(part)],
            "url": "",
        }

    claims = note.get("claims") or note.get("notes") or note.get("content") or []
    if isinstance(claims, str):
        claims = [_clean(part) for part in re.split(r"\n+|;\s*", claims) if _clean(part)]
    return {
        "source": _clean(note.get("source") or note.get("publisher") or f"source-{index + 1}"),
        "title": _clean(note.get("title") or ""),
        "claims": [_clean(claim) for claim in claims if _clean(claim)],
        "url": _clean(note.get("url") or ""),
    }


def synthesize_source_notes(notes: list[str | dict[str, Any]], *, top_terms: int = 8) -> dict[str, Any]:
    """Summarize source notes into themes, claims, and citations."""

    normalized = [normalize_source_note(note, index=index) for index, note in enumerate(notes)]
    all_claims = [
        {"claim": claim, "source": note["source"], "url": note["url"]}
        for note in normalized
        for claim in note["claims"]
    ]
    term_counts = _term_counts([claim["claim"] for claim in all_claims])
    themes = [
        {"theme": term, "mentions": count}
        for term, count in term_counts.most_common(top_terms)
    ]
    return {
        "source_count": len(normalized),
        "claim_count": len(all_claims),
        "themes": themes,
        "claims": all_claims,
        "citations": _citation_index(normalized),
    }


def build_market_research_outline(
    brief: dict[str, Any] | str,
    *,
    synthesis: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build a market research report outline from a brief and optional synthesis."""

    normalized_brief = build_research_brief(brief) if isinstance(brief, str) else dict(brief)
    topic = normalized_brief.get("topic") or "Market research"
    themes = [theme["theme"] for theme in (synthesis or {}).get("themes", [])[:5]]
    sections = [
        ("Executive Summary", f"Answer the most important question about {topic}."),
        ("Market Context", "Describe category dynamics, demand signals, and timing."),
        ("Customer Needs", "Summarize buyer/user problems and unmet needs."),
        ("Competitive Landscape", "Compare relevant alternatives and positioning."),
        ("Opportunities And Risks", "Separate actionable openings from uncertainty."),
        ("Recommended Next Steps", "Name the next research or go-to-market actions."),
    ]
    outline = [
        {"title": title, "purpose": purpose, "evidence_hints": themes if index < 3 else []}
        for index, (title, purpose) in enumerate(sections)
    ]
    if normalized_brief.get("competitors"):
        outline[3]["evidence_hints"] = normalized_brief["competitors"]
    return outline


def _term_counts(claims: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for claim in claims:
        seen: set[str] = set()
        words: list[str] = []
        for word in re.findall(r"\b[A-Za-z][A-Za-z-]{3,}\b", claim):
            normalized = word.lower()
            if normalized in STOP_WORDS or normalized in seen:
                continue
            words.append(normalized)
            seen.add(normalized)
        counter.update(words)
    return counter


def _citation_index(notes: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    citations: dict[str, dict[str, str]] = {}
    for note in notes:
        citations[note["source"]] = {"title": note["title"], "url": note["url"]}
    return citations


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
