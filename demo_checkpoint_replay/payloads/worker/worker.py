#!/usr/bin/env python3
"""Exercise persisted executor state by replaying a duplicate event delivery."""
from __future__ import annotations

import json
import os
from pathlib import Path

from run_store import write_run_store


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


step = os.environ.get("MN_WORKFLOW_STEP_ID", "run")
payload = mapping(load_json("MN_INPUT_FILE", {}))
context = mapping(load_json("MN_CONTEXT_FILE", {}))
events = [{"type": "demo_step_observed", "payload": {"step": step}}]
result = {"demo": "demo_checkpoint_replay", "step": step, "deterministic": True}
next_state = mapping(context.get("agent_state"))
complete = True
emit_messages = []

if step == "run" and not isinstance(payload.get("event_id"), str):
    sequence = ["evt-1", "evt-2", "evt-2", "evt-3", "evt-4", "evt-5"]
    next_state = {"checkpoint_replay": {"seen_ids": [], "processed_deliveries": 0, "duplicates_ignored": 0, "checkpoint_count": 0}}
    emit_messages = [
        {
            "to": "run",
            "type": "checkpoint_event",
            "payload": {"event_id": event_id, "ordinal": ordinal, "terminal": ordinal == len(sequence)},
        }
        for ordinal, event_id in enumerate(sequence, start=1)
    ]
    result["replay_plan"] = {"deliveries": sequence, "duplicate_event_id": "evt-2"}
    events.append({"type": "checkpoint_replay_seeded", "payload": result["replay_plan"]})
    complete = False
elif step == "run":
    checkpoint = mapping(next_state.get("checkpoint_replay"))
    seen_ids = list(checkpoint.get("seen_ids") or [])
    event_id = payload["event_id"]
    duplicate = event_id in seen_ids
    if not duplicate:
        seen_ids.append(event_id)
    processed = int(checkpoint.get("processed_deliveries", 0)) + 1
    duplicates = int(checkpoint.get("duplicates_ignored", 0)) + int(duplicate)
    checkpoint_count = int(checkpoint.get("checkpoint_count", 0))
    if processed % 2 == 0 or duplicate:
        checkpoint_count += 1
        events.append({"type": "runtime_checkpoint_state_updated", "payload": {"processed_deliveries": processed, "seen_ids": seen_ids, "checkpoint_count": checkpoint_count}})
    events.append({"type": "replayed_duplicate_ignored" if duplicate else "checkpoint_event_processed", "payload": {"event_id": event_id, "ordinal": payload.get("ordinal")}})
    next_state = {"checkpoint_replay": {"seen_ids": seen_ids, "processed_deliveries": processed, "duplicates_ignored": duplicates, "checkpoint_count": checkpoint_count}}
    if payload.get("terminal"):
        result["checkpoint_replay"] = {**next_state["checkpoint_replay"], "resume_source": "persisted_executor_agent_state"}
        events.append({"type": "checkpoint_replay_completed", "payload": result["checkpoint_replay"]})
    else:
        result["checkpoint_replay"] = next_state["checkpoint_replay"]
        complete = False
else:
    result["status"] = "published"
    emit_messages.append({"to": "report_sink", "type": "final_result", "payload": result})

if step == "run" and complete:
    write_run_store(result, events)
    emit_messages.append({"to": "publish", "type": "run_done", "payload": result})

output = {"events": events, "next_state": next_state}
if emit_messages:
    output["emit_messages"] = emit_messages
if complete:
    output["complete_step"] = result
print(json.dumps(output, sort_keys=True))
