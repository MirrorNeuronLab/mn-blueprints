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


ROLE = "risk_classifier"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=16)
        structured_policy = require_artifact(items, "structured_policy")
        structured_evidence = require_artifact(items, "structured_evidence")
        context_str = context_summary(items)

        sys_prompt = (
            "You are a Risk Classifier. Test whether the structured evidence satisfies "
            "the structured policy. Return JSON with status, risk_level, reasoning, "
            "matched_evidence_refs, missing_evidence, and confidence."
        )
        user_prompt = f"Context:\n{context_str}\n\nTask: Classify compliance risk."
        mock_resp = {
            "policy_id": "FEE_DISCLOSURE_001",
            "status": "potential_violation",
            "risk_level": "medium",
            "reasoning": "The fee amount and agreement request occur together after an earlier waiver offer, so timing is ambiguous.",
            "matched_evidence_refs": ["structured_evidence_1"],
            "missing_evidence": ["explicit customer agreement after disclosure"],
            "confidence": 0.86,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        risk_assessment_id = "risk_assessment_1"
        content = make_content(
            goal_id=focus_id,
            artifact_type="risk_assessment",
            payload=llm_response,
            allow_roles=["decision_agent", "critic_auditor"],
            source_refs=[structured_policy["id"], structured_evidence["id"]],
            validation={
                "policy_ref": structured_policy["id"],
                "evidence_ref": structured_evidence["id"],
                "tested_against_policy": True,
            },
        )
        add_item(
            stub,
            job_id,
            risk_assessment_id,
            "Hypothesis",
            "draft",
            ROLE,
            content,
            confidence=float(llm_response.get("confidence", 0.85)),
        )
        link_items(stub, job_id, structured_policy["id"], risk_assessment_id, "constrains")
        link_items(stub, job_id, structured_evidence["id"], risk_assessment_id, "supports")
        link_items(stub, job_id, focus_id, risk_assessment_id, "has_risk_hypothesis")
        transition_item(stub, job_id, risk_assessment_id, status="tested")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "risk_assessment",
            [structured_policy["id"], structured_evidence["id"]],
            [risk_assessment_id],
            "Tested structured evidence against structured policy.",
        )

        artifact_ids.update(
            {
                "risk_assessment": risk_assessment_id,
                "risk_trace": trace_id,
            }
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_classifier=[item["artifact_type"] or item["type"] for item in items],
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
