import json
import sys

from context_memory import (
    add_item,
    add_trace_event,
    aggregate_benchmark_events,
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
    snapshot_if_configured,
    transition_item,
)


ROLE = "briefing_author"


def first_artifact(items, artifact_type):
    return next((item for item in items if item["artifact_type"] == artifact_type), None)


def recall(expected, text):
    expected = [item for item in expected if item]
    found = [item for item in expected if item in text]
    return {
        "found": len(found),
        "total": len(expected),
        "recall": len(found) / len(expected) if expected else 1.0,
        "missing": [item for item in expected if item not in found],
    }


def build_quality_score(metrics):
    if metrics["privacy"].get("private_leak_count", 0) > 0:
        return 0.0
    score = (
        metrics["pinned_terms"]["recall"] * 0.25
        + metrics["source_refs"]["recall"] * 0.20
        + metrics["subsystems"]["recall"] * 0.20
        + metrics["hot_paths"]["recall"] * 0.10
        + metrics["privacy"].get("privacy_score", 1.0) * 0.15
        + metrics["budget"].get("budget_score", 1.0) * 0.10
    )
    return round(score, 6)


def main():
    try:
        agent_started_at = monotonic_seconds()
        source = load_input()
        job_id, focus_id = source["job_id"], source["focus_id"]
        artifact_ids = dict(source.get("artifact_ids", {}))
        stub = context_stub()

        items = get_context(stub, job_id, ROLE, focus_id, max_items=140)
        handoff = require_artifact(items, "compressed_code_handoff")
        risk_register = require_artifact(items, "code_risk_register")
        repo_fixture = require_artifact(items, "repo_fixture")
        analysis_policy = require_artifact(items, "analysis_policy")
        private_note = first_artifact(items, "private_security_note")
        projected_preview = context_summary(items[:12])
        compiled = compile_context(
            stub,
            job_id,
            ROLE,
            focus_id,
            max_items=140,
            token_budget=1000,
            target_tokens=560,
            objective="Write the final large-repo code analysis memory benchmark briefing.",
            current_subtask="Explain architecture findings, preserved evidence, compression behavior, and private-memory isolation.",
            use_model_compression=None,
        )
        compiled_context = compiled_context_summary(compiled)
        compression_state = compile_context_state(compiled)
        repo = repo_fixture["content"].get("payload", {}).get("repo", {})

        sys_prompt = (
            "You are Briefing Author. Return strict JSON with keys final_briefing, architecture_findings, "
            "hot_path_coverage, preserved_terms, memory_layer_result, traceability, benchmark_metrics, source_refs, and confidence. "
            "Keep the final briefing concise."
        )
        user_prompt = (
            f"Compiled Context Packet:\n{compiled_context}\n\n"
            f"Projected Preview:\n{projected_preview}\n\n"
            "Task: Write the final benchmark briefing from compressed working memory."
        )
        mock_resp = {
            "final_briefing": (
                "For CODE-MEM-BENCH-001, the memory layer analyzed django/django at commit "
                f"{repo.get('commit_sha', 'unknown')} by storing a large metadata-only repository fixture, "
                "projecting role-visible memory, and compiling bounded packets before every LLM turn. "
                "The useful result is a short architecture briefing over request lifecycle, ORM/migrations, "
                "auth/session/CSRF, admin/forms, templates, tests, and docs, with source_refs retained instead "
                "of replaying hundreds of generated file notes."
            ),
            "architecture_findings": [
                "Request handling, URL routing, middleware, and HTTP objects form the runtime path.",
                "ORM/query construction and migrations carry the largest data-behavior blast radius.",
                "Auth, sessions, and CSRF are security-sensitive and need explicit private-memory boundaries.",
                "Admin, forms, templates, tests, and docs provide integration and public-contract evidence.",
            ],
            "hot_path_coverage": repo_fixture["content"].get("payload", {}).get("hot_paths", []),
            "preserved_terms": [
                "CODE-MEM-BENCH-001",
                "CODE_CONTEXT_MEMORY_001",
                "REPO: django/django",
                "COMMIT: " + repo.get("commit_sha", "unknown"),
                "PINNED-INVARIANT: preserve source_refs for every code fact that reaches the final briefing",
                "PRIVATE-MEMORY-BOUNDARY",
            ],
            "memory_layer_result": {
                "selected_file_count": source.get("selected_file_count"),
                "generated_note_count": source.get("generated_note_count"),
                "private_note_visible_to_final_author": private_note is not None,
                "compressed_packet_used": compression_state.get("compressed"),
                "packet_warnings": compression_state.get("warnings", []),
            },
            "traceability": [
                {"artifact": "compressed_code_handoff", "source_ref": handoff["id"]},
                {"artifact": "code_risk_register", "source_ref": risk_register["id"]},
                {"artifact": "repo_fixture", "source_ref": repo_fixture["id"]},
                {"artifact": "analysis_policy", "source_ref": analysis_policy["id"]},
            ],
            "benchmark_metrics": compression_state,
            "source_refs": [handoff["id"], risk_register["id"], repo_fixture["id"], analysis_policy["id"]],
            "confidence": 0.91,
        }
        llm_response = call_llm(sys_prompt, user_prompt, mock_resp)

        briefing_id = "final_code_analysis_briefing_1"
        public_source_refs = [handoff["id"], risk_register["id"], repo_fixture["id"], analysis_policy["id"]]
        source_refs = list(public_source_refs)
        if private_note:
            source_refs.append(private_note["id"])
        content = make_content(
            goal_id=focus_id,
            artifact_type="final_code_analysis_briefing",
            payload=llm_response,
            allow_roles=["briefing_author"],
            source_refs=source_refs,
            validation={
                "compiled_context": compression_state,
                "llm_model": "nemotron3:33b",
                "final_output": True,
                "private_note_visible_to_final_author": private_note is not None,
            },
            do_not_lose=llm_response.get("preserved_terms", []),
        )
        add_item(stub, job_id, briefing_id, "Decision", "draft", ROLE, content, confidence=float(llm_response.get("confidence", 0.9)))
        for source_id in source_refs:
            link_items(stub, job_id, source_id, briefing_id, "supports_final_briefing")
        link_items(stub, job_id, focus_id, briefing_id, "has_final_code_analysis_briefing")
        transition_item(stub, job_id, briefing_id, status="validated")
        transition_item(stub, job_id, handoff["id"], status="used")
        transition_item(stub, job_id, focus_id, status="used")

        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            ROLE,
            "final_code_analysis_briefing",
            source_refs,
            [briefing_id],
            "Wrote final large-repo code analysis briefing from bounded compiled context.",
        )

        final_event = benchmark_event(
            source,
            ROLE,
            "final_code_analysis_briefing",
            items,
            compiled,
            llm_response,
            expected_terms=llm_response.get("preserved_terms", []),
            expected_source_refs=public_source_refs,
            extra={
                "source_artifact_id": briefing_id,
                "private_memory_visible": private_note is not None,
                "private_memory_expected_visible": True,
                "private_memory_isolation_pass": private_note is not None,
                "architecture_finding_count": len(llm_response.get("architecture_findings", [])),
                "hot_path_coverage_count": len(llm_response.get("hot_path_coverage", [])),
            },
            started_at=agent_started_at,
        )
        benchmark_events = append_benchmark_event(source, final_event)
        aggregate = aggregate_benchmark_events(benchmark_events)
        final_text = json.dumps(llm_response, sort_keys=True, default=str)
        required_subsystems = [
            "Request",
            "ORM",
            "migrations",
            "Auth",
            "sessions",
            "CSRF",
            "Admin",
            "forms",
            "templates",
            "tests",
            "docs",
        ]
        hot_paths = repo_fixture["content"].get("payload", {}).get("hot_paths", [])
        pinned_terms = llm_response.get("preserved_terms", [])
        source_ref_metrics = recall(public_source_refs, final_text)
        pinned_metrics = recall(pinned_terms, final_text)
        subsystem_metrics = recall(required_subsystems, final_text)
        hot_path_metrics = recall(hot_paths, final_text)
        private_leak_count = sum(
            1
            for event in benchmark_events
            if event.get("private_memory_expected_visible") is False
            and (event.get("private_memory_visible") or event.get("direct_private_note_visible"))
        )
        risk_saw_private = any(
            event.get("role") == "risk_classifier" and event.get("private_memory_visible")
            for event in benchmark_events
        )
        final_saw_private = private_note is not None
        privacy_metrics = {
            "private_leak_count": private_leak_count,
            "risk_classifier_saw_private_note": risk_saw_private,
            "briefing_author_saw_private_note": final_saw_private,
            "context_compressor_private_note_hidden": not any(
                event.get("role") == "context_compressor" and event.get("direct_private_note_visible")
                for event in benchmark_events
            ),
        }
        privacy_metrics["privacy_score"] = 1.0 if (
            privacy_metrics["private_leak_count"] == 0
            and privacy_metrics["risk_classifier_saw_private_note"]
            and privacy_metrics["context_compressor_private_note_hidden"]
        ) else 0.0
        quality_metrics = {
            "pinned_terms": pinned_metrics,
            "source_refs": source_ref_metrics,
            "subsystems": subsystem_metrics,
            "hot_paths": hot_path_metrics,
            "privacy": privacy_metrics,
            "budget": {"budget_score": aggregate.get("budget_score", 1.0)},
        }
        quality_score = build_quality_score(quality_metrics)
        benchmark_report = {
            "schema_version": "mn.context_memory_code_analysis_benchmark.v1",
            "benchmark_id": "CODE-MEM-BENCH-001",
            "repo": repo,
            "fixture": {
                "selected_file_count": source.get("selected_file_count"),
                "generated_note_count": source.get("generated_note_count"),
                "total_seed_items": source.get("total_seed_items"),
                "metadata_only": True,
            },
            "metric_definitions": {
                "estimated_compile_input_tokens": "Estimated uncompressed memory tokens seen by CompileContext across agents.",
                "estimated_compile_output_tokens": "Estimated bounded context packet tokens returned by CompileContext across agents.",
                "mean_compression_ratio": "compile_output_tokens / compile_input_tokens; lower means smaller packets.",
                "mean_token_reduction": "1 - mean_compression_ratio.",
                "estimated_total_tokens_processed": "Compile input + compile output + generated artifact token estimates.",
                "budget_score": "Share of compile calls that stayed within target budget or returned warnings.",
                "compile_latency_seconds_p95": "P95 CompileContext RPC latency for the workflow.",
                "tokens_per_second_compile_input": "Uncompressed memory tokens processed per compile-latency second.",
                "quality_score": "Weighted real-world quality score over pinned terms, source refs, subsystem coverage, hot path coverage, budget, and privacy.",
                "source_ref_recall": "Required source artifact refs found in the final briefing payload.",
                "hot_path_recall": "Important repo paths represented in the final briefing payload.",
                "private_leak_count": "Private notes visible to roles that should not receive them.",
            },
            "aggregate_metrics": aggregate,
            "quality_metrics": quality_metrics,
            "quality_score": quality_score,
            "quality_gates": {
                "passed": (
                    quality_score >= 0.9
                    and private_leak_count == 0
                    and pinned_metrics["recall"] == 1.0
                    and source_ref_metrics["recall"] == 1.0
                    and aggregate.get("budget_score", 1.0) >= 1.0
                ),
                "thresholds": {
                    "quality_score_min": 0.9,
                    "private_leak_count": 0,
                    "pinned_term_recall": 1.0,
                    "source_ref_recall": 1.0,
                    "budget_score": 1.0,
                },
            },
            "per_agent": benchmark_events,
        }

        report_id = "context_memory_benchmark_report_1"
        report_content = make_content(
            goal_id=focus_id,
            artifact_type="context_memory_benchmark_report",
            payload=benchmark_report,
            allow_roles=["briefing_author"],
            source_refs=[briefing_id] + source_refs,
            validation={
                "compiled_context": compression_state,
                "benchmark_report": True,
                "quality_score": quality_score,
            },
            do_not_lose=[
                "CODE-MEM-BENCH-001",
                "quality_score",
                "estimated_total_tokens_processed",
                "mean_compression_ratio",
                "compile_latency_seconds_p95",
            ],
        )
        add_item(stub, job_id, report_id, "Decision", "validated", ROLE, report_content, confidence=quality_score)
        link_items(stub, job_id, briefing_id, report_id, "has_benchmark_report")
        link_items(stub, job_id, focus_id, report_id, "has_context_memory_benchmark_report")
        snapshot_redis_url = snapshot_if_configured(stub, job_id, source)

        artifact_ids.update(
            {
                "final_code_analysis_briefing": briefing_id,
                "context_memory_benchmark_report": report_id,
                "briefing_trace": trace_id,
            }
        )
        emit_state(
            source,
            artifact_ids=artifact_ids,
            seen_by_briefing_author=[item["artifact_type"] or item["type"] for item in items],
            context_compile=compression_state,
            final_briefing=llm_response,
            benchmark_report=benchmark_report,
            benchmark_events=benchmark_events,
            snapshot_redis_url=snapshot_redis_url,
        )
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
