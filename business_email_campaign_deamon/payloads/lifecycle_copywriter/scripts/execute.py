#!/usr/bin/env python3
import json
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _synaptic_runtime.core import (
    completion_json,
    load_knowledge_section,
    load_input_plan,
    log_agent,
    read_business_context,
)
from _synaptic_skills.marketing_email import normalize_structured_draft


AGENT_ID = "lifecycle_copywriter_agent"


def fallback_draft(plan: dict) -> dict:
    return normalize_structured_draft(
        {},
        plan=plan,
        brand=load_knowledge_section("brand"),
    )


def main() -> None:
    plan = load_input_plan()
    runtime_job_id = plan.get("runtime_job_id")

    if plan.get("existing_draft"):
        log_agent(runtime_job_id, AGENT_ID, "Skipped copywriting because a ready draft already exists.")
        print(json.dumps(plan))
        return

    system_prompt = (
        "You are a lifecycle email copywriter. Return JSON only. "
        "Required keys: subject_candidates, preview_text, eyebrow, headline, body_sections, cta_label, cta_url_slug, footer_variant, secondary_text, signoff. "
        "Write one strong email for one audience, one offer, and one primary CTA. "
        "Use short paragraphs, clear benefits, and specific proof. Avoid sounding generic or overly salesy. "
        "If campaign_type is reply_followup, write like a real human replying personally: short, warm, specific, conversational, and not like a newsletter. "
        "body_sections must be an array of plain paragraph strings, not objects."
    )
    user_prompt = json.dumps(
        {
            "business_context": read_business_context(),
            "strategy": {
                "campaign_type": plan.get("campaign_type"),
                "audience_segment": plan.get("audience_segment"),
                "primary_offer": plan.get("primary_offer"),
                "why_now": plan.get("why_now"),
                "goal": plan.get("goal"),
            },
            "customer": plan["customer"],
            "customer_brief": plan.get("customer_brief", {}),
            "recent_activities": plan.get("recent_activities", []),
            "reply_context": plan.get("reply_context", {}),
            "brand": load_knowledge_section("brand"),
        },
        indent=2,
    )
    plan["draft"] = normalize_structured_draft(
        completion_json(system_prompt, user_prompt, profile="primary"),
        plan=plan,
        brand=load_knowledge_section("brand"),
    )
    if not plan["draft"]:
        plan["draft"] = fallback_draft(plan)
    log_agent(runtime_job_id, AGENT_ID, "Prepared lifecycle copy.")
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
