import json
import sys

from context_memory import (
    ALL_ROLES,
    add_item,
    add_trace_event,
    context_stub,
    emit_state,
    get_context_logger,
    link_items,
    load_input,
    make_content,
    transition_item,
)


def repeated_briefing(topic, count):
    paragraphs = []
    for index in range(1, count + 1):
        paragraphs.append(
            f"{topic} note {index}: the platform team observed that agent handoffs "
            "begin with compact goals, then accumulate tool outputs, policy notes, "
            "exceptions, user preferences, unresolved blockers, and duplicated status "
            "summaries. The important invariant is to preserve exact identifiers, "
            "deadlines, constraints, and cited source references while discarding "
            "repeated prose and narrative drift."
        )
    return "\n".join(paragraphs)


def main():
    try:
        source = load_input()
        job_id = source.get("job_id", "context_memory_advanced_job_001")
        focus_id = source.get("focus_id", "context_memory_demo_task")
        stub = context_stub()

        task_content = make_content(
            goal_id=focus_id,
            artifact_type="context_engineering_task",
            payload={
                "case_id": "CTX-COMP-ADV-001",
                "goal": "Demonstrate precise context engineering and automatic compression across a growing multi-agent context.",
                "question": "Can each LLM agent use a shorter compiled context packet while preserving non-negotiable facts?",
                "workflow": ALL_ROLES,
                "success_metric": "Final briefing cites pinned IDs, constraints, and compression evidence without replaying every generated note.",
            },
            allow_roles=ALL_ROLES,
            validation={"created_from": "blueprint_initial_input"},
            do_not_lose=[
                "CASE-ID: CTX-COMP-ADV-001",
                "DEADLINE: 2026-05-03T17:00:00-04:00",
                "PINNED-CONSTRAINT: never drop source item ids or exact deadlines",
            ],
        )
        add_item(stub, job_id, focus_id, "Task", "draft", "initializer", task_content)

        source_bundle_id = "source_bundle_1"
        source_bundle_content = make_content(
            goal_id=focus_id,
            artifact_type="source_bundle",
            payload={
                "title": "Long Context Relay Source Bundle",
                "exact_ids": ["SRC-A", "SRC-B", "SRC-C"],
                "deadline": "2026-05-03T17:00:00-04:00",
                "operator_request": (
                    "Build a demo where multiple LLM agents produce increasingly long "
                    "artifacts, while the Membrane context engine gives each turn a "
                    "precise projected and compressed runtime packet."
                ),
                "long_background": repeated_briefing("Background", 18),
                "long_operations_log": repeated_briefing("Operations", 14),
                "long_prior_discussion": repeated_briefing("Prior discussion", 12),
            },
            allow_roles=["context_researcher"],
            validation={"source_kind": "fixture", "verbatim": True},
            do_not_lose=["SRC-A", "SRC-B", "SRC-C", "2026-05-03T17:00:00-04:00"],
        )
        add_item(
            stub,
            job_id,
            source_bundle_id,
            "Evidence",
            "validated",
            "initializer",
            source_bundle_content,
            confidence=0.98,
        )
        link_items(stub, job_id, focus_id, source_bundle_id, "has_source_bundle")

        compression_policy_id = "compression_policy_1"
        compression_policy_content = make_content(
            goal_id=focus_id,
            artifact_type="compression_policy",
            payload={
                "rule_id": "CTX_COMPRESS_001",
                "policy": (
                    "Use Membrane CompileContext before every LLM turn. Prefer exact "
                    "IDs, constraints, source_refs, validation metadata, blockers, "
                    "deadlines, and do_not_lose values over verbose generated prose."
                ),
                "packet_sections": [
                    "objective",
                    "hard_constraints",
                    "shared_state",
                    "retrieved_evidence",
                    "do_not_lose",
                    "compression_trace",
                ],
            },
            allow_roles=ALL_ROLES,
            validation={"source_kind": "fixture", "authoritative": True},
            do_not_lose=["CTX_COMPRESS_001"],
        )
        add_item(
            stub,
            job_id,
            compression_policy_id,
            "Constraint",
            "validated",
            "initializer",
            compression_policy_content,
            confidence=1.0,
        )
        link_items(stub, job_id, focus_id, compression_policy_id, "has_constraint")

        transition_item(stub, job_id, focus_id, status="validated")
        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            "initializer",
            "seed_long_context_demo",
            [],
            [focus_id, source_bundle_id, compression_policy_id],
            "Seeded long source material and compression policy with role-specific projections.",
        )

        emit_state(
            {"job_id": job_id, "focus_id": focus_id, **source},
            artifact_ids={
                "task": focus_id,
                "source_bundle": source_bundle_id,
                "compression_policy": compression_policy_id,
                "initializer_trace": trace_id,
            },
        )
    except RuntimeError as exc:
        if str(exc).startswith("Context Engine is unavailable"):
            print(json.dumps({"error": str(exc), "fatal": True}), file=sys.stderr)
            sys.exit(1)
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        get_context_logger().exception("Agent failed")
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
