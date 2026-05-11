from __future__ import annotations

from typing import Any


DEFAULT_THRESHOLDS = {
    "low": 0,
    "medium": 25,
    "high": 50,
    "critical": 80,
}

DEFAULT_SIGNAL_WEIGHTS = {
    "new_device_login": 15,
    "new_location_login": 15,
    "impossible_travel": 40,
    "repeated_failed_logins": 20,
    "mfa_disabled": 40,
    "api_key_created_after_risky_login": 25,
    "large_data_download": 30,
    "privilege_change": 35,
    "sensitive_file_access_after_risky_login": 25,
    "known_safe_device": -10,
    "mfa_success": -10,
}

POSITIVE_SIGNALS = {
    "new_device_login",
    "new_location_login",
    "impossible_travel",
    "repeated_failed_logins",
    "mfa_disabled",
    "api_key_created_after_risky_login",
    "large_data_download",
    "privilege_change",
    "sensitive_file_access_after_risky_login",
}


def score_events(events: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    weights = dict(DEFAULT_SIGNAL_WEIGHTS)
    weights.update(config.get("signal_weights") or {})
    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds.update(config.get("risk_thresholds") or {})

    ordered_events = sorted(events, key=lambda item: item.get("timestamp", ""))
    applied_signals: set[str] = set()
    positive_signals: list[str] = []
    details: list[dict[str, Any]] = []
    failed_login_streak = 0
    risky_login_seen = False

    for event in ordered_events:
        event_type = event.get("event_type", "")
        event_signals: list[str] = []
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}

        if event_type == "login_failed":
            failed_login_streak += 1
            continue

        if event_type in {"login_success", "new_device_login", "new_location_login", "unusual_ip"}:
            if failed_login_streak >= 5:
                event_signals.append("repeated_failed_logins")
            failed_login_streak = 0

            if event_type == "new_device_login" or _looks_unknown_device(event):
                event_signals.append("new_device_login")
            if event_type == "new_location_login":
                event_signals.append("new_location_login")
            if event_type == "unusual_ip":
                event_signals.append("new_location_login")
            if metadata.get("mfa_used") is True:
                event_signals.append("mfa_success")
            if _looks_known_safe_device(event):
                event_signals.append("known_safe_device")

        if event_type == "impossible_travel":
            event_signals.append("impossible_travel")
        if event_type == "mfa_disabled":
            event_signals.append("mfa_disabled")
        if event_type in {"role_change", "permission_change", "admin_action"}:
            event_signals.append("privilege_change")
        if event_type == "api_key_created" and risky_login_seen:
            event_signals.append("api_key_created_after_risky_login")
        if event_type == "large_data_download" or _large_download(metadata):
            event_signals.append("large_data_download")
        if event_type == "sensitive_file_access" and risky_login_seen:
            event_signals.append("sensitive_file_access_after_risky_login")

        for signal in event_signals:
            if signal in applied_signals:
                continue
            applied_signals.add(signal)
            points = int(weights.get(signal, 0))
            details.append(
                {
                    "signal": signal,
                    "points": points,
                    "event_id": event.get("event_id"),
                    "event_type": event_type,
                    "timestamp": event.get("timestamp"),
                }
            )
            if signal in POSITIVE_SIGNALS:
                positive_signals.append(signal)
                if signal in {"new_device_login", "new_location_login", "impossible_travel", "repeated_failed_logins"}:
                    risky_login_seen = True

    raw_score = sum(item["points"] for item in details)
    risk_score = max(0, raw_score)
    return {
        "risk_score": risk_score,
        "raw_score": raw_score,
        "risk_level": risk_level(risk_score, thresholds),
        "signals": positive_signals,
        "score_details": details,
        "thresholds": thresholds,
    }


def risk_level(score: int | float, thresholds: dict[str, Any] | None = None) -> str:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    if score >= int(thresholds.get("critical", 80)):
        return "CRITICAL"
    if score >= int(thresholds.get("high", 50)):
        return "HIGH"
    if score >= int(thresholds.get("medium", 25)):
        return "MEDIUM"
    return "LOW"


def _looks_unknown_device(event: dict[str, Any]) -> bool:
    device_id = str(event.get("device_id") or "").lower()
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    return "unknown" in device_id or metadata.get("known_device") is False


def _looks_known_safe_device(event: dict[str, Any]) -> bool:
    device_id = str(event.get("device_id") or "").lower()
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    return "known" in device_id or metadata.get("known_safe_device") is True or metadata.get("known_device") is True


def _large_download(metadata: dict[str, Any]) -> bool:
    try:
        return int(metadata.get("file_count", 0)) >= 100
    except (TypeError, ValueError):
        return False

