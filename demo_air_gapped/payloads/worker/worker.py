#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mn_demo_airgap_skill import build_analysis_prompt, finalize_report

from run_store import write_run_store


MODEL = "demo-air-gapped/gemma4-e2b:latest"


def load_payload() -> dict[str, Any]:
    input_file = os.environ.get("MN_INPUT_FILE")
    if not input_file:
        return {}
    try:
        value = json.loads(Path(input_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {"input": value}


def call_local_model(system_prompt: str, user_prompt: str) -> str:
    base = (
        os.environ.get("MN_LLM_API_BASE")
        or os.environ.get("LITELLM_API_BASE")
        or "http://127.0.0.1:12434/engines/v1"
    ).rstrip("/")
    model = (
        os.environ.get("MN_LLM_MODEL")
        or os.environ.get("LITELLM_MODEL")
        or MODEL
    )
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ.get('MN_LLM_API_KEY', '')}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Bundled local model request failed: {exc}") from exc
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Bundled local model returned no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Bundled local model returned an empty response")
    return content.strip()


step = os.environ.get("MN_WORKFLOW_STEP_ID", "analyze")
incoming = load_payload()

if step == "analyze":
    system_prompt, user_prompt = build_analysis_prompt(incoming)
    result = {
        "analysis": call_local_model(system_prompt, user_prompt),
        "model": os.environ.get("MN_LLM_MODEL", MODEL),
        "network": "forbidden",
        "payload_skill": "mn-demo-airgap-skill==1.0.0",
    }
    events = [
        {
            "type": "payload_skill_loaded",
            "payload": {"package": "mn-demo-airgap-skill==1.0.0"},
        },
        {
            "type": "payload_model_called",
            "payload": {"model": result["model"], "network": "local-only"},
        },
    ]
else:
    result = finalize_report(incoming)
    events = [
        {
            "type": "airgap_report_written",
            "payload": {
                "model": result["model"],
                "network": result["network"],
            },
        }
    ]
    write_run_store(result, events)

print(
    json.dumps(
        {
            "events": events,
            "complete_step": result,
            "next_state": result,
        },
        sort_keys=True,
    )
)
