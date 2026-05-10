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


ROLE = "risk_classifier"


def ids_for(items, artifact_type, limit=12):
    return [item["id"] for item in items if item["artifact_type"] == artifact_type][:limit]


def first_artifact(items, artifact_type):
    return next((item for item in items if item["artifact_type"] == artifact_type), None)


def main():
    try:
        agent_started_at = monotonic_seconds()
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=120)
        dependency_map = require_artifact(items, "dependency_map")
        digest = require_artifact(items, "architecture_digest")
        analysis_policy = require_artifact(items, "analysis_policy")
        private_note = first_artifact(items, "private_security_note")
        file_refs = ids_for(items, "repo_code_file", limit=14)
        projected_preview = context_summary(items[:10])
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=120,
            token_budget=1350,
            target_tokens=760,
            objective="Classify code-analysis risks while checking private-memory isolation.",
            current_subtask="Identify risky subsystems, test focus, and whether role-scoped memory was visible only here.",
            use_model_compression=None,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Risk Classifier. Return strict JSON with keys risk_register, test_focus, "
            "private_memory_check, compression_risks, must_keep, source_refs, and confidence."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Preview:\n{projected_preview}\n\n"
            "Task: Classify review risks for the codebase analysis benchmark."
        )
        saw_private = private_note is not None
        mock_resp = {
            "risk_register": [
                {"area": "ORM/query execution", "risk": "Broad blast radius; small changes can affect SQL generation, transactions, and model behavior.", "review_depth": "deep"},
                {"area": "Request and middleware lifecycle", "risk": "Ordering and state propagation changes can break security or response semantics.", "review_depth": "deep"},
                {"area": "Auth, sessions, and CSRF", "risk": "Security-sensitive boundaries require explicit private-memory and test isolation.", "review_depth": "deep"},
                {"area": "Migrations", "risk": "State graph and schema editor behavior can regress compatibility.", "review_depth": "moderate"},
                {"area": "Admin/forms", "risk": "User-facing behavior spans permissions, validation, and model metadata.", "review_depth": "moderate"},
            ],
            "test_focus": [
                "Preserve source_refs when reducing hundreds of repo facts to subsystem claims.",
                "Check that private_security_note is visible to risk_classifier but absent from earlier roles.",
                "Force tight CompileContext budgets after large fixture seeding.",
                "Prefer invariant assertions over exact LLM wording.",
            ],
            "private_memory_check": {
                "risk_classifier_saw_private_security_note": saw_private,
                "private_note_ref": "redacted" if private_note else None,
                "expected_non_risk_role_visibility": "not visible",
            },
            "compression_risks": [
                "Important hot paths may be crowded out by many lower-value file notes.",
                "Final answer could lose commit SHA or GitHub source URLs if source_refs are not pinned.",
                "Repeated generated notes can consume packet budget without adding new evidence.",
            ],
            "must_keep": [
                "CODE-MEM-BENCH-001",
                "CODE_CONTEXT_MEMORY_001",
                "REPO: django/django",
                "PINNED-INVARIANT: preserve source_refs for every code fact that reaches the final briefing",
                "PRIVATE-MEMORY-BOUNDARY",
            ],
            "source_refs": [dependency_map["id"], digest["id"], analysis_policy["id"]] + file_refs,
            "confidence": 0.89,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        risk_id = "code_risk_register_1"
        source_refs = [dependency_map["id"], digest["id"], analysis_policy["id"]] + file_refs
        content = make_content(
            goal_id=focus_id,
            artifact_type="code_risk_register",
            payload=llm_response,
            allow_roles=["context_compressor", "briefing_author"],
            source_refs=source_refs,
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "private_memory_visible_to_risk_role": saw_private,
            },
            do_not_lose=llm_response.get("must_keep", []),
        )
        add_item(stub, job_id, risk_id, "Hypothesis", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.88)))
        link_items(stub, job_id, dependency_map["id"], risk_id, "classifies_risk_from")
        link_items(stub, job_id, digest["id"], risk_id, "checks_architecture_digest")
        if private_note:
            link_items(stub, job_id, private_note["id"], risk_id, "uses_private_boundary_note")
        link_items(stub, job_id, analysis_policy["id"], risk_id, "uses_policy")
        link_items(stub, job_id, focus_id, risk_id, "has_code_risk_register")
        transition_item(stub, job_id, risk_id, status="tested")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "code_risk_register",
            source_refs,
            [risk_id],
            "Classified review risks and recorded the private-memory isolation check.",
        )

        artifact_ids.update({"code_risk_register": risk_id, "risk_trace": trace_id})
        event = benchmark_event(
            source,
            ROLE,
            "code_risk_register",
            items,
            compiled,
            llm_response,
            expected_terms=llm_response.get("must_keep", []),
            expected_source_refs=source_refs,
            extra={
                "source_artifact_id": risk_id,
                "risk_count": len(llm_response.get("risk_register", [])),
                "private_memory_visible": saw_private,
                "private_memory_expected_visible": True,
                "private_memory_isolation_pass": saw_private,
            },
            started_at=agent_started_at,
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_risk_classifier=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
            private_memory_visible=saw_private,
            benchmark_events=append_benchmark_event(source, event),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
