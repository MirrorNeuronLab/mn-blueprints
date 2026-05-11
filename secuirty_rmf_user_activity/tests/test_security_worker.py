from __future__ import annotations

import json
import sys
from pathlib import Path


BLUEPRINT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BLUEPRINT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from event_loader import load_events
from main import run_worker
from normalizer import normalize_event, normalize_events
from report_writer import build_evidence_report, build_security_decision, write_artifacts
from response_policy import choose_response
from risk_scorer import score_events
from state_machine import build_triage_state


def test_event_normalization_handles_missing_optional_fields() -> None:
    event = normalize_event(
        {
            "event_id": "evt_min",
            "timestamp": "2026-05-11T14:30:00Z",
            "event_type": "Login Success",
            "user_id": "user_123",
        }
    )

    assert event["event_type"] == "login_success"
    assert event["session_id"] == "unknown_session"
    assert event["geo"] == {"country": "", "region": "", "city": ""}
    assert event["metadata"] == {}


def test_high_risk_sample_scores_to_step_up_authentication() -> None:
    raw_events = load_events(BLUEPRINT_DIR / "inputs" / "sample_events_high_risk.jsonl")
    events = normalize_events(raw_events)
    config = json.loads((BLUEPRINT_DIR / "config.example.json").read_text())

    risk = score_events(events, config)
    state = build_triage_state(events, risk)
    response = choose_response(risk, state, config)

    assert risk["risk_level"] == "HIGH"
    assert risk["risk_score"] == 65
    assert "new_location_login" in risk["signals"]
    assert "new_device_login" in risk["signals"]
    assert "api_key_created_after_risky_login" in risk["signals"]
    assert "large_data_download" in risk["signals"]
    assert state["state"] == "High Risk"
    assert response["decision"] == "step_up_authentication_required"
    assert response["response_instruction"]["dry_run"] is True
    assert response["response_instruction"]["execute_external_action"] is False


def test_report_writer_includes_all_source_event_ids_and_caveat(tmp_path: Path) -> None:
    raw_events = load_events(BLUEPRINT_DIR / "inputs" / "sample_events_high_risk.jsonl")
    events = normalize_events(raw_events)
    config = json.loads((BLUEPRINT_DIR / "config.example.json").read_text())
    risk = score_events(events, config)
    state = build_triage_state(events, risk)
    response = choose_response(risk, state, config)
    state = build_triage_state(events, risk, response_action=response["decision"])
    decision = build_security_decision(events, risk, state, response)
    report = build_evidence_report(events, risk, state, response)

    paths = write_artifacts(tmp_path, decision, report)

    saved_report = json.loads(Path(paths["evidence_report"]).read_text())
    assert [item["event_id"] for item in saved_report["evidence"]] == [
        "evt_001",
        "evt_002",
        "evt_003",
        "evt_004",
    ]
    assert "Candidate evidence mappings" in saved_report["compliance_caveat"]
    assert "does not prove or grant" in saved_report["compliance_caveat"]
    assert "Access Control" in saved_report["candidate_control_mappings"]
    assert Path(paths["incident_summary"]).exists()


def test_worker_runs_end_to_end(tmp_path: Path) -> None:
    result = run_worker(
        events_path=BLUEPRINT_DIR / "inputs" / "sample_events_high_risk.jsonl",
        config_path=BLUEPRINT_DIR / "config.example.json",
        output_dir=tmp_path,
    )

    assert result["events_processed"] == 4
    assert result["decision"]["decision"] == "step_up_authentication_required"
    assert Path(result["artifacts"]["security_decision"]).exists()
    assert Path(result["artifacts"]["evidence_report"]).exists()
    assert Path(result["artifacts"]["incident_summary"]).exists()

