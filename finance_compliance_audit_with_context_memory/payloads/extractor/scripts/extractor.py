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


ROLE = "evidence_extractor"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id)
        transcript = require_artifact(items, "raw_transcript")
        context_str = context_summary(items)

        sys_prompt = (
            "You are an Evidence Extractor. Extract exact quotes and speakers from "
            "transcripts. Do not infer compliance and do not judge. Return JSON with "
            "evidence_items, each having speaker, quote, sequence_index, and evidence_kind."
        )
        user_prompt = f"Context:\n{context_str}\n\nTask: Extract evidence items from the transcript."
        mock_resp = {
            "evidence_items": [
                {
                    "speaker": "agent",
                    "quote": "I can waive that fee for you today.",
                    "sequence_index": 1,
                    "evidence_kind": "fee_waiver_offer",
                },
                {
                    "speaker": "agent",
                    "quote": "The fee is $50. Do you agree?",
                    "sequence_index": 3,
                    "evidence_kind": "fee_disclosure_and_agreement_request",
                },
            ],
            "confidence": 0.92,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        structured_evidence_id = "structured_evidence_1"
        content = make_content(
            goal_id=focus_id,
            artifact_type="structured_evidence",
            payload=llm_response,
            allow_roles=["risk_classifier", "decision_agent", "critic_auditor"],
            source_refs=[transcript["id"]],
            validation={
                "verbatim_quotes": True,
                "no_policy_judgment": True,
                "extracted_from": transcript["id"],
            },
        )
        add_item(
            stub,
            job_id,
            structured_evidence_id,
            "Evidence",
            "draft",
            ROLE,
            content,
            confidence=float(llm_response.get("confidence", 0.9)),
        )
        link_items(stub, job_id, transcript["id"], structured_evidence_id, "extracts")
        link_items(stub, job_id, focus_id, structured_evidence_id, "has_structured_evidence")
        transition_item(stub, job_id, structured_evidence_id, status="validated")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "structured_evidence",
            [transcript["id"]],
            [structured_evidence_id],
            "Extracted quote-level evidence without policy interpretation.",
        )

        artifact_ids.update(
            {
                "structured_evidence": structured_evidence_id,
                "evidence_trace": trace_id,
            }
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_extractor=[item["artifact_type"] or item["type"] for item in items],
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
