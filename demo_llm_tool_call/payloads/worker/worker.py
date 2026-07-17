#!/usr/bin/env python3
"""Use a deterministic model fixture to invoke an actual local tool function."""
from __future__ import annotations

import hashlib
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


def deterministic_model_decision(payload: dict) -> dict:
    request = mapping(payload.get("forecast_request"))
    city = str(request.get("city", "Boston")).strip().title()
    day = str(request.get("day", "tomorrow")).strip().lower()
    return {"model": "deterministic-tool-fixture", "tool": "local_forecast", "arguments": {"city": city, "day": day}, "reason": "forecast intent maps to the local_forecast capability"}


def local_forecast(arguments: dict) -> dict:
    city = arguments["city"]
    day = arguments["day"]
    seed = int(hashlib.sha256(f"{city}:{day}".encode("utf-8")).hexdigest()[:2], 16)
    baseline = {"Boston": (19, "clear"), "Seattle": (16, "overcast"), "Austin": (27, "sunny")}.get(city, (20, "partly cloudy"))
    return {"city": city, "day": day, "high_c": baseline[0] + seed % 3, "condition": baseline[1], "provider": "local_fixture"}


def invoke_tool(name: str, arguments: dict) -> dict:
    tools = {"local_forecast": local_forecast}
    if name not in tools:
        raise ValueError(f"unsupported local tool: {name}")
    return tools[name](arguments)


step = os.environ.get("MN_WORKFLOW_STEP_ID", "run")
payload = mapping(load_json("MN_INPUT_FILE", {}))
events = [{"type": "demo_step_observed", "payload": {"step": step}}]
result = {"demo": "demo_llm_tool_call", "step": step, "deterministic": True}
emit_messages = []

if step == "run":
    decision = deterministic_model_decision(payload)
    call_id = "tool_" + hashlib.sha256(json.dumps(decision, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    events.append({"type": "llm_tool_call_requested", "payload": {"call_id": call_id, **decision}})
    tool_result = invoke_tool(decision["tool"], decision["arguments"])
    trace = {"call_id": call_id, "model": decision["model"], "tool": decision["tool"], "arguments": decision["arguments"], "result": tool_result, "invoked": True}
    result["tool_trace"] = trace
    events.append({"type": "llm_tool_call_completed", "payload": trace})
    emit_messages.append({"to": "publish", "type": "run_done", "payload": result})
else:
    result["status"] = "published"
    emit_messages.append({"to": "report_sink", "type": "final_result", "payload": result})

if is_final_step("demo_llm_tool_call", step):
    write_run_store(result, events)

output = {"events": events, "complete_step": result, "next_state": result}
if emit_messages:
    output["emit_messages"] = emit_messages
print(json.dumps(output, sort_keys=True))
