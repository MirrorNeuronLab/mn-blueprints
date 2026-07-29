"""Small standard run-store writer used by the deterministic dynamic demo."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_file(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(Path(value).read_text(encoding="utf-8"))
    except Exception:
        return default


def _json_value(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _write(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_run_store(final_artifact: dict, events: list[dict]) -> Path | None:
    run_id = os.environ.get("MN_RUN_ID")
    runs_root = os.environ.get("MN_RUNS_ROOT")
    if not run_id or not runs_root:
        return None
    run_dir = Path(runs_root).expanduser() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    job_id = os.environ.get("MN_JOB_ID", "")
    blueprint_id = "demo_dynamic_workflow"
    ts = _now()
    trace_id = "trc_" + hashlib.sha256(f"{run_id}:{job_id}".encode()).hexdigest()[:20]
    inputs = _json_file(os.environ.get("MN_INPUT_FILE"), {})
    config = _json_value(os.environ.get("MN_BLUEPRINT_CONFIG_JSON"), {})
    normalized = [
        {
            "ts": ts,
            "run_id": run_id,
            "blueprint_id": blueprint_id,
            "trace_id": trace_id,
            "span_id": f"spn_dynamic_{index}",
            "type": event.get("type", "demo_event"),
            "payload": event.get("payload", {}),
        }
        for index, event in enumerate(events)
    ]
    normalized.append(
        {
            "ts": ts,
            "run_id": run_id,
            "blueprint_id": blueprint_id,
            "trace_id": trace_id,
            "span_id": "spn_dynamic_final",
            "type": "run_completed",
            "payload": {"status": "completed"},
        }
    )
    _write(
        run_dir / "run.json",
        {
            "schema_version": "mn.run.v1",
            "run_id": run_id,
            "job_id": job_id,
            "blueprint_id": blueprint_id,
            "status": "completed",
            "trace_id": trace_id,
            "updated_at": ts,
        },
    )
    _write(run_dir / "config.json", config)
    _write(run_dir / "inputs.json", inputs)
    _write(run_dir / "result.json", final_artifact)
    _write(run_dir / "final_artifact.json", final_artifact)
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in normalized),
        encoding="utf-8",
    )
    (run_dir / "errors.jsonl").write_text("", encoding="utf-8")
    (run_dir / "timeline.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "mn.timeline.v1",
                "ts": ts,
                "run_id": run_id,
                "type": "dynamic_workflow_completed",
                "graph_revision": final_artifact["graph_revision"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _write(
        run_dir / "observability_summary.json",
        {
            "schema_version": "mn.observability.summary.v1",
            "run_id": run_id,
            "trace_id": trace_id,
            "status": "completed",
            "event_count": len(normalized),
            "graph_revision": final_artifact["graph_revision"],
        },
    )
    return run_dir
