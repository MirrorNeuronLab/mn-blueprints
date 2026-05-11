#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


BLUEPRINT_ID = "business_ai_control_room"
BLUEPRINT_NAME = "AI Control Room"
STRENGTH_SCORES = {"strong": 1.0, "medium": 0.7, "weak": 0.35, "missing": 0.0}


def main(argv: list[str] | None = None) -> None:
    _add_repo_paths()

    from mn_blueprint_support.runtime import architecture_contract
    from mn_blueprint_support.worker_contract import create_worker_run_contract

    parser = _build_parser()
    args = parser.parse_args(argv)
    default_config_path = _find_default_config_path()
    inputs, input_source = _resolve_inputs(default_config_path, args)
    contract = create_worker_run_contract(
        BLUEPRINT_ID,
        name=BLUEPRINT_NAME,
        inputs=inputs,
        input_source=input_source,
        default_config_path=default_config_path,
        config_path=args.config,
        config_json=args.config_json,
        run_id=args.run_id,
        runs_root=args.runs_root,
        write_run_store=not args.no_run_store,
    )

    try:
        contract.start()
        result = run_workflow(inputs, contract=contract)
        result["architecture"] = architecture_contract(contract.config or {}, input_source)
        result["config"] = contract.config
        result = contract.finish(result)
    except Exception as exc:  # pragma: no cover
        contract.fail(exc)
        raise
    print(json.dumps(result, indent=2, sort_keys=True))


def run_workflow(inputs: dict[str, Any], *, contract: Any | None = None) -> dict[str, Any]:
    from mn_client_report_skill import build_client_report_outline, render_report_markdown, review_client_report
    from mn_document_reading_skill import read_document
    from mn_implementation_plan_skill import build_implementation_plan, build_risk_register, format_plan_markdown
    from mn_process_map_skill import build_process_map, find_process_gaps, render_mermaid_flowchart

    policies = [
        read_document(policy.get("text", ""), source_name=policy.get("name", f"policy-{index + 1}.md"))
        for index, policy in enumerate(inputs.get("policies") or [])
    ]
    control_matrix = _build_control_matrix(inputs.get("control_framework") or [], inputs.get("evidence_items") or [])
    if contract:
        contract.event(
            "requirements_mapped",
            {
                "policy_count": len(policies),
                "requirement_count": len(control_matrix),
                "mapped_controls": sum(1 for row in control_matrix if row["status"] != "missing"),
            },
        )

    readiness_score = _readiness_score(control_matrix, inputs.get("audit_findings") or [])
    gaps = [row for row in control_matrix if row["status"] in {"missing", "weak"}]
    risks = build_risk_register(_risk_inputs(gaps, inputs.get("audit_findings") or []))
    if contract:
        contract.event(
            "risks_scored",
            {"risk_count": len(risks), "high_risk_gap_count": sum(1 for risk in risks if risk["severity"] >= 12)},
        )

    remediation = build_implementation_plan(
        f"Raise {inputs.get('program', 'program')} control readiness",
        workstreams=[
            {"name": "Governance evidence", "owner": "AI governance lead", "tasks": ["Complete inventory evidence", "Document approval trail"]},
            {"name": "Cyber controls", "owner": "Security lead", "tasks": ["Refresh access review", "Confirm logging coverage"]},
            {"name": "Third-party assurance", "owner": "Vendor risk lead", "tasks": ["Collect security package", "Close privacy evidence gaps"]},
        ],
        timeline_weeks=8,
    )
    architecture_steps = [
        {"label": step, "owner": _owner_for_architecture_step(step)}
        for step in _architecture_steps(inputs.get("system_architecture") or "")
    ]
    process_map = build_process_map(architecture_steps or ["Request", "AI service", "Human review", "Audit log"], name="Control evidence flow")
    report = build_client_report_outline(
        f"{inputs.get('program', 'AI program')} control readiness report",
        audience="Risk committee and audit stakeholders",
        findings=[_gap_sentence(row) for row in gaps] + list(inputs.get("audit_findings") or []),
        recommendations=[f"Close {row['control_id']} evidence gap: {row['requirement']}" for row in gaps[:5]],
    )
    _fill_report_sections(
        report,
        {
            "Executive Summary": " ".join(_executive_risk_summary(readiness_score, gaps, risks)),
            "Current State": f"{len(control_matrix)} control requirements were mapped to available evidence.",
            "Implementation Considerations": "Prioritize controls with missing evidence, weak evidence, policy conflicts, and audit findings.",
            "Next Steps": [
                "Assign control owners and due dates.",
                "Collect retained evidence for missing controls.",
                "Refresh the readiness score after remediation.",
            ],
        },
    )
    evidence_package = {
        "policies_reviewed": [{"name": policy["source_name"], "outline": policy["outline"], "word_count": policy["word_count"]} for policy in policies],
        "evidence_by_control": {
            row["control_id"]: row["evidence"]
            for row in control_matrix
            if row["evidence"]
        },
        "missing_or_weak_controls": gaps,
    }
    final_artifact = {
        "type": "control_readiness_report",
        "product_name": "AI Control Room",
        "program": inputs.get("program"),
        "readiness_score": readiness_score,
        "target_readiness_score": inputs.get("target_readiness_score", 85),
        "executive_risk_summary": _executive_risk_summary(readiness_score, gaps, risks),
        "compliance_gap_report": {
            "gap_count": len(gaps),
            "gaps": gaps,
            "policy_conflicts": _policy_conflicts(policies, control_matrix),
        },
        "control_matrix": control_matrix,
        "risk_register": risks,
        "remediation_plan": {
            "plan": remediation,
            "markdown": format_plan_markdown(remediation),
        },
        "audit_evidence_package": evidence_package,
        "control_process_map": {
            "process": process_map,
            "mermaid": render_mermaid_flowchart(process_map),
            "gaps": find_process_gaps(process_map),
        },
        "client_report_markdown": render_report_markdown(report),
        "quality_review": review_client_report(report),
    }
    if contract:
        contract.event(
            "readiness_pack_generated",
            {"readiness_score": readiness_score, "gap_count": len(gaps), "risk_count": len(risks)},
        )
    return {
        "blueprint": BLUEPRINT_ID,
        "name": BLUEPRINT_NAME,
        "uses_llm": False,
        "uses_simulation": False,
        "llm": {"provider": "deterministic", "calls": 0},
        "metrics": {
            "requirements_count": len(control_matrix),
            "mapped_controls": sum(1 for row in control_matrix if row["status"] != "missing"),
            "missing_controls": sum(1 for row in control_matrix if row["status"] == "missing"),
            "readiness_score": readiness_score,
        },
        "final_artifact": final_artifact,
    }


def _build_control_matrix(framework: list[dict[str, Any]], evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_by_control: dict[str, list[dict[str, Any]]] = {}
    for evidence in evidence_items:
        evidence_by_control.setdefault(str(evidence.get("control_id")), []).append(evidence)

    matrix: list[dict[str, Any]] = []
    for requirement in framework:
        control_id = str(requirement.get("id") or "")
        evidence = evidence_by_control.get(control_id, [])
        strength = max((_strength_score(item.get("strength")) for item in evidence), default=0.0)
        status = "mapped" if strength >= 0.65 else "weak" if strength > 0 else "missing"
        matrix.append(
            {
                "control_id": control_id,
                "domain": requirement.get("domain", ""),
                "requirement": requirement.get("requirement", ""),
                "status": status,
                "evidence_strength": round(strength, 2),
                "evidence": [{"name": item.get("name", ""), "strength": item.get("strength", "missing")} for item in evidence],
            }
        )
    return matrix


def _readiness_score(control_matrix: list[dict[str, Any]], audit_findings: list[str]) -> int:
    if not control_matrix:
        return 0
    average = sum(row["evidence_strength"] for row in control_matrix) / len(control_matrix)
    penalty = min(20, len(audit_findings) * 4)
    return max(0, min(100, round(average * 100 - penalty)))


def _risk_inputs(gaps: list[dict[str, Any]], audit_findings: list[str]) -> list[dict[str, Any]]:
    risks = [
        {
            "risk": f"{row['control_id']} {row['status']} evidence: {row['requirement']}",
            "impact": 5 if row["status"] == "missing" else 4,
            "likelihood": 4 if row["status"] == "missing" else 3,
            "mitigation": f"Assign owner and collect evidence for {row['control_id']}.",
        }
        for row in gaps
    ]
    risks.extend(
        {
            "risk": finding,
            "impact": 4,
            "likelihood": 3,
            "mitigation": "Tie the audit finding to a control owner, due date, and retained evidence.",
        }
        for finding in audit_findings
    )
    return risks


def _policy_conflicts(policies: list[dict[str, Any]], control_matrix: list[dict[str, Any]]) -> list[str]:
    policy_text = " ".join(policy["text"].lower() for policy in policies)
    conflicts = []
    if "human review" in policy_text and any("human" in row["requirement"].lower() and row["status"] == "missing" for row in control_matrix):
        conflicts.append("Policy requires human review, but evidence for human review controls is missing.")
    if "vendor" in policy_text and any("vendor" in row["requirement"].lower() and row["status"] == "missing" for row in control_matrix):
        conflicts.append("Policy requires vendor assurance evidence, but the control package is incomplete.")
    return conflicts


def _executive_risk_summary(score: int, gaps: list[dict[str, Any]], risks: list[dict[str, Any]]) -> list[str]:
    posture = "not ready" if score < 60 else "conditionally ready" if score < 85 else "ready for audit review"
    top_risk = risks[0]["risk"] if risks else "No material risk identified"
    return [
        f"Current readiness score is {score}, so the program is {posture}.",
        f"{len(gaps)} missing or weak control(s) require remediation before an audit package is complete.",
        f"Top risk: {top_risk}.",
    ]


def _architecture_steps(architecture: str) -> list[str]:
    return [re.sub(r"\s+", " ", part).strip() for part in architecture.split("->") if part.strip()]


def _owner_for_architecture_step(step: str) -> str:
    lowered = step.lower()
    if "human" in lowered or "adjuster" in lowered:
        return "Operations control owner"
    if "audit" in lowered or "log" in lowered:
        return "Compliance evidence owner"
    if "policy" in lowered:
        return "Risk policy owner"
    if "retrieval" in lowered or "assistant" in lowered:
        return "AI platform owner"
    return "System owner"


def _gap_sentence(row: dict[str, Any]) -> str:
    return f"{row['control_id']} is {row['status']}: {row['requirement']}"


def _fill_report_sections(report: dict[str, Any], updates: dict[str, Any]) -> None:
    for section in report.get("sections", []):
        value = updates.get(section.get("title"))
        if isinstance(value, list):
            section["bullets"] = value
        elif value:
            section["narrative"] = str(value)


def _strength_score(value: Any) -> float:
    return STRENGTH_SCORES.get(str(value or "missing").lower(), 0.0)


def _resolve_inputs(config_path: Path, args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    payload = dict((config.get("inputs") or {}).get("payload") or {})
    if args.input_file:
        payload.update(json.loads(Path(args.input_file).read_text(encoding="utf-8")))
        return payload, {"adapter": "file", "path": str(args.input_file), "real_ready": True}
    if args.input_json:
        payload.update(json.loads(args.input_json))
        return payload, {"adapter": "json", "real_ready": True}
    if os.getenv("MN_BLUEPRINT_INPUT_JSON"):
        payload.update(json.loads(os.environ["MN_BLUEPRINT_INPUT_JSON"]))
        return payload, {"adapter": "env_json", "env": "MN_BLUEPRINT_INPUT_JSON", "real_ready": True}
    return payload, {"adapter": "mock", "real_ready": False}


def _find_default_config_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config" / "default.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("config/default.json was not found near the blueprint payload")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI Control Room blueprint.")
    parser.add_argument("--input-file")
    parser.add_argument("--input-json")
    parser.add_argument("--config")
    parser.add_argument("--config-json")
    parser.add_argument("--run-id")
    parser.add_argument("--runs-root")
    parser.add_argument("--no-run-store", action="store_true")
    parser.add_argument("--mock-llm", action="store_true", help="Accepted for compatibility; this worker is deterministic.")
    return parser


def _add_repo_paths() -> None:
    needed = [
        "blueprint_support_skill",
        "document_reading_skill",
        "implementation_plan_skill",
        "process_map_skill",
        "client_report_skill",
    ]
    for parent in Path(__file__).resolve().parents:
        skills_root = parent / "mn-skills"
        if skills_root.exists():
            for skill in needed:
                src = skills_root / skill / "src"
                if src.exists() and str(src) not in sys.path:
                    sys.path.insert(0, str(src))
            return


if __name__ == "__main__":
    main()
