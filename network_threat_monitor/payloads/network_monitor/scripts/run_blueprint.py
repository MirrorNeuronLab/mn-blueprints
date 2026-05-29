#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BLUEPRINT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_EVENTS = BLUEPRINT_DIR / "inputs" / "sample_network_events.jsonl"
DEFAULT_CONFIG = BLUEPRINT_DIR / "config" / "default.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"event line must be an object: {line}")
            events.append(value)
    return events


def score_events(events: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    monitor = config.get("network_monitor", {})
    weights = monitor.get("signal_weights", {})
    signals: list[dict[str, Any]] = []
    unique_ports_by_src: dict[str, set[int]] = {}

    for event in events:
        event_id = str(event.get("event_id", "unknown"))
        event_type = str(event.get("event_type", "")).lower()
        src_ip = str(event.get("src_ip", "unknown"))
        dst_port = int(event.get("dst_port", 0) or 0)
        if dst_port:
            unique_ports_by_src.setdefault(src_ip, set()).add(dst_port)

        if dst_port in {23, 135, 139, 445, 3389, 4444, 5555, 6667}:
            signals.append(_signal("suspicious_remote_port", event_id, weights, f"remote port {dst_port} is commonly abused"))
        if dst_port in {22, 3389, 5900} and event.get("direction") == "inbound":
            signals.append(_signal("admin_protocol_exposed", event_id, weights, f"admin protocol exposed on port {dst_port}"))
        if int(event.get("bytes_out", 0) or 0) >= 5_000_000:
            signals.append(_signal("large_outbound_transfer", event_id, weights, "large outbound transfer from monitored host"))
        if event_type == "dns" and _suspicious_domain(str(event.get("query", ""))):
            signals.append(_signal("suspicious_dns", event_id, weights, "DNS query resembles malware or command-and-control traffic"))
        label = " ".join(str(event.get(key, "")) for key in ("label", "threat_label", "process")).lower()
        if any(word in label for word in ("malware", "beacon", "trojan", "spamware", "ransom")):
            signals.append(_signal("known_malware_label", event_id, weights, "endpoint or process label indicates possible malware"))
        if event_type == "auth" and int(event.get("failed_attempts", 0) or 0) >= 10:
            signals.append(_signal("failed_login_burst", event_id, weights, "many failed login attempts observed"))

    for src_ip, ports in unique_ports_by_src.items():
        if len(ports) >= 8:
            signals.append(
                {
                    "signal": "port_scan",
                    "event_id": f"src:{src_ip}",
                    "score": int(weights.get("port_scan", 30)),
                    "reason": f"{src_ip} touched {len(ports)} distinct destination ports",
                }
            )

    risk_score = sum(item["score"] for item in signals)
    thresholds = monitor.get("risk_thresholds", {})
    risk_level = "LOW"
    if risk_score >= int(thresholds.get("critical", 90)):
        risk_level = "CRITICAL"
    elif risk_score >= int(thresholds.get("high", 60)):
        risk_level = "HIGH"
    elif risk_score >= int(thresholds.get("medium", 25)):
        risk_level = "MEDIUM"
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "signals": signals,
        "source_event_ids": sorted({item["event_id"] for item in signals}),
    }


def _signal(name: str, event_id: str, weights: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "signal": name,
        "event_id": event_id,
        "score": int(weights.get(name, 0)),
        "reason": reason,
    }


def _suspicious_domain(domain: str) -> bool:
    value = domain.lower()
    if any(word in value for word in ("malware", "beacon", "botnet", "spam", "phish", "control")):
        return True
    labels = value.split(".")
    return any(len(label) > 24 or label.count("-") >= 3 for label in labels)


def build_alarm(events: list[dict[str, Any]], risk: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    policy = config.get("network_monitor", {}).get("alert_policy", {})
    risk_level = str(risk["risk_level"]).lower()
    actions = list(policy.get(risk_level, ["log_only"]))
    if risk["risk_level"] in {"HIGH", "CRITICAL"}:
        alarm_status = "ALARM"
    elif risk["risk_level"] == "MEDIUM":
        alarm_status = "WATCH"
    else:
        alarm_status = "OK"
    return {
        "schema_version": "mn.security.network_alarm.v1",
        "alarm_status": alarm_status,
        "risk_level": risk["risk_level"],
        "risk_score": risk["risk_score"],
        "recommended_actions": actions,
        "requires_human_approval_before_response": True,
        "dry_run": True,
        "event_count": len(events),
        "source_event_ids": risk["source_event_ids"],
        "signals": risk["signals"],
        "operator_message": _operator_message(alarm_status, risk),
    }


def _operator_message(alarm_status: str, risk: dict[str, Any]) -> str:
    if alarm_status == "ALARM":
        return "Suspicious network behavior detected. Review source events before blocking, isolating, or changing policy."
    if alarm_status == "WATCH":
        return "Potentially suspicious behavior detected. Continue monitoring and review the triggered signals."
    return "No actionable suspicious behavior detected in the provided sample."


def write_run_store(run_dir: Path, config: dict[str, Any], events: list[dict[str, Any]], alarm: dict[str, Any]) -> dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "blueprint": config["identity"]["blueprint_id"],
        "status": "completed",
        "alarm": alarm,
        "generated_at": now,
    }
    artifacts = {
        "run": run_dir / "run.json",
        "config": run_dir / "config.json",
        "inputs": run_dir / "inputs.json",
        "events": run_dir / "events.jsonl",
        "result": run_dir / "result.json",
        "final_artifact": run_dir / "final_artifact.json",
    }
    artifacts["run"].write_text(json.dumps({"run_id": run_dir.name, "status": "completed", "updated_at": now}, indent=2) + "\n", encoding="utf-8")
    artifacts["config"].write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts["inputs"].write_text(json.dumps({"events": events}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts["events"].write_text("\n".join(json.dumps({"type": "source_event", "event": event}, sort_keys=True) for event in events) + "\n", encoding="utf-8")
    artifacts["result"].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts["final_artifact"].write_text(json.dumps(alarm, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {name: str(path) for name, path in artifacts.items()}


def run_blueprint(
    *,
    events_path: str | Path = DEFAULT_EVENTS,
    config_path: str | Path = DEFAULT_CONFIG,
    runs_root: str | Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    config = load_json(Path(config_path))
    events = load_events(Path(events_path))
    risk = score_events(events, config)
    alarm = build_alarm(events, risk, config)
    run_root = Path(runs_root or os.path.expanduser(config.get("outputs", {}).get("run_root", "~/.mn/runs"))).expanduser()
    final_run_id = run_id or f"{config['identity']['blueprint_id']}-mock"
    artifacts = write_run_store(run_root / final_run_id, config, events, alarm)
    return {
        "blueprint": config["identity"]["blueprint_id"],
        "run_id": final_run_id,
        "risk": risk,
        "alarm": alarm,
        "artifacts": artifacts,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the generated network monitoring blueprint.")
    parser.add_argument("--events", default=str(DEFAULT_EVENTS), help="Path to JSONL network events.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config/default.json.")
    parser.add_argument("--runs-root", default=None, help="Run-store root. Defaults to config outputs.run_root.")
    parser.add_argument("--run-id", default=None, help="Optional deterministic run id.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = run_blueprint(
        events_path=args.events,
        config_path=args.config,
        runs_root=args.runs_root,
        run_id=args.run_id,
    )
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True))


if __name__ == "__main__":
    main()
