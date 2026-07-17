#!/usr/bin/env python3
"""Record real runtime message correlation and causation in the run store."""
from __future__ import annotations

import json
import os
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


step = os.environ.get("MN_WORKFLOW_STEP_ID", "run")
message = mapping(load_json("MN_MESSAGE_FILE", {}))
envelope = mapping(message.get("envelope"))
trace_id = str(envelope.get("correlation_id", "missing-correlation"))
span_id = str(envelope.get("message_id", "missing-message-id"))
parent_span_id = envelope.get("causation_id")
trace_context = {"trace_id": trace_id, "span_id": span_id, "parent_span_id": parent_span_id, "step": step}
events = [
    {"type": "trace_span_started", "trace_id": trace_id, "span_id": span_id, "parent_span_id": parent_span_id, "payload": trace_context},
    {"type": "trace_span_linked", "trace_id": trace_id, "span_id": span_id, "parent_span_id": parent_span_id, "payload": {"relation": "child_of" if parent_span_id else "root", **trace_context}},
    {"type": "trace_span_completed", "trace_id": trace_id, "span_id": span_id, "parent_span_id": parent_span_id, "payload": trace_context},
]
result = {"demo": "demo_observability_trace", "step": step, "trace_context": trace_context, "deterministic": True}
emit_messages = []

if step == "run":
    emit_messages.append({"to": "publish", "type": "run_done", "payload": result})
elif step == "publish":
    emit_messages.append({"to": "report_sink", "type": "final_result", "payload": result})

if is_final_step("demo_observability_trace", step):
    write_run_store(result, events)

output = {"events": events, "complete_step": result, "next_state": result}
if emit_messages:
    output["emit_messages"] = emit_messages
print(json.dumps(output, sort_keys=True))
