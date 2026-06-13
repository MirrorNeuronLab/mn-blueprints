from __future__ import annotations

from typing import Any


DEFAULT_RESPONSE_POLICY = {
    "low": ["log_only"],
    "medium": ["notify_admin"],
    "high": ["step_up_authentication_required"],
    "critical": ["require_mfa_challenge", "notify_admin", "create_incident_ticket"],
}


def choose_response(risk: dict[str, Any], triage_state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    mode = str(config.get("mode") or "dry_run")
    policy = dict(DEFAULT_RESPONSE_POLICY)
    policy.update(config.get("response_policy") or {})
    approval_actions = set(config.get("require_human_approval_for") or [])

    risk_level = str(risk.get("risk_level") or "LOW").lower()
    actions = list(policy.get(risk_level) or ["log_only"])
    primary_action = actions[0]
    human_review_required = any(action in approval_actions for action in actions)
    external_execution_allowed = mode != "dry_run" and not human_review_required

    instruction = {
        "action": primary_action,
        "actions": actions,
        "user_id": triage_state.get("user_id"),
        "session_id": triage_state.get("session_id"),
        "message": _message_for(primary_action, risk_level),
        "requires_mfa": risk_level in {"high", "critical"},
        "reason": f"{str(risk.get('risk_level') or 'LOW').title()}-risk activity pattern detected",
        "dry_run": mode == "dry_run",
        "execute_external_action": external_execution_allowed,
    }

    return {
        "decision": primary_action,
        "actions": actions,
        "mode": mode,
        "human_review_required": human_review_required,
        "response_instruction": instruction,
        "response_taken": _response_taken(primary_action, mode),
    }


def _message_for(action: str, risk_level: str) -> str:
    if action == "log_only":
        return "Activity was logged for audit review."
    if action == "notify_admin":
        return "Unusual activity was detected and marked for security review."
    if action == "step_up_authentication_required":
        return "We noticed unusual activity. Please log in again to continue."
    if action == "require_mfa_challenge":
        return "We noticed unusual activity. Please complete MFA and log in again to continue."
    if action == "create_incident_ticket":
        return "A security incident ticket should be created for review."
    if risk_level == "critical":
        return "Critical activity was detected. Security review is required before continuing."
    return "Security review instruction generated."


def _response_taken(action: str, mode: str) -> str:
    if mode == "dry_run":
        return "dry_run_recommendation_only"
    if action == "step_up_authentication_required":
        return "user_asked_to_login_again"
    if action == "require_mfa_challenge":
        return "mfa_challenge_required"
    return action

