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


ROLE = "context_expander"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=14)
        digest = require_artifact(items, "research_digest")
        compression_policy = require_artifact(items, "compression_policy")
        projected_context = context_summary(items)
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=14,
            token_budget=1000,
            target_tokens=650,
            objective="Expand the research digest into a longer multi-agent handoff while preserving pinned terms.",
            current_subtask="Generate intentionally longer context that remains structured and compressible.",
            use_model_compression=True,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Context Expander, an LLM agent whose job is to make the working "
            "context longer in a controlled way. Return strict JSON with keys expanded_handoff, "
            "sections, repeated_noise_examples, pinned_terms, source_refs, and confidence."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Items:\n{projected_context}\n\n"
            "Task: Expand the digest into a deliberately longer handoff. Include useful "
            "structure, but also include repeated_noise_examples so later compression can prune it."
        )
        mock_resp = {
            "expanded_handoff": "The project is a context compression relay. Each agent must call CompileContext, use the compressed packet, and add one larger artifact for the next agent.",
            "sections": [
                {"name": "Objective", "text": "Show precise shorter context under growing memory pressure."},
                {"name": "Pinned Facts", "text": "Keep CTX-COMP-ADV-001, SRC-A, SRC-B, SRC-C, and 2026-05-03T17:00:00-04:00."},
                {"name": "Compression Behavior", "text": "Record token estimates, level, warnings, and whether compression happened."},
                {"name": "Agent Contract", "text": "Use generated long context only after checking the compiled packet."},
            ],
            "repeated_noise_examples": [
                "Repeated status: the context is growing but the core facts are unchanged.",
                "Repeated status: the context is growing but the core facts are unchanged.",
                "Repeated status: the context is growing but the core facts are unchanged.",
                "Repeated note: exact identifiers matter more than prose volume.",
                "Repeated note: exact identifiers matter more than prose volume.",
            ],
            "pinned_terms": ["CTX-COMP-ADV-001", "CTX_COMPRESS_001", "SRC-A", "SRC-B", "SRC-C", "2026-05-03T17:00:00-04:00"],
            "source_refs": [digest["id"], compression_policy["id"]],
            "confidence": 0.87,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        expanded_id = "expanded_context_1"
        content = make_content(
            goal_id=focus_id,
            artifact_type="expanded_context",
            payload=llm_response,
            allow_roles=["constraint_challenger", "context_compressor", "briefing_author"],
            source_refs=[digest["id"], compression_policy["id"]],
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "intentionally_added_repetition": True,
            },
            do_not_lose=llm_response.get("pinned_terms", []),
        )
        add_item(stub, job_id, expanded_id, "Evidence", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.86)))
        link_items(stub, job_id, digest["id"], expanded_id, "expands")
        link_items(stub, job_id, compression_policy["id"], expanded_id, "uses_policy")
        link_items(stub, job_id, focus_id, expanded_id, "has_expanded_context")
        transition_item(stub, job_id, expanded_id, status="validated")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "expanded_context",
            [digest["id"], compression_policy["id"]],
            [expanded_id],
            "Consumed compiled context and created a longer structured handoff.",
        )

        artifact_ids.update({"expanded_context": expanded_id, "expander_trace": trace_id})
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_expander=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
