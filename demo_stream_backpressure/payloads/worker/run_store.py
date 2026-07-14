from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_ARTIFACTS = (
    "run.json",
    "config.json",
    "inputs.json",
    "events.jsonl",
    "errors.jsonl",
    "timeline.jsonl",
    "observability_summary.json",
    "result.json",
    "final_artifact.json",
)

FINAL_STEPS = {
    "demo_canary_deployment": "close",
    "demo_checkpoint_replay": "publish",
    "demo_context_compression": "publish",
    "demo_context_memory_acl": "publish",
    "demo_dag_conditional_branch": "join",
    "demo_dag_failure_fallback": "report",
    "demo_dag_fork_join": "join",
    "demo_dag_linear": "report",
    "demo_dag_quorum": "approve",
    "demo_dag_scatter_gather": "collect",
    "demo_docker_worker": "publish",
    "demo_event_trigger": "publish",
    "demo_executor_pool": "join",
    "demo_hostlocal_worker": "publish",
    "demo_human_approval": "publish",
    "demo_llm_tool_call": "publish",
    "demo_native_beam_agent": "publish",
    "demo_observability_trace": "publish",
    "demo_openshell_worker": "publish",
    "demo_periodic_schedule": "publish",
    "demo_python_sdk_workflow": "publish",
    "demo_resource_allocation": "publish",
    "demo_retry_recovery": "publish",
    "demo_service_health": "close",
    "demo_stream_backpressure": "consume",
}


def is_final_step(demo: str, step: str) -> bool:
    """Return true only for the node that feeds the workflow result sink."""
    return FINAL_STEPS.get(demo) == step


def request_human_approval(
    request_id: str,
    prompt: str,
    *,
    timeout_seconds: float = 15.0,
) -> dict:
    """Write a real run-store request and wait for a CLI/API response."""
    run_id = os.environ.get("MN_RUN_ID")
    runs_root = os.environ.get("MN_RUNS_ROOT")
    if not run_id or not runs_root:
        raise RuntimeError("MN_RUN_ID and MN_RUNS_ROOT are required for human approval")
    run_dir = Path(runs_root).expanduser() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    blueprint_id = os.environ.get("MN_DEMO_ID", "demo_human_approval")
    trace_id = "trc_" + secrets.token_hex(10)
    if not (run_dir / "run.json").exists():
        _write_json(
            run_dir / "run.json",
            {
                "schema_version": "mn.run.v1",
                "run_id": run_id,
                "job_id": os.environ.get("MN_JOB_ID", ""),
                "blueprint_id": blueprint_id,
                "status": "waiting_for_human",
                "trace_id": trace_id,
                "updated_at": _now(),
            },
        )
    request = {
        "ts": _now(),
        "run_id": run_id,
        "blueprint_id": blueprint_id,
        "trace_id": trace_id,
        "span_id": "spn_" + secrets.token_hex(8),
        "channel": "human",
        "type": "human_input_requested",
        "payload": {
            "request_id": request_id,
            "prompt": prompt,
            "allowed_decisions": ["approve", "reject"],
            "status": "pending",
        },
    }
    encoded = json.dumps(request, sort_keys=True) + "\n"
    for name in ("human.jsonl", "events.jsonl"):
        with (run_dir / name).open("a", encoding="utf-8") as handle:
            handle.write(encoded)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        human_path = run_dir / "human.jsonl"
        if human_path.exists():
            for line in human_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
                if event.get("type") == "human_input_received" and payload.get("request_id") == request_id:
                    return payload
        time.sleep(0.1)
    timeout = {
        **request,
        "ts": _now(),
        "type": "human_input_timeout",
        "payload": {"request_id": request_id, "status": "timed_out"},
    }
    with (run_dir / "human.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(timeout, sort_keys=True) + "\n")
    raise TimeoutError(f"human request {request_id} was not answered")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json_file(path_value: str | None, default):
    if not path_value:
        return default
    try:
        return json.loads(Path(path_value).read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_json_value(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_run_store(result: dict, events: list[dict], *, status: str = "completed") -> Path | None:
    run_id = os.environ.get("MN_RUN_ID")
    runs_root = os.environ.get("MN_RUNS_ROOT")
    if not run_id or not runs_root:
        return None

    run_dir = Path(runs_root).expanduser() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    blueprint_id = os.environ.get("MN_DEMO_ID", "unknown")
    job_id = os.environ.get("MN_JOB_ID", "")
    ts = _now()
    trace_id = "trc_" + hashlib.sha256(f"{run_id}:{job_id}".encode()).hexdigest()[:20]
    span_id = "spn_" + hashlib.sha256(f"{run_id}:final".encode()).hexdigest()[:16]
    inputs = _load_json_file(os.environ.get("MN_INPUT_FILE"), {})
    config = _load_json_value(os.environ.get("MN_BLUEPRINT_CONFIG_JSON"), {})

    normalized_events = []
    for index, event in enumerate(events):
        normalized_events.append(
            {
                "ts": ts,
                "run_id": run_id,
                "blueprint_id": blueprint_id,
                "trace_id": trace_id,
                "span_id": f"{span_id}_{index}",
                "type": event.get("type", "demo_event"),
                "payload": event.get("payload", {}),
            }
        )
    normalized_events.append(
        {
            "ts": ts,
            "run_id": run_id,
            "blueprint_id": blueprint_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "type": "run_completed" if status == "completed" else "blueprint_status",
            "payload": {"status": status},
        }
    )

    _write_json(
        run_dir / "run.json",
        {
            "schema_version": "mn.run.v1",
            "run_id": run_id,
            "job_id": job_id,
            "blueprint_id": blueprint_id,
            "status": status,
            "trace_id": trace_id,
            "updated_at": ts,
        },
    )
    _write_json(run_dir / "config.json", config)
    _write_json(run_dir / "inputs.json", inputs)
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in normalized_events),
        encoding="utf-8",
    )
    (run_dir / "errors.jsonl").write_text("", encoding="utf-8")
    (run_dir / "timeline.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "mn.timeline.v1",
                "ts": ts,
                "run_id": run_id,
                "blueprint_id": blueprint_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "type": "run_completed" if status == "completed" else "blueprint_status",
                "phase": "writing_artifacts",
                "status": status,
                "summary": "Demo run-store artifacts written.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        run_dir / "observability_summary.json",
        {
            "schema_version": "mn.observability.summary.v1",
            "run_id": run_id,
            "trace_id": trace_id,
            "status": status,
            "event_count": len(normalized_events),
            "error_count": 0,
            "artifacts": list(REQUIRED_ARTIFACTS),
        },
    )
    _write_json(run_dir / "result.json", {"schema_version": "mn.blueprint.response.v1", "result": result})
    _write_json(
        run_dir / "final_artifact.json",
        {
            "schema_version": "mn.blueprint.final_artifact.v1",
            "type": "runtime_demo_result",
            "executive_summary": f"{blueprint_id} demonstrated its focused runtime feature.",
            "recommended_action": "Inspect the feature-specific result and runtime events.",
            "confidence": 1.0,
            "evidence": result,
            "next_steps": [],
            "source_refs": ["inputs.json", "events.jsonl", "result.json"],
        },
    )
    return run_dir
