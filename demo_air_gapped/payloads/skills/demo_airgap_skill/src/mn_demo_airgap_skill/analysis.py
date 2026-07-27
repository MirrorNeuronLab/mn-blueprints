from __future__ import annotations

from typing import Any


def extract_note(payload: Any) -> str:
    """Find a bounded note in common MirrorNeuron message envelopes."""
    if isinstance(payload, str):
        return payload[:8_000]
    if isinstance(payload, dict):
        for key in ("note", "text", "input"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:8_000]
        for key in ("complete_step", "next_state", "payload", "result"):
            value = payload.get(key)
            if value is not None:
                note = extract_note(value)
                if note:
                    return note
    if isinstance(payload, list):
        for value in payload:
            note = extract_note(value)
            if note:
                return note
    return "No note was supplied."


def build_analysis_prompt(payload: Any) -> tuple[str, str]:
    note = extract_note(payload)
    system = (
        "You are an offline operations analyst. Work only from the supplied note. "
        "Give a concise assessment with likely causes, exactly three safe local "
        "checks, and any uncertainty. Do not suggest internet lookups."
    )
    user = f"Analyze this local operational note:\n\n{note}"
    return system, user


def finalize_report(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        for key in ("complete_step", "next_state", "payload", "result"):
            value = payload.get(key)
            if isinstance(value, dict) and value.get("analysis"):
                payload = value
                break
    if not isinstance(payload, dict):
        payload = {"analysis": str(payload)}
    return {
        "analysis": str(payload.get("analysis") or "No analysis was returned."),
        "model": str(
            payload.get("model") or "demo-air-gapped/gemma4-e2b:latest"
        ),
        "network": "forbidden",
        "payload_skill": "mn-demo-airgap-skill==1.0.0",
        "status": "completed",
    }
