from __future__ import annotations

import re
from typing import Any


DEFAULT_SECTIONS = (
    "Executive Summary",
    "Current State",
    "Key Findings",
    "Recommendations",
    "Implementation Considerations",
    "Next Steps",
)


def build_client_report_outline(
    title: str,
    *,
    audience: str = "",
    findings: list[str] | None = None,
    recommendations: list[str] | None = None,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    """Build a structured client report outline."""

    report_sections = []
    for section in sections or list(DEFAULT_SECTIONS):
        section_title = _clean(section)
        body = []
        if section_title == "Key Findings":
            body = _string_list(findings)
        elif section_title == "Recommendations":
            body = _string_list(recommendations)
        report_sections.append({"title": section_title, "bullets": body, "narrative": ""})
    return {
        "title": _clean(title),
        "audience": _clean(audience),
        "sections": report_sections,
        "appendices": [],
    }


def render_report_markdown(report: dict[str, Any]) -> str:
    """Render a report outline or draft as Markdown."""

    lines = [f"# {report.get('title') or 'Client Report'}"]
    if report.get("audience"):
        lines.extend(["", f"Audience: {report['audience']}"])
    for section in report.get("sections", []):
        lines.extend(["", f"## {section.get('title') or 'Section'}"])
        narrative = _clean(section.get("narrative") or "")
        if narrative:
            lines.append(narrative)
        for bullet in section.get("bullets") or []:
            lines.append(f"- {_clean(bullet)}")
    appendices = report.get("appendices") or []
    if appendices:
        lines.extend(["", "## Appendices"])
        for appendix in appendices:
            lines.append(f"- {_clean(appendix)}")
    return "\n".join(lines).strip() + "\n"


def review_client_report(report: dict[str, Any]) -> dict[str, Any]:
    """Check for common missing pieces in a client-facing report."""

    issues: list[str] = []
    if not _clean(report.get("title")):
        issues.append("Report is missing a title.")
    if not _clean(report.get("audience")):
        issues.append("Report is missing an audience.")

    section_titles = {_clean(section.get("title")) for section in report.get("sections", [])}
    for required in ("Executive Summary", "Key Findings", "Recommendations", "Next Steps"):
        if required not in section_titles:
            issues.append(f"Report is missing {required}.")

    for section in report.get("sections", []):
        if not section.get("bullets") and not _clean(section.get("narrative")):
            issues.append(f"{section.get('title') or 'A section'} has no content.")
    return {"approved": not issues, "issues": issues, "section_count": len(report.get("sections", []))}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_clean(value)] if _clean(value) else []
    return [_clean(item) for item in value if _clean(item)]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
