#!/usr/bin/env python3
"""Emit a burst, let the runtime queue it, and drain it through one consumer."""
from __future__ import annotations

import json
import os
import time
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


step = os.environ.get("MN_WORKFLOW_STEP_ID", "produce")
payload = mapping(load_json("MN_INPUT_FILE", {}))
context = mapping(load_json("MN_CONTEXT_FILE", {}))
events = [{"type": "demo_step_observed", "payload": {"step": step}}]
result = {"demo": "demo_stream_backpressure", "step": step, "deterministic": True}
next_state = mapping(context.get("agent_state"))
emit_messages = []
complete = True
burst_size = int(os.environ.get("MN_STREAM_BURST_SIZE", "10"))
queue_bound = int(os.environ.get("MN_STREAM_QUEUE_BOUND", "3"))

if step == "produce":
    stream_id = "bounded-burst-v1"
    emit_messages = [
        {
            "to": "consume",
            "type": "stream_item",
            "payload": {"stream_id": stream_id, "sequence": sequence, "value": sequence * 10, "terminal": sequence == burst_size - 1},
            "stream": {"stream_id": stream_id, "sequence": sequence, "end": sequence == burst_size - 1},
        }
        for sequence in range(burst_size)
    ]
    result["producer"] = {"emitted": burst_size, "stream_id": stream_id, "queue_bound": queue_bound}
    events.append({"type": "stream_burst_emitted", "payload": result["producer"]})
elif step == "consume":
    item = mapping(payload.get("stream_item")) or payload
    if "sequence" not in item or "stream_id" not in item:
        result["consumer"] = {"status": "waiting_for_stream_items"}
        events.append({"type": "stream_control_message_ignored", "payload": result["consumer"]})
        complete = False
    else:
        time.sleep(int(os.environ.get("MN_STREAM_CONSUME_DELAY_MS", "60")) / 1_000)
        stream = mapping(next_state.get("stream_backpressure"))
        processed = list(stream.get("processed_sequences") or [])
        sequence = item["sequence"]
        duplicate = sequence in processed
        if not duplicate:
            processed.append(sequence)
        stream = {"stream_id": item["stream_id"], "processed_sequences": sorted(processed), "duplicates": int(stream.get("duplicates", 0)) + int(duplicate)}
        next_state = {"stream_backpressure": stream}
        events.append({"type": "stream_item_processed", "payload": {"sequence": sequence, "processed_count": len(processed), "queue_bound": queue_bound, "duplicate": duplicate}})
        if item.get("terminal") and len(processed) == burst_size:
            result["backpressure"] = {"producer_emitted": burst_size, "consumer_processed": len(processed), "queue_bound": queue_bound, "policy": "block", "drained_sequences": sorted(processed), "duplicates": stream["duplicates"]}
            events.append({"type": "stream_drain_completed", "payload": result["backpressure"]})
        else:
            result["backpressure"] = {"processed": len(processed), "waiting_for": burst_size - len(processed), "queue_bound": queue_bound}
            complete = False
else:
    result["status"] = "ok"

if step == "consume" and complete and is_final_step("demo_stream_backpressure", step):
    write_run_store(result, events)

output = {"events": events, "next_state": next_state}
if emit_messages:
    output["emit_messages"] = emit_messages
if complete:
    output["complete_step"] = result
    if step == "consume":
        # The sink receives one terminal result after the full burst has drained.
        output["emit_messages"] = [{"to": "report_sink", "type": "final_result", "payload": result}]
print(json.dumps(output, sort_keys=True))
