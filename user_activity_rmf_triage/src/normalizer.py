from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SUPPORTED_EVENT_TYPES = {
    "login_success",
    "login_failed",
    "logout",
    "new_device_login",
    "new_location_login",
    "impossible_travel",
    "unusual_ip",
    "mfa_disabled",
    "mfa_challenge_failed",
    "password_reset",
    "role_change",
    "permission_change",
    "api_key_created",
    "api_key_used",
    "large_data_download",
    "admin_action",
    "session_refresh",
    "sensitive_file_access",
}

KNOWN_FIELDS = {
    "event_id",
    "timestamp",
    "event_type",
    "user_id",
    "user_email",
    "session_id",
    "source_ip",
    "geo",
    "device_id",
    "user_agent",
    "resource",
    "metadata",
}


def normalize_events(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_event(raw_event, index=index) for index, raw_event in enumerate(raw_events, start=1)]


def normalize_event(raw_event: dict[str, Any], *, index: int = 1) -> dict[str, Any]:
    metadata = dict(raw_event.get("metadata") or {})
    for key, value in raw_event.items():
        if key not in KNOWN_FIELDS:
            metadata.setdefault(key, value)

    event_type = str(raw_event.get("event_type") or raw_event.get("type") or "unknown").strip().lower()
    event_type = event_type.replace("-", "_").replace(" ", "_")
    if event_type not in SUPPORTED_EVENT_TYPES:
        metadata.setdefault("unsupported_event_type", event_type)

    geo = raw_event.get("geo") if isinstance(raw_event.get("geo"), dict) else {}
    return {
        "event_id": str(raw_event.get("event_id") or f"evt_{index:03d}"),
        "timestamp": normalize_timestamp(raw_event.get("timestamp")),
        "event_type": event_type,
        "user_id": str(raw_event.get("user_id") or raw_event.get("actor_id") or "unknown_user"),
        "user_email": str(raw_event.get("user_email") or raw_event.get("email") or ""),
        "session_id": str(raw_event.get("session_id") or raw_event.get("session") or "unknown_session"),
        "source_ip": str(raw_event.get("source_ip") or raw_event.get("ip") or ""),
        "geo": {
            "country": str(geo.get("country") or ""),
            "region": str(geo.get("region") or ""),
            "city": str(geo.get("city") or ""),
        },
        "device_id": str(raw_event.get("device_id") or raw_event.get("device") or ""),
        "user_agent": str(raw_event.get("user_agent") or ""),
        "resource": str(raw_event.get("resource") or "unknown"),
        "metadata": metadata,
    }


def normalize_timestamp(value: Any) -> str:
    if not value:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
