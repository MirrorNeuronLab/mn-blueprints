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


def main():
    try:
        source = load_input()
        job_id = source.get("job_id", "audit_job_777")
        focus_id = source.get("focus_id", "audit_task_1")
        stub = context_stub()

        task_content = make_content(
            goal_id=focus_id,
            artifact_type="audit_task",
            payload={
                "case_id": "C_992",
                "goal": "Perform financial compliance audit",
                "question": "Did the agent disclose the fee before confirming customer agreement?",
                "workflow": [
                    "policy_interpreter",
                    "evidence_extractor",
                    "risk_classifier",
                    "decision_agent",
                    "critic_auditor",
                ],
            },
            allow_roles=ALL_ROLES,
            validation={"created_from": "blueprint_initial_input"},
        )
        add_item(stub, job_id, focus_id, "Task", "draft", "initializer", task_content)

        transcript_id = "transcript_1"
        transcript_content = make_content(
            goal_id=focus_id,
            artifact_type="raw_transcript",
            payload={
                "call_id": "C_992",
                "text": (
                    "Agent: I can waive that fee for you today. "
                    "Customer: Oh, okay. "
                    "Agent: The fee is $50. Do you agree?"
                ),
            },
            allow_roles=["evidence_extractor"],
            validation={"source_kind": "fixture", "verbatim": True},
        )
        add_item(
            stub,
            job_id,
            transcript_id,
            "Evidence",
            "validated",
            "initializer",
            transcript_content,
        )
        link_items(stub, job_id, focus_id, transcript_id, "has_evidence")

        policy_id = "policy_1"
        policy_content = make_content(
            goal_id=focus_id,
            artifact_type="policy_document",
            payload={
                "rule_id": "FEE_DISCLOSURE_001",
                "text": "Agent must clearly disclose any fee before confirming customer agreement.",
            },
            allow_roles=["policy_interpreter"],
            validation={"source_kind": "fixture", "authoritative": True},
        )
        add_item(
            stub,
            job_id,
            policy_id,
            "Constraint",
            "validated",
            "initializer",
            policy_content,
        )
        link_items(stub, job_id, focus_id, policy_id, "has_constraint")

        transition_item(stub, job_id, focus_id, status="validated")
        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            "initializer",
            "seed_context",
            [],
            [focus_id, transcript_id, policy_id],
            "Seeded task, raw transcript, and policy with role-specific ACLs.",
        )

        emit_state(
            {"job_id": job_id, "focus_id": focus_id, **source},
            artifact_ids={
                "task": focus_id,
                "raw_transcript": transcript_id,
                "policy_document": policy_id,
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
