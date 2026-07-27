from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {}
    try:
        value = json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {"value": value}


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_run_store(result: dict[str, Any], events: list[dict[str, Any]]) -> Path | None:
    run_id = os.environ.get("MN_RUN_ID")
    runs_root = os.environ.get("MN_RUNS_ROOT")
    if not run_id or not runs_root:
        return None
    run_dir = Path(runs_root).expanduser() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    ts = _now()
    blueprint_id = "demo_air_gapped"
    job_id = os.environ.get("MN_JOB_ID", "")
    trace_id = "trc_" + hashlib.sha256(f"{run_id}:{job_id}".encode()).hexdigest()[:20]
    normalized = [
        {
            "blueprint_id": blueprint_id,
            "payload": event.get("payload", {}),
            "run_id": run_id,
            "trace_id": trace_id,
            "ts": ts,
            "type": event.get("type", "demo_event"),
        }
        for event in events
    ]
    normalized.append(
        {
            "blueprint_id": blueprint_id,
            "payload": {"status": "completed"},
            "run_id": run_id,
            "trace_id": trace_id,
            "ts": ts,
            "type": "run_completed",
        }
    )
    _write(
        run_dir / "run.json",
        {
            "blueprint_id": blueprint_id,
            "job_id": job_id,
            "run_id": run_id,
            "schema_version": "mn.run.v1",
            "status": "completed",
            "trace_id": trace_id,
            "updated_at": ts,
        },
    )
    _write(run_dir / "config.json", json.loads(os.environ.get("MN_BLUEPRINT_CONFIG_JSON", "{}")))
    _write(run_dir / "inputs.json", _read_json(os.environ.get("MN_INPUT_FILE")))
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in normalized),
        encoding="utf-8",
    )
    (run_dir / "errors.jsonl").write_text("", encoding="utf-8")
    (run_dir / "timeline.jsonl").write_text(
        json.dumps(
            {
                "blueprint_id": blueprint_id,
                "phase": "writing_artifacts",
                "run_id": run_id,
                "status": "completed",
                "trace_id": trace_id,
                "ts": ts,
                "type": "run_completed",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _write(
        run_dir / "observability_summary.json",
        {
            "error_count": 0,
            "event_count": len(normalized),
            "run_id": run_id,
            "schema_version": "mn.observability.summary.v1",
            "status": "completed",
            "trace_id": trace_id,
        },
    )
    _write(
        run_dir / "result.json",
        {"result": result, "schema_version": "mn.blueprint.response.v1"},
    )
    _write(
        run_dir / "final_artifact.json",
        {
            "confidence": 0.8,
            "evidence": result,
            "executive_summary": result["analysis"],
            "next_steps": [],
            "recommended_action": "Perform the three safe local checks from the analysis.",
            "schema_version": "mn.blueprint.final_artifact.v1",
            "source_refs": ["inputs.json", "events.jsonl", "result.json"],
            "type": "air_gapped_analysis",
        },
    )
    return run_dir
