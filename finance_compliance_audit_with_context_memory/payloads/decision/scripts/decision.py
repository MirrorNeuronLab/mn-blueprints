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


ROLE = "decision_agent"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=20)
        risk_assessment = require_artifact(items, "risk_assessment")
        structured_policy = require_artifact(items, "structured_policy")
        structured_evidence = require_artifact(items, "structured_evidence")
        context_str = context_summary(items)

        sys_prompt = (
            "You are a Decision Agent. Use the tested risk hypothesis, structured "
            "policy, and structured evidence to produce a final audit decision. "
            "Return JSON with final_status, severity, decision_summary, confirmed_risk, "
            "evidence_refs, and confidence."
        )
        user_prompt = f"Context:\n{context_str}\n\nTask: Output final decision."
        mock_resp = {
            "final_status": "failed",
            "severity": "medium",
            "decision_summary": "Fee disclosure timing is not clearly compliant.",
            "confirmed_risk": True,
            "evidence_refs": ["structured_evidence_1", "risk_assessment_1"],
            "confidence": 0.84,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        final_decision_id = "final_decision_1"
        source_refs = [
            risk_assessment["id"],
            structured_policy["id"],
            structured_evidence["id"],
        ]
        content = make_content(
            goal_id=focus_id,
            artifact_type="final_decision",
            payload=llm_response,
            allow_roles=["critic_auditor"],
            source_refs=source_refs,
            validation={
                "risk_assessment_status": risk_assessment["status"],
                "decision_basis_refs": source_refs,
            },
        )
        add_item(
            stub,
            job_id,
            final_decision_id,
            "Decision",
            "draft",
            ROLE,
            content,
            confidence=float(llm_response.get("confidence", 0.82)),
        )
        for source_id in source_refs:
            link_items(stub, job_id, source_id, final_decision_id, "informs_decision")
        link_items(stub, job_id, focus_id, final_decision_id, "has_final_decision")
        transition_item(stub, job_id, final_decision_id, status="validated")

        risk_status = "confirmed" if llm_response.get("confirmed_risk") else "rejected"
        transition_item(stub, job_id, risk_assessment["id"], status=risk_status)

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "final_decision",
            source_refs,
            [final_decision_id],
            f"Produced final decision and marked risk hypothesis {risk_status}.",
        )

        artifact_ids.update(
            {
                "final_decision": final_decision_id,
                "decision_trace": trace_id,
            }
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_decision=[item["artifact_type"] or item["type"] for item in items],
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
