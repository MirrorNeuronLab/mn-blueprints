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
    snapshot_if_configured,
    transition_item,
)


ROLE = "briefing_author"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=26)
        handoff = require_artifact(items, "compressed_handoff")
        challenge = require_artifact(items, "compression_challenge")
        compression_policy = require_artifact(items, "compression_policy")
        projected_context = context_summary(items)
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=26,
            token_budget=750,
            target_tokens=480,
            objective="Write the final demo briefing from compressed context.",
            current_subtask="Explain how Membrane kept the useful context short and precise across LLM agents.",
            use_model_compression=True,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Briefing Author, the final LLM agent. Return strict JSON with "
            "keys final_briefing, preserved_terms, compression_summary, traceability, "
            "source_refs, and confidence. Keep final_briefing short and precise."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Items:\n{projected_context}\n\n"
            "Task: Write the final briefing. Demonstrate that you used the shorter "
            "compiled context, not a full replay of all generated notes."
        )
        mock_resp = {
            "final_briefing": (
                "Membrane handled case CTX-COMP-ADV-001 by storing long generated artifacts "
                "as typed memory, projecting each agent's visible fields, and compiling a "
                "short context packet before every LLM call. The final packet preserved "
                "source ids SRC-A/SRC-B/SRC-C, policy CTX_COMPRESS_001, and deadline "
                "2026-05-03T17:00:00-04:00 while summarizing repeated handoff prose."
            ),
            "preserved_terms": ["CTX-COMP-ADV-001", "CTX_COMPRESS_001", "SRC-A", "SRC-B", "SRC-C", "2026-05-03T17:00:00-04:00"],
            "compression_summary": compile_context_state(compiled),
            "traceability": [
                {"artifact": "compressed_handoff", "source_ref": handoff["id"]},
                {"artifact": "compression_challenge", "source_ref": challenge["id"]},
                {"artifact": "compression_policy", "source_ref": compression_policy["id"]},
            ],
            "source_refs": [handoff["id"], challenge["id"], compression_policy["id"]],
            "confidence": 0.91,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        briefing_id = "final_context_briefing_1"
        source_refs = [handoff["id"], challenge["id"], compression_policy["id"]]
        content = make_content(
            goal_id=focus_id,
            artifact_type="final_context_briefing",
            payload=llm_response,
            allow_roles=["briefing_author"],
            source_refs=source_refs,
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "final_output": True,
            },
            do_not_lose=llm_response.get("preserved_terms", []),
        )
        add_item(stub, job_id, briefing_id, "Decision", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.9)))
        for source_id in source_refs:
            link_items(stub, job_id, source_id, briefing_id, "supports_final_briefing")
        link_items(stub, job_id, focus_id, briefing_id, "has_final_briefing")
        transition_item(stub, job_id, briefing_id, status="validated")
        transition_item(stub, job_id, handoff["id"], status="used")
        transition_item(stub, job_id, focus_id, status="used")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "final_context_briefing",
            source_refs,
            [briefing_id],
            "Wrote final short briefing from compiled and compressed context.",
        )
        snapshot_redis_url = snapshot_if_configured(stub, job_id, source)

        artifact_ids.update({"final_context_briefing": briefing_id, "briefing_trace": trace_id})
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_briefing_author=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
            final_briefing=llm_response,
            snapshot_redis_url=snapshot_redis_url,
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
