import json
import sys

from context_memory import (
    add_item,
    add_trace_event,
    call_llm,
    compile_context,
    compile_context_state,
    compiled_context_summary,
    context_stub,
    context_summary,
    emit_state,
    get_context,
    get_context_logger,
    link_items,
    load_input,
    make_content,
    require_artifact,
    transition_item,
)


ROLE = "context_researcher"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=10)
        source_bundle = require_artifact(items, "source_bundle")
        compression_policy = require_artifact(items, "compression_policy")
        projected_context = context_summary(items)
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=10,
            token_budget=1200,
            target_tokens=700,
            objective="Research the long context source bundle without losing exact pinned terms.",
            current_subtask="Create a research digest that is longer than the seed but structured for later compression.",
            use_model_compression=True,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Context Researcher, the first LLM agent in a context compression demo. "
            "Return strict JSON with keys digest_title, concise_summary, long_generated_notes, "
            "pinned_terms, source_refs, and confidence. Use the compiled context packet as "
            "your primary context, then use projected items only to verify exact source ids."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Items:\n{projected_context}\n\n"
            "Task: Produce a detailed research digest. Make long_generated_notes at least "
            "8 numbered bullets so downstream context has grown."
        )
        mock_resp = {
            "digest_title": "Long Context Relay Research Digest",
            "concise_summary": "The demo should preserve exact IDs and deadlines while compressing repeated context for each agent turn.",
            "long_generated_notes": [
                "1. Source SRC-A establishes that every turn must keep the case identifier visible.",
                "2. Source SRC-B emphasizes exact deadline preservation: 2026-05-03T17:00:00-04:00.",
                "3. Source SRC-C describes long handoffs as repeated prose around a small set of invariants.",
                "4. The context engine should project only role-visible fields before compression.",
                "5. CompileContext should produce objective, constraints, evidence, artifacts, and do_not_lose sections.",
                "6. Later agents should not need to reread the entire source bundle.",
                "7. Generated artifacts intentionally grow so compression has visible work to do.",
                "8. The final briefing should cite compression trace metrics and source refs.",
            ],
            "pinned_terms": ["CTX-COMP-ADV-001", "SRC-A", "SRC-B", "SRC-C", "2026-05-03T17:00:00-04:00"],
            "source_refs": [source_bundle["id"], compression_policy["id"]],
            "confidence": 0.9,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        digest_id = "research_digest_1"
        content = make_content(
            goal_id=focus_id,
            artifact_type="research_digest",
            payload=llm_response,
            allow_roles=["context_expander", "constraint_challenger", "context_compressor", "briefing_author"],
            source_refs=[source_bundle["id"], compression_policy["id"]],
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "grew_context": True,
            },
            do_not_lose=llm_response.get("pinned_terms", []),
        )
        add_item(stub, job_id, digest_id, "Evidence", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.88)))
        link_items(stub, job_id, source_bundle["id"], digest_id, "summarizes")
        link_items(stub, job_id, compression_policy["id"], digest_id, "uses_policy")
        link_items(stub, job_id, focus_id, digest_id, "has_research_digest")
        transition_item(stub, job_id, digest_id, status="validated")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "research_digest",
            [source_bundle["id"], compression_policy["id"]],
            [digest_id],
            "Consumed compiled context and produced the first longer generated digest.",
        )

        artifact_ids.update({"research_digest": digest_id, "research_trace": trace_id})
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_researcher=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
