from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from agentmail import AgentMail

def post_email(request: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("AGENTMAIL_API_KEY", "").strip()
    inbox_id = os.environ.get("AGENTMAIL_INBOX", "").strip()
    
    if not api_key or not inbox_id:
        return {"status": "skipped", "reason": "missing_agentmail_credentials"}

    client = AgentMail(api_key=api_key)

    to_emails = request.get("to", [])
    if isinstance(to_emails, list):
        to_str = ", ".join(to_emails)
    else:
        to_str = to_emails

    try:
        sent = client.inboxes.messages.send(
            inbox_id=inbox_id,
            to=to_str,
            subject=request.get("subject", ""),
            text=request.get("text", ""),
            html=request.get("html", None)
        )
        return {
            "status": "sent",
            "provider_id": sent.message_id,
            "http_status": 200,
        }
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}

def post_slack_message(text: str) -> dict[str, Any]:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel = os.environ.get("SLACK_DEFAULT_CHANNEL", "#claw").strip() or "#claw"
    if not token:
        return {
            "status": "skipped",
            "reason": "missing_slack_bot_token",
            "channel": channel,
        }

    body = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    http_request = urllib.request.Request(
        os.environ.get("SLACK_API_BASE_URL", "https://slack.com/api/chat.postMessage"),
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
