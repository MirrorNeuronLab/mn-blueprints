#!/usr/bin/env python3
"""Deterministic controller and template worker for the dynamic DAG demo."""
from __future__ import annotations

import json
import os
from pathlib import Path

from run_store import write_run_store


def load_json(path_name: str) -> dict:
    value = os.environ.get(path_name)
    if not value:
        return {}
    try:
        decoded = json.loads(Path(value).read_text(encoding="utf-8"))
        return decoded if isinstance(decoded, dict) else {}
    except Exception:
        return {}


def find_key(value, key):
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for nested in value.values():
            found = find_key(nested, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = find_key(nested, key)
            if found is not None:
                return found
    return None


step = os.environ.get("MN_WORKFLOW_STEP_ID", "inspect_context")
revision = int(os.environ.get("MN_WORKFLOW_GRAPH_REVISION", "0"))
input_document = load_json("MN_INPUT_FILE")
message = load_json("MN_MESSAGE_FILE")
evidence_gap = find_key(input_document, "evidence_gap")
evidence_gap = True if evidence_gap is None else bool(evidence_gap)
events = [{"type": "dynamic_demo_step_observed", "payload": {"step": step}}]
outputs = {"step": step, "deterministic": True}

if step == "inspect_context":
    outputs.update({"evidence_gap": evidence_gap, "decision": "expand" if evidence_gap else "keep_fixed_path"})
    if evidence_gap:
        events.append(
            {
                "type": "workflow_graph_patch",
                "payload": {
                    "patch_id": "evidence-gap-1",
                    "base_revision": revision,
                    "region_id": "research_followups",
                    "operations": [
                        {"op": "remove_edge", "id": "inspect_to_report"},
                        {
                            "op": "add_step",
                            "id": "followup_research_1",
                            "template": "followup_research",
                            "with": {"question": "Collect deterministic primary evidence."},
                        },
                        {
                            "op": "add_step",
                            "id": "verify_evidence_1",
                            "template": "verify_evidence",
                            "with": {"minimum_sources": 1},
                        },
                        {
                            "op": "add_edge",
                            "id": "inspect_to_followup",
                            "from": "inspect_context",
                            "to": "followup_research_1",
                        },
                        {
                            "op": "add_edge",
                            "id": "followup_to_verify",
                            "from": "followup_research_1",
                            "to": "verify_evidence_1",
                        },
                        {
                            "op": "add_edge",
                            "id": "verify_to_report",
                            "from": "verify_evidence_1",
                            "to": "write_report",
                        },
                    ],
                },
            }
        )
elif step == "followup_research_1":
    outputs.update(
        {
            "evidence": [
                {
                    "id": "local-primary-1",
                    "claim": "The admitted follow-up worker executed.",
                    "source": "bundled deterministic fixture",
                }
            ]
        }
    )
elif step == "verify_evidence_1":
    outputs.update(
        {
            "verified": True,
            "evidence_ids": ["local-primary-1"],
            "verification": "deterministic schema and provenance checks passed",
        }
    )
elif step == "write_report":
    inserted = (
        ["followup_research_1", "verify_evidence_1"] if revision == 1 else []
    )
    final_artifact = {
        "schema_version": "mn.blueprint.final_artifact.v1",
        "blueprint_id": "demo_dynamic_workflow",
        "status": "completed",
        "fixed_steps": ["inspect_context", "write_report"],
        "inserted_steps": inserted,
        "graph_revision": revision,
        "verified_evidence": revision == 1,
        "applied_patch_id": "evidence-gap-1" if revision == 1 else None,
        "path": (
            ["inspect_context", *inserted, "write_report"]
            if inserted
            else ["inspect_context", "write_report"]
        ),
    }
    outputs = final_artifact
    events.append(
        {
            "type": "dynamic_workflow_demo_completed",
            "payload": {
                "graph_revision": revision,
                "applied_patch_id": final_artifact["applied_patch_id"],
                "verified_evidence": final_artifact["verified_evidence"],
            },
        }
    )
    write_run_store(final_artifact, events)

print(
    json.dumps(
        {
            "outputs": outputs,
            "events": events,
            "complete_step": outputs,
            "status": "completed",
        },
        sort_keys=True,
    )
)
