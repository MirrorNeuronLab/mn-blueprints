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


ROLE = "repo_architect"


def ids_for(items, artifact_type, limit=12):
    return [item["id"] for item in items if item["artifact_type"] == artifact_type][:limit]


def main():
    try:
        agent_started_at = monotonic_seconds()
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=90)
        repo_fixture = require_artifact(items, "repo_fixture")
        analysis_policy = require_artifact(items, "analysis_policy")
        file_refs = ids_for(items, "repo_code_file", limit=16)
        projected_preview = context_summary(items[:10])
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=90,
            token_budget=1800,
            target_tokens=950,
            objective="Create a large-repo architecture digest from memory-owned code facts.",
            current_subtask="Find the major Django subsystems and a first-pass inspection strategy without replaying all file notes.",
            use_model_compression=None,
        )
        compiled_context = compiled_context_summary(compiled)
        fixture_payload = repo_fixture["content"].get("payload", {})
        repo = fixture_payload.get("repo", {})

        sys_prompt = (
            "You are Repo Architect. Return strict JSON with keys brief_title, architecture_summary, "
            "subsystems, inspection_plan, pinned_terms, source_refs, and confidence. Use the compiled "
            "context packet as the source of truth and use the projected preview only for spot checks."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Preview:\n{projected_preview}\n\n"
            "Task: Produce a concise architecture digest for a large repository analysis benchmark."
        )
        mock_resp = {
            "brief_title": "Django Large-Repo Architecture Digest",
            "architecture_summary": (
                "Django separates request handling, URL routing, HTTP objects, ORM/query construction, "
                "migrations, auth/session security, admin integration, templates, and regression tests. "
                "The memory benchmark should preserve source_refs and exact repo identity while summarizing noisy file notes."
            ),
            "subsystems": [
                {"name": "Request lifecycle", "paths": ["django/core/handlers", "django/http", "django/urls"], "reason": "Entry, routing, middleware, and response boundaries."},
                {"name": "ORM and migrations", "paths": ["django/db/models", "django/db/migrations"], "reason": "Model metadata, query construction, schema evolution, and transactions."},
                {"name": "Auth and sessions", "paths": ["django/contrib/auth", "django/contrib/sessions", "django/middleware/csrf.py"], "reason": "Security-sensitive identity, session, and request protection state."},
                {"name": "Admin and forms", "paths": ["django/contrib/admin", "django/forms"], "reason": "High-level product surface and validation contracts."},
                {"name": "Tests and docs", "paths": ["tests", "docs"], "reason": "Behavioral examples and public API promises."},
            ],
            "inspection_plan": [
                "Start with hot paths before sampling lower-signal generated notes.",
                "Keep source item IDs and GitHub URLs for every architecture claim.",
                "Use component and signal counts to decide what to compress.",
                "Verify private security notes remain role-scoped.",
            ],
            "pinned_terms": [
                "CODE-MEM-BENCH-001",
                "CODE_CONTEXT_MEMORY_001",
                f"REPO: {repo.get('owner', 'django')}/{repo.get('name', 'django')}",
                f"COMMIT: {repo.get('commit_sha')}",
                "PINNED-INVARIANT: preserve source_refs for every code fact that reaches the final briefing",
            ],
            "source_refs": [repo_fixture["id"], analysis_policy["id"]] + file_refs,
            "confidence": 0.9,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        digest_id = "architecture_digest_1"
        source_refs = [repo_fixture["id"], analysis_policy["id"]] + file_refs
        content = make_content(
            goal_id=focus_id,
            artifact_type="architecture_digest",
            payload=llm_response,
            allow_roles=["dependency_mapper", "risk_classifier", "context_compressor", "briefing_author"],
            source_refs=source_refs,
            validation={
                "compiled_context": compile_context_state(compiled),
                "llm_model": "nemotron3:33b",
                "metadata_only_fixture": True,
            },
            do_not_lose=llm_response.get("pinned_terms", []),
        )
        add_item(stub, job_id, digest_id, "Evidence", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.88)))
        link_items(stub, job_id, repo_fixture["id"], digest_id, "summarizes_architecture")
        link_items(stub, job_id, analysis_policy["id"], digest_id, "uses_policy")
        link_items(stub, job_id, focus_id, digest_id, "has_architecture_digest")
        transition_item(stub, job_id, digest_id, status="validated")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "architecture_digest",
            source_refs,
            [digest_id],
            "Created a first-pass architecture digest from a compressed packet over many repo facts.",
        )

        artifact_ids.update({"architecture_digest": digest_id, "architecture_trace": trace_id})
        event = benchmark_event(
            source,
            ROLE,
            "architecture_digest",
            items,
            compiled,
            llm_response,
            expected_terms=llm_response.get("pinned_terms", []),
            expected_source_refs=source_refs,
            extra={
                "source_artifact_id": digest_id,
                "quality_probe": "architecture_subsystem_coverage",
                "subsystem_count": len(llm_response.get("subsystems", [])),
            },
            started_at=agent_started_at,
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_repo_architect=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compile_context_state(compiled),
            benchmark_events=append_benchmark_event(source, event),
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
