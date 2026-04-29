from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

vendored_skills = Path(__file__).resolve().parents[1] / "mn_skills"
if vendored_skills.exists():
    sys.path.insert(0, str(vendored_skills))


def load_local_env() -> None:
    for env_path in (
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[1] / "mn_skills" / ".env",
    ):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            os.environ.setdefault(key.strip(), value)


load_local_env()

try:
    from mn_email_send_resend_skill import dry_run_email as skill_dry_run_email
    from mn_email_send_resend_skill import send_resend_email
except ImportError:
    skill_dry_run_email = None
    send_resend_email = None


def dry_run_email(request: dict[str, Any]) -> dict[str, Any]:
    if skill_dry_run_email is not None:
        return skill_dry_run_email(request)
    return {
        "status": "sent",
        "provider_id": "dry_run",
        "http_status": 200,
        "dry_run": True,
    }


def post_email(request: dict[str, Any]) -> dict[str, Any]:
    if send_resend_email is not None:
        resend_delivery = send_resend_email(request)
        if resend_delivery.get("reason") != "missing_resend_credentials":
            return resend_delivery

    api_key = os.environ.get("AGENTMAIL_API_KEY", "").strip()
    inbox_id = os.environ.get("AGENTMAIL_INBOX", "").strip()
    
    if not api_key or not inbox_id:
        return {"status": "skipped", "reason": "missing_agentmail_credentials"}

    to_emails = request.get("to", [])
    if isinstance(to_emails, list):
        to_str = ", ".join(to_emails)
    else:
        to_str = to_emails

    body = json.dumps(
        {
            "to": to_str,
            "subject": request.get("subject", ""),
            "text": request.get("text", ""),
            "html": request.get("html", None),
            "headers": request.get("headers", {}),
        }
    ).encode("utf-8")
    http_request = urllib.request.Request(
        f"https://api.agentmail.to/v0/inboxes/{urllib.parse.quote(inbox_id, safe='')}/messages/send",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "status": "sent",
            "provider_id": payload.get("message_id") or payload.get("id"),
            "http_status": response.status,
        }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"status": "failed", "http_status": exc.code, "error": raw}
    except urllib.error.URLError as exc:
        return {"status": "failed", "error": str(exc)}

def _env_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def post_slack_message(text: str, *, channel: str | None = None) -> dict[str, Any]:
    token = _env_value("MIRROR_NEURON_SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN")
    channel = (
        channel
        or _env_value("MIRROR_NEURON_SLACK_DEFAULT_CHANNEL", "SLACK_DEFAULT_CHANNEL")
    ).strip()
    if not token:
        return {
            "status": "skipped",
            "reason": "missing_slack_bot_token",
            "channel": channel,
        }
    if not channel:
        return {
            "status": "skipped",
            "reason": "missing_slack_channel",
            "channel": channel,
        }

    body = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    http_request = urllib.request.Request(
        _env_value(
            "MIRROR_NEURON_SLACK_API_BASE_URL",
            "SLACK_API_BASE_URL",
            default="https://slack.com/api/chat.postMessage",
        ),
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {
                "status": "sent" if payload.get("ok") else "failed",
                "channel": channel,
                "http_status": response.status,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(raw)
        except json.JSONDecodeError:
            details = {"raw": raw}
        return {
            "status": "failed",
            "channel": channel,
            "http_status": exc.code,
            "error": details,
        }
    except urllib.error.URLError as exc:
        return {"status": "failed", "channel": channel, "error": str(exc)}
