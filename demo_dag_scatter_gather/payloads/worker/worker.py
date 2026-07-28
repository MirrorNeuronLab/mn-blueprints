#!/usr/bin/env python3
"""Dynamically fan out records, score each mapped item, then gather them."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from run_store import is_final_step, write_run_store


def load_json(path_env: str, default):
    path = os.environ.get(path_env)
    if not path:
        return default
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def mapping(value):
    return value if isinstance(value, dict) else {}


def gathered_scores(mapped_score):
    runs_root = os.environ.get("MN_RUNS_ROOT")
    run_id = os.environ.get("MN_RUN_ID")
    if not runs_root or not run_id:
        raise RuntimeError("MN_RUNS_ROOT and MN_RUN_ID are required for gather state")
    run_dir = Path(runs_root).expanduser() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(run_dir / ".gather.sqlite3", timeout=5) as database:
        database.execute(
            "CREATE TABLE IF NOT EXISTS scores "
            "(map_index INTEGER PRIMARY KEY, record_id TEXT NOT NULL, score REAL NOT NULL)"
        )
        if mapped_score:
            database.execute(
                "INSERT OR REPLACE INTO scores(map_index, record_id, score) "
                "VALUES (?, ?, ?)",
                (
                    int(mapped_score["map_index"]),
                    str(mapped_score["record_id"]),
                    float(mapped_score["score"]),
                ),
            )
        rows = database.execute(
            "SELECT map_index, record_id, score FROM scores ORDER BY map_index"
        ).fetchall()
    return {
        str(map_index): {
            "record_id": record_id,
            "score": int(score) if score.is_integer() else score,
        }
        for map_index, record_id, score in rows
    }


configured_step = os.environ.get("MN_WORKFLOW_STEP_ID", "scatter")
payload = mapping(load_json("MN_INPUT_FILE", {}))
context = mapping(load_json("MN_CONTEXT_FILE", {}))
runtime_step = str(mapping(context.get("workflow")).get("step_id") or configured_step)
step = runtime_step.split("[", 1)[0]
events = [{"type": "demo_step_observed", "payload": {"step": runtime_step}}]
result = {"demo": "demo_dag_scatter_gather", "step": runtime_step, "deterministic": True}
next_state = mapping(context.get("agent_state"))
complete = True
emit_messages = []

if step == "scatter":
    records = payload.get("records") if isinstance(payload.get("records"), list) else [1, 2, 3, 4, 5]
    items = [{"record_id": f"r-{index}", "value": value} for index, value in enumerate(records, start=1)]
    events.append(
        {
            "type": "workflow_step_scatter",
            "payload": {"targets": ["worker"], "items": items, "max_items": len(items)},
        }
    )
    result["scatter"] = {"requested_items": len(items), "target": "worker"}
elif step == "worker":
    item = mapping(payload.get("item"))
    value = item.get("value", 0)
    if not isinstance(value, (int, float)):
        raise ValueError("mapped record value must be numeric")
    score = value * value
    result["mapped_score"] = {"record_id": item.get("record_id"), "map_index": payload.get("map_index"), "score": score}
    events.append({"type": "mapped_record_scored", "payload": result["mapped_score"]})
    emit_messages.append(
        {
            "to": "collect",
            "type": "worker_done",
            "body": {"mapped_score": result["mapped_score"]},
        }
    )
elif step == "collect":
    mapped_score = mapping(payload.get("mapped_score"))
    scores = gathered_scores(mapped_score)
    if mapped_score:
        events.append(
            {
                "type": "gather_item_received",
                "payload": mapped_score,
            }
        )
    else:
        events.append({"type": "gather_control_message_ignored", "payload": {"reason": "no mapped item"}})
    next_state = {"gather": {"scores": scores}}
    expected = int(os.environ.get("MN_SCATTER_EXPECTED_ITEMS", "5"))
    if len(scores) >= expected:
        collected = [scores[key] for key in sorted(scores, key=int)]
        result["gather"] = {"mapped_items": len(collected), "collected_scores": collected, "score_total": sum(item["score"] for item in collected)}
        events.append(
            {
                "type": "workflow_step_scattered_observed",
                "payload": {"mapped_items": len(collected)},
            }
        )
        events.append({"type": "workflow_gather_completed", "payload": result["gather"]})
    else:
        result["gather"] = {"waiting_for": expected - len(scores), "received": len(scores)}
        events.append({"type": "workflow_gather_waiting", "payload": result["gather"]})
        complete = False
else:
    result["status"] = "ok"

if step == "collect" and complete and is_final_step("demo_dag_scatter_gather", step):
    write_run_store(result, events)

output = {"events": events, "next_state": next_state}
if emit_messages:
    output["emit_messages"] = emit_messages
if complete:
    output["complete_step"] = result
    if step == "collect":
        # Only the completed gather may notify the terminal result sink; earlier
        # collection passes intentionally persist state without finishing the run.
        output["emit_messages"] = [{"to": "report_sink", "type": "final_result", "payload": result}]
print(json.dumps(output, sort_keys=True))
