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


ROLE = "dependency_mapper"


def ids_for(items, artifact_type, limit=12):
    return [item["id"] for item in items if item["artifact_type"] == artifact_type][:limit]


def main():
    try:
        agent_started_at = monotonic_seconds()
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=105)
        digest = require_artifact(items, "architecture_digest")
        repo_fixture = require_artifact(items, "repo_fixture")
        analysis_policy = require_artifact(items, "analysis_policy")
        file_refs = ids_for(items, "repo_code_file", limit=18)
        projected_preview = context_summary(items[:10])
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=105,
            token_budget=1550,
            target_tokens=820,
            objective="Map high-level dependencies between large repository subsystems from compressed memory.",
            current_subtask="Produce a dependency map that keeps evidence refs but does not need every file note.",
            use_model_compression=None,
        )
        compiled_context = compiled_context_summary(compiled)

        sys_prompt = (
            "You are Dependency Mapper. Return strict JSON with keys dependency_map, critical_paths, "
            "source_ref_coverage, compression_notes, pinned_terms, source_refs, and confidence."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Preview:\n{projected_preview}\n\n"
            "Task: Turn the architecture digest into a dependency map for code-review planning."
        )
        mock_resp = {
            "dependency_map": [
                {"from": "ASGI/WSGI and handlers", "to": "middleware, URL resolver, view response", "evidence": ["django/core/handlers", "django/urls", "django/http"]},
                {"from": "Models and querysets", "to": "SQL compiler, expressions, transactions", "evidence": ["django/db/models", "django/db/backends"]},
                {"from": "Migrations", "to": "project state, schema editor, app registry", "evidence": ["django/db/migrations", "django/apps"]},
                {"from": "Auth and sessions", "to": "middleware, backends, request user state", "evidence": ["django/contrib/auth", "django/contrib/sessions"]},
                {"from": "Admin", "to": "forms, model metadata, permissions, URL routing", "evidence": ["django/contrib/admin", "django/forms"]},
            ],
            "critical_paths": [
                "Request path: server entrypoint -> handler -> middleware -> URL resolver -> view -> response.",
                "ORM path: model metadata -> QuerySet -> SQL compiler -> database backend.",
                "Migration path: migration graph -> project state -> schema editor -> database operations.",
                "Security path: middleware/session/auth backend -> request user and CSRF decisions.",
            ],
            "source_ref_coverage": {
                "repo_fixture": repo_fixture["id"],
                "architecture_digest": digest["id"],
                "sampled_file_refs": file_refs,
            },
            "compression_notes": [
                "File-level notes are useful for sampling but should collapse into subsystem edges.",
                "Keep exact file paths and source item IDs when an edge becomes a final claim.",
                "Repeated generated pressure notes are safe to summarize.",
            ],
            "pinned_terms": [
                "CODE-MEM-BENCH-001",
                "CODE_CONTEXT_MEMORY_001",
                "PINNED-INVARIANT: preserve source_refs for every code fact that reaches the final briefing",
            ],
            "source_refs": [digest["id"], repo_fixture["id"], analysis_policy["id"]] + file_refs,
            "confidence": 0.88,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        map_id = "dependency_map_1"
        source_refs = [digest["id"], repo_fixture["id"], analysis_policy["id"]] + file_refs
        content = make_content(
            goal_id=focus_id,
            artifact_type="dependency_map",
            payload=llm_response,
            allow_roles=["risk_classifier", "context_compressor", "briefing_author"],
            source_refs=source_refs,
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "source_ref_coverage": True,
            },
            do_not_lose=llm_response.get("pinned_terms", []),
        )
        add_item(stub, job_id, map_id, "Evidence", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.86)))
        link_items(stub, job_id, digest["id"], map_id, "maps_dependencies_from")
        link_items(stub, job_id, repo_fixture["id"], map_id, "samples_fixture")
        link_items(stub, job_id, analysis_policy["id"], map_id, "uses_policy")
        link_items(stub, job_id, focus_id, map_id, "has_dependency_map")
        transition_item(stub, job_id, map_id, status="validated")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "dependency_map",
            source_refs,
            [map_id],
            "Mapped subsystem dependencies from compressed memory and retained source refs.",
        )

        artifact_ids.update({"dependency_map": map_id, "dependency_trace": trace_id})
        event = benchmark_event(
            source,
            ROLE,
            "dependency_map",
            items,
            compiled,
            llm_response,
            expected_terms=llm_response.get("pinned_terms", []),
            expected_source_refs=source_refs,
            extra={
                "source_artifact_id": map_id,
                "dependency_edge_count": len(llm_response.get("dependency_map", [])),
                "critical_path_count": len(llm_response.get("critical_paths", [])),
            },
            started_at=agent_started_at,
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_dependency_mapper=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
            benchmark_events=append_benchmark_event(source, event),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
