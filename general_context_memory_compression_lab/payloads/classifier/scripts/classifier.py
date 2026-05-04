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


ROLE = "constraint_challenger"


def main():
    try:
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=18)
        expanded = require_artifact(items, "expanded_context")
        digest = require_artifact(items, "research_digest")
        compression_policy = require_artifact(items, "compression_policy")
        projected_context = context_summary(items)
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=18,
            token_budget=900,
            target_tokens=600,
            objective="Challenge the growing context and identify what must survive compression.",
            current_subtask="Produce a tested hypothesis about what a shorter context packet must retain.",
            use_model_compression=True,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Constraint Challenger, an LLM reviewer. Return strict JSON with "
            "keys hypothesis, must_keep, safe_to_compress, risks, challenge_notes, "
            "source_refs, and confidence. Be skeptical about verbose handoffs."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Items:\n{projected_context}\n\n"
            "Task: Identify the smallest set of facts that must survive compression, "
            "and name the repeated or low-value context that can be shortened."
        )
        mock_resp = {
            "hypothesis": "A compact packet can support the next agent if it preserves exact IDs, deadline, policy id, source refs, and compression trace metrics.",
            "must_keep": [
                "CTX-COMP-ADV-001",
                "CTX_COMPRESS_001",
                "SRC-A",
                "SRC-B",
                "SRC-C",
                "2026-05-03T17:00:00-04:00",
                "CompileContext was called before each LLM turn",
            ],
            "safe_to_compress": [
                "Repeated status lines",
                "Duplicate descriptions of why context grows",
                "Long background paragraphs once source_refs are preserved",
            ],
            "risks": [
                "Dropping exact deadline would make the final briefing untrustworthy.",
                "Dropping source_refs would sever traceability.",
            ],
            "challenge_notes": [
                "Generated context is now larger than the original task.",
                "The next agent should prefer compression trace over raw repeated prose.",
                "A final answer should be short, not a replay of all sections.",
            ],
            "source_refs": [expanded["id"], digest["id"], compression_policy["id"]],
            "confidence": 0.89,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        challenge_id = "compression_challenge_1"
        content = make_content(
            goal_id=focus_id,
            artifact_type="compression_challenge",
            payload=llm_response,
            allow_roles=["context_compressor", "briefing_author"],
            source_refs=[expanded["id"], digest["id"], compression_policy["id"]],
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "tested_compressibility": True,
            },
            do_not_lose=llm_response.get("must_keep", []),
        )
        add_item(stub, job_id, challenge_id, "Hypothesis", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.88)))
        link_items(stub, job_id, expanded["id"], challenge_id, "challenges")
        link_items(stub, job_id, digest["id"], challenge_id, "checks")
        link_items(stub, job_id, compression_policy["id"], challenge_id, "tests_policy")
        link_items(stub, job_id, focus_id, challenge_id, "has_compression_hypothesis")
        transition_item(stub, job_id, challenge_id, status="tested")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "compression_challenge",
            [expanded["id"], digest["id"], compression_policy["id"]],
            [challenge_id],
            "Consumed compressed context and identified must-keep terms versus compressible repetition.",
        )

        artifact_ids.update({"compression_challenge": challenge_id, "challenge_trace": trace_id})
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_challenger=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
