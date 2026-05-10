import json
import sys

from context_memory import (
    add_item,
    add_trace_event,
    append_benchmark_event,
    benchmark_event,
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
    monotonic_seconds,
    require_artifact,
    transition_item,
)


ROLE = "context_compressor"


def first_artifact(items, artifact_type):
    return next((item for item in items if item["artifact_type"] == artifact_type), None)


def main():
    try:
        agent_started_at = monotonic_seconds()
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=130)
        risk_register = require_artifact(items, "code_risk_register")
        dependency_map = require_artifact(items, "dependency_map")
        digest = require_artifact(items, "architecture_digest")
        repo_fixture = require_artifact(items, "repo_fixture")
        analysis_policy = require_artifact(items, "analysis_policy")
        private_note = first_artifact(items, "private_security_note")
        projected_preview = context_summary(items[:10])
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=130,
            token_budget=1150,
            target_tokens=640,
            objective="Compress large-repo working memory into a short handoff for final briefing.",
            current_subtask="Preserve repo identity, subsystem claims, evidence refs, risk results, and private-memory isolation evidence.",
            use_model_compression=None,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Context Compressor. Return strict JSON with keys compressed_code_handoff, "
            "subsystem_table, preserved_evidence, omitted_context, private_memory_isolation, "
            "compression_observations, source_refs, and confidence."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Preview:\n{projected_preview}\n\n"
            "Task: Produce a compact handoff for a codebase architecture briefing."
        )
        compression_state = compile_context_state(compiled)
        mock_resp = {
            "compressed_code_handoff": (
                "Django repository analysis should focus on request lifecycle, ORM/query and migrations, "
                "auth/session/CSRF security, admin/forms, templates, tests, and docs. The final briefing "
                "must preserve repo commit, source_refs, and the private-memory boundary check while omitting "
                "repeated generated file notes."
            ),
            "subsystem_table": [
                {"subsystem": "Request lifecycle", "why": "Core path for runtime behavior and middleware order.", "evidence_refs": [dependency_map["id"], digest["id"]]},
                {"subsystem": "ORM and migrations", "why": "Highest blast radius for data behavior.", "evidence_refs": [dependency_map["id"], risk_register["id"]]},
                {"subsystem": "Auth/session security", "why": "Private note and risk classifier highlight strict isolation and review depth.", "evidence_refs": [risk_register["id"]]},
                {"subsystem": "Admin/forms/templates", "why": "User-facing integration layer with permissions and validation.", "evidence_refs": [digest["id"]]},
            ],
            "preserved_evidence": [
                "CODE-MEM-BENCH-001",
                "CODE_CONTEXT_MEMORY_001",
                "REPO: django/django",
                "COMMIT: " + repo_fixture["content"].get("payload", {}).get("repo", {}).get("commit_sha", "unknown"),
                "source_refs are preserved through digest, dependency map, and risk register",
            ],
            "omitted_context": [
                "Hundreds of lower-rank file facts not needed for the final narrative.",
                "Repeated generated context-pressure notes.",
                "Locale and documentation noise unless directly tied to a claim.",
            ],
            "private_memory_isolation": {
                "context_compressor_directly_saw_private_note": private_note is not None,
                "expected": "false; only the risk register summary should be visible here.",
            },
            "compression_observations": compression_state,
            "source_refs": [risk_register["id"], dependency_map["id"], digest["id"], repo_fixture["id"], analysis_policy["id"]],
            "confidence": 0.9,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        handoff_id = "compressed_code_handoff_1"
        source_refs = [risk_register["id"], dependency_map["id"], digest["id"], repo_fixture["id"], analysis_policy["id"]]
        content = make_content(
            goal_id=focus_id,
            artifact_type="compressed_code_handoff",
            payload=llm_response,
            allow_roles=["briefing_author"],
            source_refs=source_refs,
            validation={
                "compiled_context": compression_state,
                "llm_model": "nemotron3:33b",
                "ready_for_final_author": True,
                "context_compressor_direct_private_note_visibility": private_note is not None,
            },
            do_not_lose=[
                "CODE-MEM-BENCH-001",
                "CODE_CONTEXT_MEMORY_001",
                "REPO: django/django",
                "PINNED-INVARIANT: preserve source_refs for every code fact that reaches the final briefing",
                "PRIVATE-MEMORY-BOUNDARY",
            ],
        )
        add_item(stub, job_id, handoff_id, "Decision", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.88)))
        for source_id in source_refs:
            link_items(stub, job_id, source_id, handoff_id, "compresses_into")
        link_items(stub, job_id, focus_id, handoff_id, "has_compressed_code_handoff")
        transition_item(stub, job_id, handoff_id, status="validated")
        transition_item(stub, job_id, risk_register["id"], status="confirmed")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "compressed_code_handoff",
            source_refs,
            [handoff_id],
            "Produced a compact handoff from a large memory graph and noted private-memory isolation.",
        )

        artifact_ids.update({"compressed_code_handoff": handoff_id, "compressor_trace": trace_id})
        event = benchmark_event(
            source,
            ROLE,
            "compressed_code_handoff",
            items,
            compiled,
            llm_response,
            expected_terms=content.get("do_not_lose", []),
            expected_source_refs=source_refs,
            extra={
                "source_artifact_id": handoff_id,
                "direct_private_note_visible": private_note is not None,
                "private_memory_expected_visible": False,
                "private_memory_isolation_pass": private_note is None,
                "subsystem_table_count": len(llm_response.get("subsystem_table", [])),
            },
            started_at=agent_started_at,
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_context_compressor=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compression_state,
            direct_private_note_visible=private_note is not None,
            benchmark_events=append_benchmark_event(source, event),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
