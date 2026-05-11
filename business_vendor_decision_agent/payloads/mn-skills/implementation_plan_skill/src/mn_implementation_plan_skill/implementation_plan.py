from __future__ import annotations

import math
import re
from typing import Any


DEFAULT_PHASES = ("Discover", "Design", "Build", "Validate", "Launch")


def normalize_workstream(workstream: str | dict[str, Any], *, index: int = 0) -> dict[str, Any]:
    """Normalize a workstream into owner, outcomes, tasks, and dependencies."""

    if isinstance(workstream, str):
        return {
            "name": _clean(workstream),
            "owner": "",
            "outcomes": [],
            "tasks": [],
            "dependencies": [],
        }
    return {
        "name": _clean(workstream.get("name") or f"Workstream {index + 1}"),
        "owner": _clean(workstream.get("owner") or ""),
        "outcomes": _string_list(workstream.get("outcomes") or workstream.get("deliverables")),
        "tasks": _string_list(workstream.get("tasks")),
        "dependencies": _string_list(workstream.get("dependencies")),
    }


def build_implementation_plan(
    goal: str,
    *,
    workstreams: list[str | dict[str, Any]] | None = None,
    timeline_weeks: int = 6,
    phases: list[str] | None = None,
) -> dict[str, Any]:
    """Build a reusable implementation plan scaffold."""

    if timeline_weeks <= 0:
        raise ValueError("timeline_weeks must be greater than 0")
    phase_names = phases or list(DEFAULT_PHASES)
    weeks_per_phase = max(1, math.ceil(timeline_weeks / len(phase_names)))
    normalized_workstreams = [
        normalize_workstream(workstream, index=index)
        for index, workstream in enumerate(workstreams or [])
    ]
    phase_entries = []
    start_week = 1
    for phase_name in phase_names:
        end_week = min(timeline_weeks, start_week + weeks_per_phase - 1)
        phase_entries.append(
            {
                "name": phase_name,
                "start_week": start_week,
                "end_week": end_week,
                "activities": _phase_activities(phase_name, normalized_workstreams),
                "exit_criteria": _exit_criteria(phase_name),
            }
        )
        start_week = end_week + 1
        if start_week > timeline_weeks:
            break
    return {
        "goal": _clean(goal),
        "timeline_weeks": timeline_weeks,
        "workstreams": normalized_workstreams,
        "phases": phase_entries,
        "milestones": [
            {"name": f"{phase['name']} complete", "week": phase["end_week"]}
            for phase in phase_entries
        ],
    }


def build_risk_register(risks: list[str | dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize implementation risks with impact, likelihood, and mitigation fields."""

    register: list[dict[str, Any]] = []
    for index, risk in enumerate(risks):
        if isinstance(risk, str):
            data = {"risk": risk}
        else:
            data = dict(risk)
        impact = _bounded_score(data.get("impact", 3))
        likelihood = _bounded_score(data.get("likelihood", 3))
        register.append(
            {
                "id": f"R{index + 1}",
                "risk": _clean(data.get("risk") or data.get("name")),
                "impact": impact,
                "likelihood": likelihood,
                "severity": impact * likelihood,
                "mitigation": _clean(data.get("mitigation") or "Assign owner and review weekly."),
                "owner": _clean(data.get("owner") or ""),
            }
        )
    return sorted(register, key=lambda item: item["severity"], reverse=True)


def format_plan_markdown(plan: dict[str, Any]) -> str:
    """Render an implementation plan dictionary as Markdown."""

    lines = [f"# Implementation Plan: {plan.get('goal') or 'Untitled'}"]
    lines.extend(["", f"Timeline: {plan.get('timeline_weeks')} weeks"])
    if plan.get("workstreams"):
        lines.extend(["", "## Workstreams"])
        for workstream in plan["workstreams"]:
            owner = f" ({workstream['owner']})" if workstream.get("owner") else ""
            lines.append(f"- {workstream['name']}{owner}")
    lines.extend(["", "## Phases"])
    for phase in plan.get("phases", []):
        lines.append(f"- Weeks {phase['start_week']}-{phase['end_week']}: {phase['name']}")
    lines.extend(["", "## Milestones"])
    for milestone in plan.get("milestones", []):
        lines.append(f"- Week {milestone['week']}: {milestone['name']}")
    return "\n".join(lines).strip() + "\n"


def _phase_activities(phase_name: str, workstreams: list[dict[str, Any]]) -> list[str]:
    names = [workstream["name"] for workstream in workstreams] or ["program"]
    if phase_name.lower() == "discover":
        return [f"Confirm scope and success criteria for {name}." for name in names]
    if phase_name.lower() == "design":
        return [f"Define target process and handoffs for {name}." for name in names]
    if phase_name.lower() == "build":
        return [f"Implement and configure {name}." for name in names]
    if phase_name.lower() == "validate":
        return [f"Test {name} with representative users and data." for name in names]
    if phase_name.lower() == "launch":
        return [f"Launch {name} with support and measurement in place." for name in names]
    return [f"Advance {name} through {phase_name}." for name in names]


def _exit_criteria(phase_name: str) -> list[str]:
    return [
        f"{phase_name} deliverables accepted.",
        "Risks and open decisions reviewed.",
    ]


def _bounded_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 3
    return max(1, min(5, score))


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_clean(value)] if _clean(value) else []
    return [_clean(item) for item in value if _clean(item)]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
