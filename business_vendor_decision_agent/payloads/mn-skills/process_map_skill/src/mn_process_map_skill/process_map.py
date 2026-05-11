from __future__ import annotations

import re
from typing import Any


def normalize_step(step: str | dict[str, Any], *, index: int = 0) -> dict[str, Any]:
    """Normalize a process step into an id, label, owner, inputs, and outputs."""

    if isinstance(step, str):
        data = {"label": step}
    else:
        data = dict(step)
    step_id = _slug(data.get("id") or data.get("label") or f"step-{index + 1}")
    return {
        "id": step_id,
        "label": _clean(data.get("label") or data.get("name") or f"Step {index + 1}"),
        "owner": _clean(data.get("owner") or ""),
        "inputs": _string_list(data.get("inputs")),
        "outputs": _string_list(data.get("outputs")),
        "type": _clean(data.get("type") or "activity"),
    }


def build_process_map(
    steps: list[str | dict[str, Any]],
    *,
    name: str = "Process",
) -> dict[str, Any]:
    """Build a linear process map from ordered steps."""

    nodes = [normalize_step(step, index=index) for index, step in enumerate(steps)]
    edges = [
        {"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": ""}
        for index in range(max(0, len(nodes) - 1))
    ]
    return {"name": _clean(name), "nodes": nodes, "edges": edges}


def render_mermaid_flowchart(process_map: dict[str, Any]) -> str:
    """Render a process map as a Mermaid flowchart."""

    lines = ["flowchart TD"]
    for node in process_map.get("nodes", []):
        label = _escape_label(node.get("label") or node.get("id"))
        owner = node.get("owner")
        if owner:
            label = f"{label}\\nOwner: {_escape_label(owner)}"
        lines.append(f"  {node['id']}[\"{label}\"]")
    for edge in process_map.get("edges", []):
        label = edge.get("label")
        if label:
            lines.append(f"  {edge['from']} -->|{_escape_label(label)}| {edge['to']}")
        else:
            lines.append(f"  {edge['from']} --> {edge['to']}")
    return "\n".join(lines) + "\n"


def find_process_gaps(process_map: dict[str, Any]) -> list[str]:
    """Flag missing owners, disconnected nodes, and empty process maps."""

    nodes = process_map.get("nodes", [])
    edges = process_map.get("edges", [])
    if not nodes:
        return ["Process map has no steps."]
    connected = {edge["from"] for edge in edges} | {edge["to"] for edge in edges}
    gaps: list[str] = []
    for node in nodes:
        if not node.get("owner"):
            gaps.append(f"{node['label']} has no owner.")
        if len(nodes) > 1 and node["id"] not in connected:
            gaps.append(f"{node['label']} is disconnected.")
    if not edges and len(nodes) > 1:
        gaps.append("Process map has multiple steps but no edges.")
    return gaps


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_clean(value)] if _clean(value) else []
    return [_clean(item) for item in value if _clean(item)]


def _slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return slug or "step"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _escape_label(value: Any) -> str:
    return _clean(value).replace('"', "'").replace("|", "/")
