from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import config, load_json_file, output_root, write_json


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
    "peer_exchange.json",
    "mcp_exchange.sqlite3",
)


def write_run_store(result: dict[str, Any], events: list[dict[str, Any]]) -> Path:
    root = output_root()
    run_id = os.environ.get("MN_RUN_ID") or root.name
    job_id = os.environ.get("MN_JOB_ID", "")
    blueprint_id = os.environ.get("MN_DEMO_ID", "demo_mcp_collaboration")
    timestamp = _now()
    trace_id = "trc_" + hashlib.sha256(f"{run_id}:{job_id}".encode()).hexdigest()[:20]
    span_id = "spn_" + hashlib.sha256(f"{run_id}:final".encode()).hexdigest()[:16]
    inputs = load_json_file(Path(os.environ.get("MN_INPUT_FILE", "")), {})

    normalized_events = [
        {
            "ts": timestamp,
            "run_id": run_id,
            "blueprint_id": blueprint_id,
            "trace_id": trace_id,
            "span_id": f"{span_id}_{index}",
            "type": event.get("type", "mcp_collaboration_event"),
            "payload": event.get("payload", {}),
        }
        for index, event in enumerate(events)
    ]
    normalized_events.append(
        {
            "ts": timestamp,
            "run_id": run_id,
            "blueprint_id": blueprint_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "type": "run_completed",
            "payload": {"status": "completed"},
        }
    )

    write_json(
        root / "run.json",
        {
            "schema_version": "mn.run.v1",
            "run_id": run_id,
            "job_id": job_id,
            "blueprint_id": blueprint_id,
            "status": "completed",
            "trace_id": trace_id,
            "updated_at": timestamp,
        },
    )
    write_json(root / "config.json", config())
    write_json(root / "inputs.json", inputs)
    (root / "events.jsonl").write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in normalized_events),
        encoding="utf-8",
    )
    (root / "errors.jsonl").write_text("", encoding="utf-8")
    (root / "timeline.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "mn.timeline.v1",
                "ts": timestamp,
                "run_id": run_id,
                "blueprint_id": blueprint_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "type": "run_completed",
                "phase": "writing_artifacts",
                "status": "completed",
                "summary": "Cross-job MCP collaboration evidence written.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        root / "observability_summary.json",
        {
            "schema_version": "mn.observability.summary.v1",
            "run_id": run_id,
            "trace_id": trace_id,
            "status": "completed",
            "event_count": len(normalized_events),
            "error_count": 0,
            "artifacts": list(REQUIRED_ARTIFACTS),
        },
    )
    write_json(
        root / "result.json",
        {"schema_version": "mn.blueprint.response.v1", "result": result},
    )
    write_json(
        root / "final_artifact.json",
        {
            "schema_version": "mn.blueprint.final_artifact.v1",
            "type": "runtime_demo_result",
            "executive_summary": (
                "This job exposed its own status, knowledge, and staged or final "
                "results over MCP and read matching peer exchanges."
            ),
            "recommended_action": "Inspect peer_exchange.json and the local MCP update journal.",
            "confidence": 1.0,
            "evidence": result,
            "next_steps": [],
            "source_refs": [
                "inputs.json",
                "events.jsonl",
                "peer_exchange.json",
                "mcp_exchange.sqlite3",
                "result.json",
            ],
        },
    )
    return root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
