from __future__ import annotations

import re
from collections import Counter
from typing import Any


ACTION_PATTERNS = (
    r"\b(?P<owner>[A-Z][A-Za-z .'-]{1,40})\s+(?:will|to)\s+(?P<task>[^.?!\n]+)",
    r"\baction(?: item)?\s*[:\-]\s*(?P<task>[^.?!\n]+)",
)
DECISION_PATTERN = re.compile(r"\b(decided|decision|agreed|approved)\b[:\s-]*(?P<decision>[^.?!\n]+)", re.I)
SPEAKER_PATTERN = re.compile(r"^\s*(?P<speaker>[A-Z][A-Za-z .'-]{1,40})\s*:\s+", re.MULTILINE)
STOP_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "for",
    "from",
    "have",
    "into",
    "that",
    "the",
    "this",
    "with",
    "will",
}
NON_PARTICIPANT_LABELS = {"action item", "decision", "note", "notes"}


def extract_participants(transcript: str) -> list[str]:
    """Return unique speaker labels in first-seen order."""

    participants: list[str] = []
    seen: set[str] = set()
    for match in SPEAKER_PATTERN.finditer(transcript):
        speaker = re.sub(r"\s+", " ", match.group("speaker")).strip()
        if speaker.lower() in NON_PARTICIPANT_LABELS:
            continue
        if speaker not in seen:
            participants.append(speaker)
            seen.add(speaker)
    return participants


def extract_action_items(transcript: str) -> list[dict[str, str]]:
    """Extract explicit action-style sentences from meeting text."""

    actions: list[dict[str, str]] = []
    for pattern in ACTION_PATTERNS:
        for match in re.finditer(pattern, transcript, flags=re.I):
            owner = match.groupdict().get("owner") or ""
            task = _clean_sentence(match.group("task"))
            if task:
                actions.append({"owner": owner.strip(), "task": task})
    return _dedupe_dicts(actions, key_fields=("owner", "task"))


def extract_decisions(transcript: str) -> list[str]:
    """Extract decision-like statements from a transcript or notes."""

    decisions = [_clean_sentence(match.group("decision")) for match in DECISION_PATTERN.finditer(transcript)]
    return [decision for decision in dict.fromkeys(decisions) if decision]


def build_meeting_summary(
    transcript: str,
    *,
    title: str = "Meeting summary",
    max_topics: int = 5,
) -> dict[str, Any]:
    """Build a structured meeting summary scaffold from transcript text."""

    participants = extract_participants(transcript)
    actions = extract_action_items(transcript)
    decisions = extract_decisions(transcript)
    topics = _top_terms(transcript, limit=max_topics)
    return {
        "title": title,
        "participants": participants,
        "topics": topics,
        "decisions": decisions,
        "action_items": actions,
        "summary_bullets": _summary_bullets(transcript, topics, decisions),
    }


def format_meeting_summary_markdown(summary: dict[str, Any]) -> str:
    """Render a meeting summary dictionary as portable Markdown."""

    lines = [f"# {summary.get('title') or 'Meeting summary'}"]
    participants = summary.get("participants") or []
    if participants:
        lines.extend(["", "## Participants", *[f"- {participant}" for participant in participants]])

    bullets = summary.get("summary_bullets") or []
    if bullets:
        lines.extend(["", "## Summary", *[f"- {bullet}" for bullet in bullets]])

    decisions = summary.get("decisions") or []
    if decisions:
        lines.extend(["", "## Decisions", *[f"- {decision}" for decision in decisions]])

    actions = summary.get("action_items") or []
    if actions:
        lines.append("")
        lines.append("## Action Items")
        for action in actions:
            owner = action.get("owner") or "Unassigned"
            lines.append(f"- {owner}: {action.get('task', '').strip()}")
    return "\n".join(lines).strip() + "\n"


def _summary_bullets(transcript: str, topics: list[str], decisions: list[str]) -> list[str]:
    bullets: list[str] = []
    if topics:
        bullets.append("Discussed " + ", ".join(topics[:3]) + ".")
    if decisions:
        bullets.append(f"Captured {len(decisions)} decision(s).")
    if not bullets and transcript.strip():
        bullets.append(_clean_sentence(transcript.splitlines()[0])[:180])
    return bullets


def _top_terms(text: str, *, limit: int) -> list[str]:
    terms = [
        word.lower()
        for word in re.findall(r"\b[A-Za-z][A-Za-z-]{3,}\b", text)
        if word.lower() not in STOP_WORDS
    ]
    return [term for term, _count in Counter(terms).most_common(limit)]


def _clean_sentence(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .:-")


def _dedupe_dicts(items: list[dict[str, str]], *, key_fields: tuple[str, ...]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[dict[str, str]] = []
    for item in items:
        key = tuple(item.get(field, "").lower() for field in key_fields)
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped
