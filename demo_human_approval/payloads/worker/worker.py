#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from run_store import is_final_step, request_human_approval, write_run_store


def load_json(path_env: str, default):
    path = os.environ.get(path_env)
    if not path:
        return default
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


demo = os.environ.get("MN_DEMO_ID", "unknown")
step = os.environ.get("MN_WORKFLOW_STEP_ID", "run")
payload = load_json("MN_INPUT_FILE", {})
context = load_json("MN_CONTEXT_FILE", {})
workflow = context.get("workflow") or {}
attempt = int(workflow.get("attempt") or 1)
sleep_ms = int(os.environ.get("MN_DEMO_SLEEP_MS", "0"))
if sleep_ms:
    time.sleep(sleep_ms / 1000)

result = {
    "demo": demo,
    "step": step,
    "input": payload,
    "attempt": attempt,
    "deterministic": True,
}

events = [{"type": "demo_step_observed", "payload": {"demo": demo, "step": step, "attempt": attempt}}]

if demo == "demo_dag_scatter_gather" and step == "scatter":
    events.append({"type": "workflow_step_scatter", "payload": {"targets": ["worker"], "items": [{"record_id": f"r-{i}", "value": i} for i in range(1, 6)]}})
    result["mapped_items"] = 5
elif demo == "demo_dag_conditional_branch" and step == "route":
    events.append({"type": "workflow_step_branch", "payload": {"branches": ["high_risk"]}})
    result["selected_branch"] = "high_risk"
elif demo == "demo_dag_failure_fallback" and step == "primary":
    print(json.dumps({"events": events + [{"type": "workflow_step_failed", "payload": {"reason": "intentional primary outage"}}], "next_state": result}, sort_keys=True))
    raise SystemExit(0)
elif demo == "demo_dag_quorum" and step == "sensor_c":
    print(json.dumps({"events": events + [{"type": "workflow_step_failed", "payload": {"reason": "intentional dissenting sensor"}}], "next_state": result}, sort_keys=True))
    raise SystemExit(0)
elif demo == "demo_retry_recovery" and step == "run" and attempt == 1:
    print(json.dumps({"events": events, "next_state": result}, sort_keys=True))
    raise SystemExit(23)
elif demo == "demo_human_approval" and step == "run":
    response = request_human_approval(
        "demo-approval",
        "Approve a harmless local artifact write?",
    )
    approved = bool(response.get("approved") or response.get("decision") == "approve")
    events.append(
        {
            "type": "human_decision_applied",
            "payload": {"request_id": "demo-approval", "decision": response.get("decision"), "approved": approved},
        }
    )
    result.update({"approved": approved, "reviewer": response.get("reviewer")})
    if not approved:
        raise SystemExit(24)
elif demo == "demo_llm_tool_call" and step == "run":
    tool_args = {"city": "Boston", "day": "tomorrow"}
    tool_result = {"high_c": 22, "condition": "clear"}
    events.extend([
        {"type": "llm_tool_selected", "payload": {"model": "deterministic-tool-fixture", "tool": "local_forecast", "arguments": tool_args}},
        {"type": "llm_tool_completed", "payload": {"tool": "local_forecast", "result": tool_result}},
    ])
    result["tool_trace"] = {"tool": "local_forecast", "arguments": tool_args, "result": tool_result}
elif demo == "demo_context_memory_acl" and step == "run":
    from context_demo import run_acl_demo
    result.update(run_acl_demo(context))
elif demo == "demo_context_compression" and step == "run":
    from context_demo import run_compression_demo
    result.update(run_compression_demo(context))
elif demo == "demo_stream_backpressure":
    result.update({"produced": 10, "queue_size": 3, "drop_policy": "sample", "processed": [0, 3, 6, 9]})
    events.append({"type": "stream_sampled", "payload": {"received": 10, "processed": 4, "queue_size": 3}})
elif demo == "demo_executor_pool" and step.startswith("worker_"):
    result.update({"pool": "demo", "pool_slots": 1, "worker": step})
elif demo == "demo_resource_allocation" and step == "run":
    raw = os.environ.get("MN_ALLOCATION_JSON", "{}")
    try:
        allocation = json.loads(raw)
    except json.JSONDecodeError:
        allocation = {"raw": raw}
    result["allocation"] = allocation
elif demo == "demo_checkpoint_replay" and step == "run":
    ids = ["evt-1", "evt-2", "evt-2", "evt-3", "evt-4", "evt-5"]
    seen = []
    for event_id in ids:
        if event_id not in seen:
            seen.append(event_id)
    result.update({"seen_ids": seen, "duplicates_ignored": len(ids) - len(seen), "checkpoint_after": 2})
    events.append({"type": "checkpoint_written", "payload": {"processed_messages": 2, "seen_ids": seen[:2]}})
elif demo == "demo_observability_trace" and step == "run":
    result["trace_probe"] = {"parent": "run", "child": "worker", "linked": True}
    events.append({"type": "trace_probe", "payload": {"parent_span": "run", "child_span": "worker"}})
elif demo == "demo_docker_worker" and step == "run":
    value = b"mirror-neuron-demo"
    result["sha256"] = hashlib.sha256(value).hexdigest()
elif demo == "demo_openshell_worker" and step == "run":
    result["sandbox_validation"] = {"config_valid": True, "network_policy": "deny-all"}
else:
    result["status"] = "ok"

if is_final_step(demo, step):
    write_run_store(result, events)

print(json.dumps({"events": events, "complete_step": result, "next_state": result}, sort_keys=True))
