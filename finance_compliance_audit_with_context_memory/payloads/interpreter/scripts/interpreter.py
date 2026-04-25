import json
import sys

from context_memory import (
    add_item,
    add_trace_event,
    call_llm,
    context_stub,
    context_summary,
    emit_state,
    get_context,
    link_items,
    load_input,
    make_content,
    require_artifact,
    transition_item,
)


ROLE = "policy_interpreter"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id)
        policy = require_artifact(items, "policy_document")
        context_str = context_summary(items)

        sys_prompt = (
            "You are a Policy Interpreter. Convert policy documents into structured, "
            "testable rules. Do not use transcript facts. Return JSON with policy_id, "
            "rule, required_evidence, prohibited_blind_spots, and confidence."
        )
        user_prompt = f"Context:\n{context_str}\n\nTask: Extract structured policy rules."
        mock_resp = {
            "policy_id": "FEE_DISCLOSURE_001",
            "rule": "Disclose fee before agreement",
            "required_evidence": [
                "fee amount mentioned",
                "customer agreement occurs after fee disclosure",
            ],
            "prohibited_blind_spots": ["do not infer agreement timing without transcript order"],
            "confidence": 0.93,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        structured_policy_id = "structured_policy_1"
        content = make_content(
            goal_id=focus_id,
            artifact_type="structured_policy",
            payload=llm_response,
            allow_roles=["risk_classifier", "decision_agent", "critic_auditor"],
            source_refs=[policy["id"]],
            validation={
                "normalized_from": policy["id"],
                "schema": "policy_id, rule, required_evidence",
            },
        )
        add_item(
            stub,
            job_id,
            structured_policy_id,
            "Constraint",
            "draft",
            ROLE,
            content,
            confidence=float(llm_response.get("confidence", 0.9)),
        )
        link_items(stub, job_id, policy["id"], structured_policy_id, "interprets")
        link_items(stub, job_id, focus_id, structured_policy_id, "has_structured_constraint")
        transition_item(stub, job_id, structured_policy_id, status="validated")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "structured_policy",
            [policy["id"]],
            [structured_policy_id],
            "Converted policy document into a structured constraint.",
        )

        artifact_ids.update(
            {
                "structured_policy": structured_policy_id,
                "policy_trace": trace_id,
            }
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_interpreter=[item["artifact_type"] or item["type"] for item in items],
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
