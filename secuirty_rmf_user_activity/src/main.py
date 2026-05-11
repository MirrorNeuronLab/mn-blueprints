#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .event_loader import load_events
    from .normalizer import normalize_events
    from .report_writer import build_evidence_report, build_security_decision, write_artifacts
    from .response_policy import choose_response
    from .risk_scorer import score_events
    from .state_machine import build_triage_state
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from event_loader import load_events
    from normalizer import normalize_events
    from report_writer import build_evidence_report, build_security_decision, write_artifacts
    from response_policy import choose_response
    from risk_scorer import score_events
    from state_machine import build_triage_state


BLUEPRINT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS = BLUEPRINT_DIR / "inputs" / "sample_events_high_risk.jsonl"
DEFAULT_CONFIG = BLUEPRINT_DIR / "config.example.json"
DEFAULT_OUTPUT_DIR = BLUEPRINT_DIR / "outputs"


def run_worker(
    *,
    events_path: str | Path = DEFAULT_EVENTS,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    mode: str | None = None,
) -> dict[str, Any]:
    config = load_worker_config(config_path)
    if mode:
        config["mode"] = mode

    raw_events = load_events(events_path)
    events = normalize_events(raw_events)
    risk = score_events(events, config)
    initial_state = build_triage_state(events, risk)
    response = choose_response(risk, initial_state, config)
    triage_state = build_triage_state(events, risk, response_action=response["decision"])
    decision = build_security_decision(events, risk, triage_state, response)
    evidence_report = build_evidence_report(events, risk, triage_state, response)
    artifact_paths = write_artifacts(output_dir, decision, evidence_report)

    return {
        "blueprint": "secuirty_rmf_user_activity",
        "canonical_spec_name": "security_user_activity_response_worker",
        "events_processed": len(events),
        "risk": risk,
        "triage_state": triage_state,
        "decision": decision,
        "evidence_report": evidence_report,
        "artifacts": artifact_paths,
    }


def load_worker_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if isinstance(value.get("security_worker"), dict):
        worker_config = dict(value["security_worker"])
        if "mode" in value:
            worker_config.setdefault("mode", value["mode"])
        return worker_config
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the security user activity response worker.")
    parser.add_argument("--events", default=str(DEFAULT_EVENTS), help="Path to JSON or JSONL user activity events.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to worker config JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for output artifacts.")
    parser.add_argument("--mode", choices=["dry_run", "execute"], help="Override configured mode.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON instead of pretty JSON.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = run_worker(
        events_path=args.events,
        config_path=args.config,
        output_dir=args.output_dir,
        mode=args.mode,
    )
    indent = None if args.compact else 2
    print(json.dumps(result, indent=indent, sort_keys=True))


if __name__ == "__main__":
    main()

