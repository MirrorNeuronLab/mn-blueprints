#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


BLUEPRINT_ID = "business_vendor_decision_agent"
BLUEPRINT_NAME = "Vendor Decision Agent"


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
    from mn_code_generation_skill import build_script_spec, render_python_script
    from mn_first_draft_slides_skill import build_slide_outline, render_deck_markdown
    from mn_implementation_plan_skill import build_implementation_plan, build_risk_register, format_plan_markdown
    from mn_process_map_skill import build_process_map, render_mermaid_flowchart
    from mn_spreadsheet_analysis_skill import profile_table, read_csv_table, summarize_table_profile
    from mn_vendor_comparison_skill import build_comparison_matrix, recommend_vendor

    criteria = inputs.get("weighted_criteria") or []
    vendors = inputs.get("vendors") or []
    matrix = build_comparison_matrix(vendors, criteria)
    recommendation = recommend_vendor(matrix["ranking"])
    if contract:
        contract.event(
            "vendors_scored",
            {"vendor_count": len(vendors), "criteria_count": len(criteria), "recommended": recommendation["recommended"]},
        )

    pricing_rows = read_csv_table(str(inputs.get("pricing_csv") or "vendor,year_one_cost_usd\n"))
    pricing_profile = profile_table(pricing_rows)
    missing_answers = _missing_answers(vendors, criteria)
    vendor_risks = _vendor_risks(vendors, missing_answers)
    risk_register = build_risk_register(vendor_risks)
    roadmap = build_implementation_plan(
        f"Implement {recommendation['recommended'] or 'selected vendor'} for {inputs.get('initiative', 'the initiative')}",
        workstreams=[
            {"name": "Commercial negotiation", "owner": "Procurement", "tasks": ["Lock pricing", "Clarify implementation assumptions"]},
            {"name": "Security and architecture", "owner": "CISO / enterprise architecture", "tasks": ["Review evidence", "Confirm integration controls"]},
            {"name": "Pilot delivery", "owner": "Transformation office", "tasks": ["Launch pilot", "Measure adoption and service impact"]},
        ],
        timeline_weeks=int(inputs.get("timeline_weeks") or 12),
    )
    if contract:
        contract.event(
            "roadmap_generated",
            {"roadmap_phase_count": len(roadmap["phases"]), "risk_count": len(risk_register)},
        )

    process_map = build_process_map(
        [
            {"label": "Confirm requirements", "owner": "Business sponsor"},
            {"label": "Issue RFP / RFI", "owner": "Procurement"},
            {"label": "Normalize responses", "owner": "Evaluation team"},
            {"label": "Score vendors", "owner": "Steering committee"},
            {"label": "Negotiate finalist", "owner": "Procurement"},
            {"label": "Launch implementation roadmap", "owner": "Transformation office"},
        ],
        name="Vendor decision process",
    )
    script_spec = build_script_spec(
        "normalize_vendor_pricing",
        "Normalize vendor pricing rows before weighted scoring.",
        inputs=["vendor pricing CSV"],
        outputs=["normalized pricing records"],
    )
    rfp_package = _build_rfp_package(inputs)
    report = build_client_report_outline(
        f"{inputs.get('initiative', 'Vendor selection')} recommendation memo",
        audience="CIO, procurement, and transformation steering committee",
        findings=[
            f"{recommendation['recommended']} leads the weighted evaluation with {recommendation['confidence']} confidence.",
            *summarize_table_profile(pricing_profile)[:3],
        ],
        recommendations=[
            recommendation["rationale"],
            "Use negotiation questions to resolve vague claims before award.",
            "Start the pilot roadmap only after security evidence is complete.",
        ],
    )
    _fill_report_sections(
        report,
        {
            "Executive Summary": f"{recommendation['recommended']} is the recommended vendor based on weighted scoring, with {recommendation['confidence']} confidence.",
            "Current State": f"{len(vendors)} vendors were compared across {len(criteria)} weighted criteria.",
            "Implementation Considerations": "Do not start the pilot until pricing, security evidence, implementation assumptions, and data-portability terms are clear.",
            "Next Steps": [
                "Issue negotiation questions to finalists.",
                "Confirm security and architecture evidence.",
                "Approve roadmap gates with the steering committee.",
            ],
        },
    )
    slides = build_slide_outline(
        inputs.get("initiative") or "Vendor decision",
        sections=[
            {"title": "Decision Summary", "takeaway": recommendation["rationale"], "bullets": [f"Confidence: {recommendation['confidence']}", f"Margin to next option: {recommendation.get('margin', 0)}"]},
            {"title": "Comparison Matrix", "takeaway": "Weighted criteria make tradeoffs explicit.", "bullets": [f"{row['vendor']}: {row['weighted_score']}" for row in matrix["ranking"]]},
            {"title": "Implementation Roadmap", "takeaway": "Move from negotiation to pilot with security and architecture gates.", "bullets": [f"{phase['name']}: weeks {phase['start_week']}-{phase['end_week']}" for phase in roadmap["phases"]]},
        ],
        audience="executive steering committee",
        max_slides=5,
    )
    final_artifact = {
        "type": "vendor_selection_recommendation",
        "product_name": "Vendor Decision Agent",
        "initiative": inputs.get("initiative"),
        "rfp_rfi_package": rfp_package,
        "vendor_comparison_matrix": matrix,
        "recommendation_memo": {
            "recommended_vendor": recommendation["recommended"],
            "confidence": recommendation["confidence"],
            "rationale": recommendation["rationale"],
            "missing_answers": missing_answers,
            "vendor_risks": vendor_risks,
        },
        "implementation_roadmap": {
            "plan": roadmap,
            "markdown": format_plan_markdown(roadmap),
        },
        "cost_risk_model": {
            "pricing_profile": pricing_profile,
            "observations": summarize_table_profile(pricing_profile),
            "risk_register": risk_register,
        },
        "process_map": {
            "process": process_map,
            "mermaid": render_mermaid_flowchart(process_map),
        },
        "negotiation_questions": _negotiation_questions(vendors, missing_answers),
        "first_draft_slide_deck": {
            "slides": slides,
            "markdown": render_deck_markdown(slides),
        },
        "generated_script_scaffold": {
            "spec": script_spec,
            "python": render_python_script(script_spec),
        },
        "client_report_markdown": render_report_markdown(report),
        "quality_review": review_client_report(report),
    }
    if contract:
        contract.event(
            "recommendation_generated",
            {"recommended": recommendation["recommended"], "missing_answer_count": len(missing_answers)},
        )
    return {
        "blueprint": BLUEPRINT_ID,
        "name": BLUEPRINT_NAME,
        "uses_llm": False,
        "uses_simulation": False,
        "llm": {"provider": "deterministic", "calls": 0},
        "metrics": {
            "vendor_count": len(vendors),
            "criteria_count": len(criteria),
            "missing_answer_count": len(missing_answers),
            "roadmap_phase_count": len(roadmap["phases"]),
            "weighted_vendor_score": matrix["ranking"][0]["weighted_score"] if matrix["ranking"] else 0,
        },
        "final_artifact": final_artifact,
    }


def _build_rfp_package(inputs: dict[str, Any]) -> dict[str, Any]:
    requirements = list(inputs.get("requirements") or [])
    return {
        "initiative": inputs.get("initiative"),
        "sections": [
            "Company context and business objectives",
            "Functional and integration requirements",
            "Security, privacy, and compliance evidence",
            "Implementation plan, resourcing, and timeline",
            "Commercial model, assumptions, and negotiation terms",
        ],
        "requirements": requirements,
        "response_template": [
            {"field": "requirement_fit", "prompt": "Explain fit against each stated requirement."},
            {"field": "security_evidence", "prompt": "Attach controls, certifications, audit logs, and policy evidence."},
            {"field": "implementation_assumptions", "prompt": "List timeline, dependencies, client resources, and exclusions."},
            {"field": "pricing", "prompt": "Break out subscription, services, implementation, support, and optional costs."},
        ],
    }


def _missing_answers(vendors: list[dict[str, Any]], criteria: list[dict[str, Any]]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    criterion_names = [str(item.get("name") if isinstance(item, dict) else item) for item in criteria]
    for vendor in vendors:
        scores = vendor.get("scores", {})
        for criterion in criterion_names:
            if criterion not in scores:
                missing.append({"vendor": vendor.get("name", ""), "field": criterion, "reason": "No score or response provided."})
        notes = str(vendor.get("notes") or "").lower()
        if "vague" in notes:
            missing.append({"vendor": vendor.get("name", ""), "field": "implementation_assumptions", "reason": "Response contains vague implementation claims."})
        if "incomplete" in notes:
            missing.append({"vendor": vendor.get("name", ""), "field": "security_evidence", "reason": "Security or audit evidence appears incomplete."})
    return missing


def _vendor_risks(vendors: list[dict[str, Any]], missing_answers: list[dict[str, str]]) -> list[dict[str, Any]]:
    risks = [
        {
            "risk": f"{item['vendor']} unresolved {item['field']}: {item['reason']}",
            "impact": 4,
            "likelihood": 3,
            "mitigation": "Require written clarification before finalist award.",
            "owner": "Procurement",
        }
        for item in missing_answers
    ]
    for vendor in vendors:
        if float(vendor.get("pricing_usd") or 0) > 800000:
            risks.append(
                {
                    "risk": f"{vendor.get('name')} may exceed first-year budget tolerance.",
                    "impact": 3,
                    "likelihood": 3,
                    "mitigation": "Negotiate implementation services and phased licensing.",
                    "owner": "Procurement",
                }
            )
    return risks


def _negotiation_questions(vendors: list[dict[str, Any]], missing_answers: list[dict[str, str]]) -> list[str]:
    questions = [
        f"{item['vendor']}: Please provide a concrete answer for {item['field']} because {item['reason'].lower()}"
        for item in missing_answers
    ]
    if not questions:
        questions.append("Confirm final pricing, implementation assumptions, termination terms, and data portability obligations.")
    for vendor in vendors:
        questions.append(f"{vendor.get('name')}: What implementation resources are included in the quoted price?")
    return questions


def _fill_report_sections(report: dict[str, Any], updates: dict[str, Any]) -> None:
    for section in report.get("sections", []):
        value = updates.get(section.get("title"))
        if isinstance(value, list):
            section["bullets"] = value
        elif value:
            section["narrative"] = str(value)


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
    parser = argparse.ArgumentParser(description="Run the Vendor Decision Agent blueprint.")
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
        "vendor_comparison_skill",
        "spreadsheet_analysis_skill",
        "implementation_plan_skill",
        "process_map_skill",
        "code_generation_skill",
        "first_draft_slides_skill",
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
