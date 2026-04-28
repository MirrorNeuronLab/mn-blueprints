#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _synaptic_runtime.core import (
    add_marketing_activity,
    load_input_plan,
    load_knowledge_section,
    log_agent,
    mark_draft_sent,
    read_delivery_settings,
)
from _synaptic_skills.email_delivery import dry_run_email, post_email, post_slack_message


AGENT_ID = "marketing_automation_agent"


def quick_testing_enabled(delivery_settings: dict) -> bool:
    values = [
        os.environ.get("SYNAPTIC_QUICK_TEST_MODE", ""),
        os.environ.get("SYNAPTIC_EMAIL_DRY_RUN", ""),
        str(delivery_settings.get("quick_testing", "")),
        str(delivery_settings.get("dry_run", "")),
    ]
    mode = (
        os.environ.get("SYNAPTIC_EMAIL_DELIVERY_MODE", "")
        or str(delivery_settings.get("mode", ""))
    ).strip().lower()
    if mode in {"agentmail", "live"}:
        return False
    return mode in {"dry_run", "dry-run", "test", "quick_test"} or any(
        value.strip().lower() in {"1", "true", "yes", "on"} for value in values
    )


def log_email_sent_event(runtime_job_id: str | None, to_email: str, subject: str) -> None:
    log_agent(
        runtime_job_id,
        AGENT_ID,
        "Email sent event.",
        details={"to": to_email, "subject": subject},
    )


def main(email_sender=None, slack_sender=None) -> None:
    plan = load_input_plan()
    runtime_job_id = plan.get("runtime_job_id")
    customer = plan["customer"]
    control_decision = plan.get("control_decision", {})
    saved_draft = plan.get("saved_draft")
    policy_decision = plan.get("policy_decision", {})
    delivery_settings = read_delivery_settings()
    brand = load_knowledge_section("brand")
    test_recipient = (
        os.environ.get("SYNAPTIC_TEST_EMAIL_TO", "").strip()
        or str(delivery_settings.get("test_recipient", "")).strip()
    )
    actual_recipient = test_recipient or customer["email"]
    quick_testing = quick_testing_enabled(delivery_settings)
    send_email = email_sender or (dry_run_email if quick_testing else post_email)
    send_slack = slack_sender or post_slack_message
    reply_context = dict(plan.get("reply_context") or {})
    email_headers = {"Idempotency-Key": saved_draft["draft_id"]}
    thread_message_id = str(reply_context.get("thread_message_id") or "").strip()
    in_reply_to_message_id = str(
        reply_context.get("in_reply_to_message_id") or thread_message_id
    ).strip()
    references_message_ids = [
        str(item).strip()
        for item in list(reply_context.get("references_message_ids") or [])
        if str(item).strip()
    ]
    if in_reply_to_message_id:
        email_headers["In-Reply-To"] = in_reply_to_message_id
    if references_message_ids:
        email_headers["References"] = " ".join(references_message_ids)
    if thread_message_id and thread_message_id not in references_message_ids:
        email_headers["References"] = " ".join([*references_message_ids, thread_message_id]).strip()
        
    if policy_decision.get("decision") == "block":
        delivery = {"status": "blocked", "reason": "deliverability_policy_block"}
        slack_delivery = {"status": "not_sent", "reason": "email_not_successful"}
    elif control_decision.get("decision") != "send_now":
        delivery = {
            "status": "waiting",
            "reason": "minimum_interval_not_reached",
            "scheduled_send_at": control_decision.get("scheduled_send_at"),
        }
        slack_delivery = {"status": "not_sent", "reason": "email_not_successful"}
    else:
        execution_request = {
            "to": [actual_recipient],
            "subject": saved_draft["subject"],
            "text": saved_draft["body_text"],
            "html": saved_draft["html_body"],
            "headers": email_headers,
        }
        delivery = send_email(execution_request)
        if delivery["status"] == "sent":
            mark_draft_sent(saved_draft["draft_id"], delivery.get("provider_id"))
            add_marketing_activity(
                customer["customer_id"],
                f"Sent email: {saved_draft['subject']}",
            )
            log_email_sent_event(runtime_job_id, actual_recipient, saved_draft["subject"])
            if quick_testing:
                slack_delivery = {"status": "skipped", "reason": "quick_test_mode"}
            else:
                slack_delivery = send_slack(
                    f"Synaptic sent a customized email to {customer['name']} <{customer['email']}>."
                )
            log_agent(
                runtime_job_id,
                AGENT_ID,
                "Sent email to customer.",
                details={
                    "customer_id": customer["customer_id"],
                    "provider_id": delivery.get("provider_id"),
                    "customer_email": customer["email"],
                    "delivery_recipient": actual_recipient,
                    "test_recipient_override": bool(test_recipient),
                    "subject": saved_draft["subject"],
                },
            )
        else:
            slack_delivery = {"status": "not_sent", "reason": "email_not_successful"}
            log_agent(
                runtime_job_id,
                AGENT_ID,
                "Email delivery failed.",
                details={
                    "customer_id": customer["customer_id"],
                    "customer_email": customer["email"],
                    "delivery_recipient": actual_recipient,
                    "test_recipient_override": bool(test_recipient),
                    "error": delivery.get("error"),
                    "subject": saved_draft["subject"],
                },
            )

    print(
        json.dumps(
            {
                "events": [
                    {
                        "type": "email_delivery_attempted",
                        "payload": {
                            "customer_id": customer["customer_id"],
                            "email": actual_recipient,
                            "customer_email": customer["email"],
                            "subject": saved_draft["subject"],
                            "cycle": int(plan.get("cycle", 1)),
                            "status": delivery["status"],
                            "http_status": delivery.get("http_status"),
                            "provider_id": delivery.get("provider_id"),
                            "reason": delivery.get("reason"),
                            "error": delivery.get("error"),
                            "dry_run": bool(delivery.get("dry_run")),
                            "quick_testing": quick_testing,
                            "test_recipient_override": bool(test_recipient),
                        },
                    },
                    *(
                        [
                            {
                                "type": "slack_confirmation_attempted",
                                "payload": {
                                    "customer_id": customer["customer_id"],
                                    "email": actual_recipient,
                                    "customer_email": customer["email"],
                                    "cycle": int(plan.get("cycle", 1)),
                                    "status": slack_delivery["status"],
                                    "channel": slack_delivery.get("channel", "#claw"),
                                },
                            }
                        ]
                        if delivery["status"] == "sent"
                        else []
                    ),
                ],
                "emit_messages": [
                    *(
                        [
                            {
                                "to": "monitor_scheduler_agent",
                                "type": "cycle_trigger",
                                "body": {
                                    "status": delivery["status"],
                                    "cycle": int(plan.get("cycle", 1)) + 1,
                                    "original_plan": plan,
                                },
                                "class": "event",
                                "headers": {
                                    "schema_ref": "com.synaptic.monitor.cycle_trigger",
                                    "schema_version": "1.0.0",
                                },
                            }
                        ]
                        if os.environ.get("SYNAPTIC_EMIT_CYCLE_TRIGGER", "true").lower() != "false"
                        else []
                    )
                ],
                "next_state": {
                    "last_cycle": int(plan.get("cycle", 1)),
                    "last_status": delivery["status"],
                },
            }
        )
    )


if __name__ == "__main__":
    main()
