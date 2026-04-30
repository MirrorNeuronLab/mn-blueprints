import json
import sys

from context_memory import (
    add_item,
    add_trace_event,
    call_llm,
    context_stub,
    context_summary,
    emit_state,
    get_context_logger,
    get_context,
    link_items,
    load_input,
    make_content,
    require_artifact,
    snapshot_if_configured,
    transition_item,
)


ROLE = "critic_auditor"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=30)
        final_decision = require_artifact(items, "final_decision")
        risk_assessment = require_artifact(items, "risk_assessment")
        structured_policy = require_artifact(items, "structured_policy")
        structured_evidence = require_artifact(items, "structured_evidence")
        context_str = context_summary(items)

        sys_prompt = (
            "You are a Critic Auditor. Challenge the final decision using only the "
            "structured evidence, structured policy, risk assessment, decision, and "
            "trace events you can see. Return JSON with audit_result, correction_needed, "
            "auditor_note, challenged_refs, and confidence."
        )
        user_prompt = f"Context:\n{context_str}\n\nTask: Perform final audit on the decision."
        mock_resp = {
            "audit_result": "decision_supported",
            "correction_needed": False,
            "auditor_note": "The failed status is supported by the tested risk hypothesis and extracted evidence.",
            "challenged_refs": [],
            "confidence": 0.88,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        audit_result_id = "audit_result_1"
        source_refs = [
            final_decision["id"],
            risk_assessment["id"],
            structured_policy["id"],
            structured_evidence["id"],
        ]
        content = make_content(
            goal_id=focus_id,
            artifact_type="audit_result",
            payload=llm_response,
            allow_roles=["critic_auditor"],
            source_refs=source_refs,
            validation={
                "audited_decision_ref": final_decision["id"],
                "correction_needed": bool(llm_response.get("correction_needed")),
            },
        )
        add_item(
            stub,
            job_id,
            audit_result_id,
            "Decision",
            "draft",
            ROLE,
            content,
            confidence=float(llm_response.get("confidence", 0.86)),
        )
        for source_id in source_refs:
            link_items(stub, job_id, source_id, audit_result_id, "audits")
        link_items(stub, job_id, focus_id, audit_result_id, "has_audit_result")
        transition_item(stub, job_id, audit_result_id, status="validated")
        transition_item(stub, job_id, final_decision["id"], status="used")
        transition_item(stub, job_id, focus_id, status="used")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "audit_result",
            source_refs,
            [audit_result_id],
            "Audited final decision against visible evidence, policy, risk, and trace.",
        )
        snapshot_redis_url = snapshot_if_configured(stub, job_id, source)

        artifact_ids.update(
            {
                "audit_result": audit_result_id,
                "critic_trace": trace_id,
            }
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_critic=[item["artifact_type"] or item["type"] for item in items],
            llm_audit_output=llm_response,
            snapshot_redis_url=snapshot_redis_url,
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
