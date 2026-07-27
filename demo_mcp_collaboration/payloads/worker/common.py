from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mn_mcp_server_skill import JobExchangeStore


def config() -> dict[str, Any]:
    raw = os.environ.get("MN_BLUEPRINT_CONFIG_JSON")
    if raw:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    for parent in Path(__file__).resolve().parents:
        path = parent / "config" / "default.json"
        if path.is_file():
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                return value
    raise RuntimeError("resolved blueprint config is unavailable")


def output_root() -> Path:
    runs_root = os.environ.get("MN_RUNS_ROOT")
    run_id = os.environ.get("MN_RUN_ID")
    if runs_root and run_id:
        root = Path(runs_root).expanduser() / run_id
    elif os.environ.get("MN_JOB_OUTPUT_DIR"):
        root = Path(os.environ["MN_JOB_OUTPUT_DIR"]).expanduser()
    else:
        root = Path(os.environ.get("MN_WORKDIR") or Path.cwd()) / "outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def exchange_store() -> JobExchangeStore:
    root = output_root()
    collaboration = config()["collaboration"]
    return JobExchangeStore(
        root / "mcp_exchange.sqlite3",
        allowed_root=root,
        job_id=os.environ.get("MN_JOB_ID") or os.environ.get("MN_RUN_ID") or "local-job",
        blueprint_id=os.environ.get("MN_DEMO_ID", "demo_mcp_collaboration"),
        run_id=os.environ.get("MN_RUN_ID"),
        goal_id=str(collaboration["goal_id"]),
    )


def load_json_file(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
