#!/usr/bin/env python3
"""Emit small structured executor results for the DAG flow-pattern demo."""

import json
import os


step_id = os.environ.get("MN_WORKFLOW_STEP_ID", "unknown")
hello = f"hello from {step_id}"

failure_steps = {
    "any_done_failure",
    "failure_source",
    "fallback_primary",
    "fallback_secondary",
}

if step_id in failure_steps:
    result = {
        "events": [
            {
                "type": "workflow_step_failed",
                "payload": {"reason": f"intentional demo failure: {hello}"},
            }
        ],
        "next_state": {"hello": hello, "outcome": "intentional handled failure"},
    }
elif step_id == "branch_router":
    result = {
        "events": [
            {"type": "workflow_step_branch", "payload": {"branches": ["branch_left"]}}
        ],
        "complete_step": True,
        "next_state": {"hello": hello, "selected_branch": "branch_left"},
    }
elif step_id == "short_circuit_guard":
    result = {
        "events": [
            {
                "type": "workflow_step_skipped",
                "payload": {"reason": "intentional no-work guard", "skip_downstream": True},
            }
        ],
        "next_state": {"hello": hello, "outcome": "short-circuited"},
    }
elif step_id == "scatter_source":
    result = {
        "events": [
            {
                "type": "workflow_step_scatter",
                "payload": {
                    "target": "scatter_worker",
                    "items": [
                        {"message": "hello mapped item 0"},
                        {"message": "hello mapped item 1"},
                        {"message": "hello mapped item 2"},
                    ],
                },
            }
        ],
        "complete_step": True,
        "next_state": {"hello": hello, "mapped_items": 3},
    }
else:
    result = {"complete_step": True, "next_state": {"hello": hello}}

print(json.dumps(result, sort_keys=True))
