from __future__ import annotations

from typing import Any


STATE_BY_RISK_LEVEL = {
    "LOW": "Normal",
    "MEDIUM": "Watch",
    "HIGH": "High Risk",
    "CRITICAL": "Critical",
}


def build_triage_state(events: list[dict[str, Any]], risk: dict[str, Any], response_action: str | None = None) -> dict[str, Any]:
    latest = sorted(events, key=lambda item: item.get("timestamp", ""))[-1] if events else {}
    risk_level = str(risk.get("risk_level") or "LOW")
    state = STATE_BY_RISK_LEVEL.get(risk_level, "Normal")

    if _reauth_completed(events) and state in {"High Risk", "Critical"}:
        state = "Resolved"

    return {
        "user_id": latest.get("user_id", "unknown_user"),
        "user_email": latest.get("user_email", ""),
        "session_id": latest.get("session_id", "unknown_session"),
        "current_risk_score": risk.get("risk_score", 0),
        "current_risk_level": risk_level,
        "state": state,
        "open_signals": list(risk.get("signals") or []),
        "last_action": response_action or "pending_response_policy",
        "last_updated": latest.get("timestamp"),
    }


def _reauth_completed(events: list[dict[str, Any]]) -> bool:
    for event in events:
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        if event.get("event_type") == "login_success" and metadata.get("step_up_completed") is True:
            return True
        if event.get("event_type") == "login_success" and metadata.get("re_authenticated") is True:
            return True
    return False

