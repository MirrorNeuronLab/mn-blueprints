from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


BLUEPRINT_DIR = Path(__file__).resolve().parents[1]
RUNNER = BLUEPRINT_DIR / "payloads" / "network_monitor" / "scripts" / "run_blueprint.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("generated_network_monitor_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sample_network_events_trigger_alarm(tmp_path: Path) -> None:
    runner = _load_runner()
    result = runner.run_blueprint(
        events_path=BLUEPRINT_DIR / "inputs" / "sample_network_events.jsonl",
        config_path=BLUEPRINT_DIR / "config" / "default.json",
        runs_root=tmp_path,
        run_id="test-run",
    )

    assert result["alarm"]["alarm_status"] == "ALARM"
    assert result["alarm"]["risk_level"] in {"HIGH", "CRITICAL"}
    assert result["alarm"]["requires_human_approval_before_response"] is True
    assert Path(result["artifacts"]["final_artifact"]).exists()
