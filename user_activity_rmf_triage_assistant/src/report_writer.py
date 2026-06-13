from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CANDIDATE_CONTROL_MAPPINGS = [
    "Access Control",
    "Identification and Authentication",
    "Audit and Accountability",
    "Incident Response",
    "System and Communications Protection",
    "Security Assessment and Authorization",
    "Continuous Monitoring",
    "Risk Assessment",
]

COMPLIANCE_CAVEAT = (
    "Candidate evidence mappings are provided for compliance review only; "
    "this blueprint does not prove or grant RMF, ATO, cATO, FedRAMP, CMMC, or other compliance status."
)


def build_security_decision(
    events: list[dict[str, Any]],
    risk: dict[str, Any],
    triage_state: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    return {
        "user_id": triage_state.get("user_id"),
        "user_email": triage_state.get("user_email"),
        "session_id": triage_state.get("session_id"),
        "risk_score": risk.get("risk_score"),
        "risk_level": risk.get("risk_level"),
        "signals": list(risk.get("signals") or []),
        "decision": response.get("decision"),
        "actions": response.get("actions"),
        "response_instruction": response.get("response_instruction"),
        "human_review_required": bool(response.get("human_review_required")),
        "mode": response.get("mode"),
        "triage_state": triage_state,
        "evidence_event_ids": [event.get("event_id") for event in events],
    }


def build_evidence_report(
    events: list[dict[str, Any]],
    risk: dict[str, Any],
    triage_state: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    risk_level = risk.get("risk_level")
    summary = f"{str(risk_level).title()}-risk user activity detected."
    if response.get("decision") in {"step_up_authentication_required", "require_mfa_challenge"}:
        summary += " Step-up authentication was required or recommended."

    return {
        "artifact_type": "security_user_activity_evidence_report",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "user_id": triage_state.get("user_id"),
        "user_email": triage_state.get("user_email"),
        "session_id": triage_state.get("session_id"),
        "risk_level": risk_level,
        "risk_score": risk.get("risk_score"),
        "suspicious_activity": list(risk.get("signals") or []),
        "score_details": list(risk.get("score_details") or []),
        "decision": response.get("decision"),
        "actions": response.get("actions"),
        "response_taken": response.get("response_taken"),
        "response_instruction": response.get("response_instruction"),
        "evidence": [
            {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "timestamp": event.get("timestamp"),
                "source_ip": event.get("source_ip"),
                "geo": event.get("geo"),
                "device_id": event.get("device_id"),
            }
            for event in events
        ],
        "candidate_control_mappings": CANDIDATE_CONTROL_MAPPINGS,
        "human_review_required": bool(response.get("human_review_required")),
        "summary": summary,
        "recommended_follow_up": recommended_follow_up(risk, response),
        "compliance_caveat": COMPLIANCE_CAVEAT,
    }


def write_artifacts(
    output_dir: str | Path,
    decision: dict[str, Any],
    evidence_report: dict[str, Any],
) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    decision_path = output_path / "security_decision.json"
    evidence_path = output_path / "evidence_report.json"
    summary_path = output_path / "incident_summary.md"

    decision_path.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(render_markdown_report(evidence_report), encoding="utf-8")

    return {
        "security_decision": str(decision_path),
        "evidence_report": str(evidence_path),
        "incident_summary": str(summary_path),
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    signals = "\n".join(f"- {_humanize(item)}" for item in report.get("suspicious_activity", [])) or "- None"
    evidence = "\n".join(
        f"- {item.get('event_id')}: {item.get('event_type')} at {item.get('timestamp')}"
        for item in report.get("evidence", [])
    )
    mappings = "\n".join(f"- {item}" for item in report.get("candidate_control_mappings", []))
    actions = ", ".join(report.get("actions") or [str(report.get("decision"))])
    return (
        "# Suspicious User Activity Report\n\n"
        "## Summary\n"
        f"{report.get('summary')}\n\n"
        "## Risk Level\n"
        f"{report.get('risk_level')} ({report.get('risk_score')} points)\n\n"
        "## Suspicious Signals\n"
        f"{signals}\n\n"
        "## Response Taken\n"
        f"{report.get('response_taken')} ({actions})\n\n"
        "## Evidence\n"
        f"{evidence}\n\n"
        "## Candidate RMF/ATO/cATO Evidence Mapping\n"
        f"{mappings}\n\n"
        "## Recommended Follow-up\n"
        f"{report.get('recommended_follow_up')}\n\n"
        "## Compliance Caveat\n"
        f"{report.get('compliance_caveat')}\n"
    )


def recommended_follow_up(risk: dict[str, Any], response: dict[str, Any]) -> str:
    signals = set(risk.get("signals") or [])
    if "api_key_created_after_risky_login" in signals:
        return "Review API key usage and confirm whether the credential creation was legitimate."
    if "large_data_download" in signals:
        return "Review data access scope and confirm whether the download was expected."
    if response.get("human_review_required"):
        return "Route the event package to a human security reviewer before external action."
    return "Confirm the activity with the user and retain the evidence artifact with the security review record."


def _humanize(value: str) -> str:
    return value.replace("_", " ").capitalize()
