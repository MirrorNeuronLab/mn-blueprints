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


ROLE = "context_compressor"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=22)
        challenge = require_artifact(items, "compression_challenge")
        expanded = require_artifact(items, "expanded_context")
        digest = require_artifact(items, "research_digest")
        projected_context = context_summary(items)
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=22,
            token_budget=800,
            target_tokens=520,
            objective="Build a short handoff from a long working memory graph.",
            current_subtask="Create a compressed handoff for the final author, citing compression trace and pinned terms.",
            use_model_compression=True,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Context Compressor, an LLM agent that turns growing memory into a "
            "short handoff. Return strict JSON with keys compressed_handoff, evidence_table, "
            "dropped_or_summarized, compression_observations, source_refs, and confidence."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Items:\n{projected_context}\n\n"
            "Task: Produce a short, precise handoff that gives the final author enough "
            "context without replaying the expanded notes."
        )
        mock_resp = {
            "compressed_handoff": (
                "Use case CTX-COMP-ADV-001 to show that Membrane projected and compiled "
                "context can keep source IDs, exact deadline, policy ID, and traceability "
                "while pruning repeated generated prose."
            ),
            "evidence_table": [
                {"fact": "Case id", "value": "CTX-COMP-ADV-001", "source_ref": digest["id"]},
                {"fact": "Deadline", "value": "2026-05-03T17:00:00-04:00", "source_ref": challenge["id"]},
                {"fact": "Policy", "value": "CTX_COMPRESS_001", "source_ref": challenge["id"]},
                {"fact": "Growing context", "value": "research_digest -> expanded_context -> compression_challenge", "source_ref": expanded["id"]},
            ],
            "dropped_or_summarized": [
                "Repeated status lines",
                "Duplicate descriptions of handoff growth",
                "Long fixture background once source refs were retained",
            ],
            "compression_observations": {
                "compiled_level": compile_context_state(compiled).get("level"),
                "compressed": compile_context_state(compiled).get("compressed"),
                "estimated_input_tokens": compile_context_state(compiled).get("estimated_input_tokens"),
                "estimated_output_tokens": compile_context_state(compiled).get("estimated_output_tokens"),
            },
            "source_refs": [challenge["id"], expanded["id"], digest["id"]],
            "confidence": 0.9,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        handoff_id = "compressed_handoff_1"
        source_refs = [challenge["id"], expanded["id"], digest["id"]]
        content = make_content(
            goal_id=focus_id,
            artifact_type="compressed_handoff",
            payload=llm_response,
            allow_roles=["briefing_author"],
            source_refs=source_refs,
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "ready_for_final_author": True,
            },
            do_not_lose=["CTX-COMP-ADV-001", "CTX_COMPRESS_001", "SRC-A", "SRC-B", "SRC-C", "2026-05-03T17:00:00-04:00"],
        )
        add_item(stub, job_id, handoff_id, "Decision", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.88)))
        for source_id in source_refs:
            link_items(stub, job_id, source_id, handoff_id, "compresses_into")
        link_items(stub, job_id, focus_id, handoff_id, "has_compressed_handoff")
        transition_item(stub, job_id, handoff_id, status="validated")
        transition_item(stub, job_id, challenge["id"], status="confirmed")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "compressed_handoff",
            source_refs,
            [handoff_id],
            "Produced a short handoff from a longer generated memory graph.",
        )

        artifact_ids.update({"compressed_handoff": handoff_id, "compressor_trace": trace_id})
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_compressor=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
