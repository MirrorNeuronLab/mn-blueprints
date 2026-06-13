import json
import os
import sys
from collections import Counter
from pathlib import Path

from context_memory import (
    ALL_ROLES,
    add_item,
    add_trace_event,
    append_benchmark_event,
    context_stub,
    emit_state,
    env_bool,
    env_int,
    get_context_logger,
    link_items,
    load_input,
    make_content,
    monotonic_seconds,
    transition_item,
)


FIXTURE_FILE = "django_tree_fixture.json"


def fixture_path():
    configured = os.environ.get("MN_CODE_ANALYSIS_FIXTURE_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "repo_fixture" / FIXTURE_FILE


def load_fixture():
    path = fixture_path()
    data = json.loads(path.read_text())
    data["_fixture_path"] = str(path)
    return data


def source_int(source, key, default):
    if key in source and source[key] not in (None, ""):
        return int(source[key])
    return default


def safe_id(value):
    allowed = []
    for char in str(value or ""):
        allowed.append(char if char.isalnum() or char in {"_", "-"} else "_")
    return "".join(allowed).strip("_")


def resolve_job_id(source):
    explicit = source.get("context_job_id") or os.environ.get("MN_CONTEXT_JOB_ID")
    if explicit:
        return explicit
    base = source.get("job_id", "business_code_analysis_memory_job_001")
    run_id = os.environ.get("MN_RUN_ID", "").strip()
    if run_id:
        return f"{base}_{safe_id(run_id)}"
    return base


def select_files(fixture, max_files):
    hot_paths = set(fixture.get("hot_paths", []))
    files = fixture.get("files", [])
    hot = [entry for entry in files if entry.get("path") in hot_paths]
    rest = [entry for entry in files if entry.get("path") not in hot_paths]
    selected = []
    seen = set()
    for entry in hot + rest:
        path = entry.get("path")
        if not path or path in seen:
            continue
        selected.append(entry)
        seen.add(path)
        if len(selected) >= max_files:
            break
    return selected


def count_values(entries, key):
    counts = Counter()
    for entry in entries:
        value = entry.get(key)
        if isinstance(value, list):
            counts.update(value)
        elif value:
            counts[value] += 1
    return dict(counts.most_common(12))


def file_summary(entry):
    signals = ", ".join(entry.get("signals", [])[:5]) or "general"
    return (
        f"{entry['path']} is a {entry.get('language', 'text')} file in "
        f"{entry.get('component', 'unknown')} with {entry.get('size', 0)} bytes. "
        f"Derived architecture signals: {signals}. "
        "This benchmark stores metadata and generated analysis notes only, not source text."
    )


def analysis_note(entry, note_index):
    signals = entry.get("signals", ["general"])
    repeated = (
        "For context pressure, this note repeats the same high-level instruction: "
        "prefer source_refs, subsystem boundaries, explicit invariants, and exact file paths "
        "over replaying every code-derived observation."
    )
    return {
        "path": entry["path"],
        "note_index": note_index,
        "component": entry.get("component"),
        "signals": signals,
        "observation": (
            f"Inspect {entry['path']} when reasoning about {', '.join(signals[:3])}. "
            f"{entry.get('business_relevance', '')}"
        ),
        "repeated_context_pressure": [repeated, repeated],
    }


def main():
    try:
        agent_started_at = monotonic_seconds()
        source = load_input()
        job_id = resolve_job_id(source)
        focus_id = source.get("focus_id", "repo_code_analysis_task")
        quick_mode = env_bool("MN_BLUEPRINT_QUICK_TEST", default=False)
        fixture = load_fixture()
        scale = fixture.get("scale", {})
        default_max_files = scale.get("quick_test_max_files" if quick_mode else "default_max_files", 260)
        max_files = source_int(
            source,
            "fixture_max_files",
            env_int("MN_CODE_ANALYSIS_FIXTURE_MAX_FILES", default=int(default_max_files)),
        )
        default_notes = 0 if quick_mode else int(scale.get("default_notes_per_file", 1))
        notes_per_file = source_int(
            source,
            "notes_per_file",
            env_int("MN_CODE_ANALYSIS_NOTES_PER_FILE", default=default_notes),
        )
        selected_files = select_files(fixture, max_files)
        repo = fixture["repo"]
        pinned = list(fixture.get("pinned_facts", []))
        pinned.append(f"SELECTED-FILE-COUNT: {len(selected_files)}")

        stub = context_stub()
        task_content = make_content(
            goal_id=focus_id,
            artifact_type="code_analysis_task",
            payload={
                "case_id": "CODE-MEM-BENCH-001",
                "goal": "Analyze a large real repository through the memory layer with bounded context packets.",
                "repo": repo,
                "question": "Can working memory preserve architecture evidence and source refs while hundreds of code facts compete for context?",
                "workflow": ALL_ROLES,
                "benchmark_questions": fixture.get("benchmark_questions", []),
                "selected_file_count": len(selected_files),
                "notes_per_file": notes_per_file,
                "success_metric": "Final briefing names critical subsystems, preserved repo facts, source_refs, compression traces, and private-memory isolation.",
            },
            allow_roles=ALL_ROLES,
            validation={"created_from": "django_tree_fixture", "schema_version": fixture.get("schema_version")},
            do_not_lose=pinned,
        )
        add_item(stub, job_id, focus_id, "Task", "draft", "initializer", task_content)

        fixture_id = "repo_fixture_django"
        component_counts = count_values(selected_files, "component")
        signal_counts = count_values(selected_files, "signals")
        fixture_content = make_content(
            goal_id=focus_id,
            artifact_type="repo_fixture",
            payload={
                "fixture_id": fixture.get("fixture_id"),
                "repo": repo,
                "available_files": scale.get("available_files", len(fixture.get("files", []))),
                "selected_file_count": len(selected_files),
                "notes_per_file": notes_per_file,
                "component_counts": component_counts,
                "signal_counts": signal_counts,
                "hot_paths": fixture.get("hot_paths", []),
                "benchmark_questions": fixture.get("benchmark_questions", []),
                "fixture_path": fixture.get("_fixture_path"),
                "metadata_only": True,
            },
            allow_roles=ALL_ROLES,
            source_refs=[repo["url"], f"{repo['url']}/tree/{repo['commit_sha']}"],
            validation={"source_kind": "github_tree_fixture", "metadata_only": True},
            do_not_lose=pinned,
        )
        add_item(stub, job_id, fixture_id, "Evidence", "validated", "initializer", fixture_content, confidence=0.99)
        link_items(stub, job_id, focus_id, fixture_id, "has_repo_fixture")

        policy_id = "analysis_policy_code_memory_1"
        policy_content = make_content(
            goal_id=focus_id,
            artifact_type="analysis_policy",
            payload={
                "rule_id": "CODE_CONTEXT_MEMORY_001",
                "policy": (
                    "Every agent must call CompileContext before LLM reasoning. Preserve exact repo, commit, "
                    "file paths, source_refs, private-memory boundaries, and compression metrics. Summarize "
                    "low-value repeated notes instead of replaying them."
                ),
                "packet_sections": [
                    "objective",
                    "hard_constraints",
                    "repo_facts",
                    "selected_evidence",
                    "source_refs",
                    "private_memory_boundary",
                    "compression_trace",
                ],
            },
            allow_roles=ALL_ROLES,
            validation={"source_kind": "benchmark_policy", "authoritative": True},
            do_not_lose=["CODE_CONTEXT_MEMORY_001", "CODE-MEM-BENCH-001"],
        )
        add_item(stub, job_id, policy_id, "Constraint", "validated", "initializer", policy_content, confidence=1.0)
        link_items(stub, job_id, focus_id, policy_id, "has_constraint")

        private_note_id = "private_security_review_note_1"
        private_note_content = make_content(
            goal_id=focus_id,
            artifact_type="private_security_note",
            payload={
                "private": True,
                "note": (
                    "Risk review may inspect auth, csrf, session, and middleware files, but this private "
                    "note must only be projected to risk_classifier and briefing_author roles."
                ),
                "expected_isolation": "repo_architect, dependency_mapper, and context_compressor should not receive this payload.",
            },
            allow_roles=["risk_classifier", "briefing_author"],
            validation={"private_memory_boundary": True},
            do_not_lose=["PRIVATE-MEMORY-BOUNDARY"],
        )
        add_item(stub, job_id, private_note_id, "Fact", "validated", "initializer", private_note_content, confidence=1.0)
        link_items(stub, job_id, focus_id, private_note_id, "has_private_review_note")

        file_ids = []
        note_ids = []
        for index, entry in enumerate(selected_files, start=1):
            file_id = f"repo_file_{index:04d}"
            file_ids.append(file_id)
            content = make_content(
                goal_id=focus_id,
                artifact_type="repo_code_file",
                payload={
                    "path": entry["path"],
                    "component": entry.get("component"),
                    "language": entry.get("language"),
                    "size": entry.get("size"),
                    "sha": entry.get("sha"),
                    "signals": entry.get("signals", []),
                    "business_relevance": entry.get("business_relevance"),
                    "generated_summary": file_summary(entry),
                    "metadata_only": True,
                },
                allow_roles=ALL_ROLES,
                source_refs=[entry.get("source_url")],
                validation={"source_kind": "github_tree_blob", "metadata_only": True},
                do_not_lose=[entry["path"], entry.get("source_url", "")],
            )
            add_item(stub, job_id, file_id, "Evidence", "validated", "initializer", content, confidence=0.86)
            link_items(stub, job_id, fixture_id, file_id, "contains_file_fact")

            for note_index in range(1, notes_per_file + 1):
                note_id = f"repo_note_{index:04d}_{note_index}"
                note_ids.append(note_id)
                note_content = make_content(
                    goal_id=focus_id,
                    artifact_type="code_analysis_note",
                    payload=analysis_note(entry, note_index),
                    allow_roles=ALL_ROLES,
                    source_refs=[entry.get("source_url")],
                    validation={"generated_from": file_id, "context_pressure": True},
                )
                add_item(stub, job_id, note_id, "Fact", "validated", "initializer", note_content, confidence=0.72)
                link_items(stub, job_id, fixture_id, note_id, "contains_generated_note")
                link_items(stub, job_id, file_id, note_id, "has_analysis_note")

        transition_item(stub, job_id, focus_id, status="validated")
        trace_id = add_trace_event(
            stub,
            job_id,
            focus_id,
            "initializer",
            "seed_large_code_analysis_fixture",
            [],
            [focus_id, fixture_id, policy_id, private_note_id] + file_ids[:12],
            "Seeded a metadata-only Django repository fixture with many linked code facts and generated notes.",
        )

        emit_state(
            {"job_id": job_id, "focus_id": focus_id, **source},
            artifact_ids={
                "task": focus_id,
                "repo_fixture": fixture_id,
                "analysis_policy": policy_id,
                "private_security_note": private_note_id,
                "initializer_trace": trace_id,
            },
            repo=repo,
            selected_file_count=len(selected_files),
            generated_note_count=len(note_ids),
            total_seed_items=4 + len(file_ids) + len(note_ids),
            component_counts=component_counts,
            signal_counts=signal_counts,
            benchmark_events=append_benchmark_event(
                source,
                {
                    "role": "initializer",
                    "stage": "seed_large_code_analysis_fixture",
                    "agent_wall_seconds": monotonic_seconds() - agent_started_at,
                    "memory_items_created": 4 + len(file_ids) + len(note_ids),
                    "selected_file_count": len(selected_files),
                    "generated_note_count": len(note_ids),
                    "available_fixture_files": scale.get("available_files", len(fixture.get("files", []))),
                    "fixture_metadata_only": True,
                    "repo": repo,
                },
            ),
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
