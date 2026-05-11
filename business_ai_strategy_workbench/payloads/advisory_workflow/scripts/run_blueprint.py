#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


BLUEPRINT_ID = "business_ai_strategy_workbench"
BLUEPRINT_NAME = "AI Strategy Workbench"
THEME_KEYWORDS = {
    "cost_reduction": ("cost", "spend", "sga", "sg&a", "margin", "waste", "shared services"),
    "growth": ("revenue", "growth", "buyer", "customer", "win-rate", "renewal"),
    "operational_bottlenecks": ("manual", "cycle", "backlog", "approval", "scheduling", "delay"),
    "risk": ("risk", "policy", "exception", "quality", "service", "governance"),
    "technology_gaps": ("erp", "cloud", "automation", "data", "workflow", "tagging"),
}


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
    except Exception as exc:  # pragma: no cover - defensive CLI path
        contract.fail(exc)
        raise
    print(json.dumps(result, indent=2, sort_keys=True))


def run_workflow(inputs: dict[str, Any], *, contract: Any | None = None) -> dict[str, Any]:
    from mn_client_report_skill import build_client_report_outline, render_report_markdown, review_client_report
    from mn_document_reading_skill import read_document
    from mn_first_draft_slides_skill import build_slide_outline, render_deck_markdown
    from mn_implementation_plan_skill import build_implementation_plan, build_risk_register, format_plan_markdown
    from mn_market_research_skill import build_market_research_outline, build_research_brief, synthesize_source_notes
    from mn_meeting_summary_skill import build_meeting_summary, format_meeting_summary_markdown
    from mn_process_map_skill import build_process_map, render_mermaid_flowchart
    from mn_spreadsheet_analysis_skill import profile_table, read_csv_table, summarize_table_profile

    documents = [
        read_document(document.get("text", ""), source_name=document.get("name", f"document-{index + 1}.txt"))
        for index, document in enumerate(inputs.get("documents") or [])
    ]
    transcripts = [
        build_meeting_summary(transcript, title=f"Discovery interview {index + 1}")
        for index, transcript in enumerate(inputs.get("meeting_transcripts") or [])
    ]
    if contract:
        contract.event(
            "documents_read",
            {"document_count": len(documents), "transcript_count": len(transcripts)},
        )

    financial_rows = read_csv_table(str(inputs.get("financials_csv") or "metric,baseline,target\n"))
    financial_profile = profile_table(financial_rows)
    financial_observations = summarize_table_profile(financial_profile)

    source_notes = list(inputs.get("market_notes") or [])
    source_notes.extend(
        {"source": document["source_name"], "claims": _sentences(document["text"])[:4]}
        for document in documents
    )
    synthesis = synthesize_source_notes(source_notes)
    research_brief = build_research_brief(
        inputs.get("engagement_goal") or "Strategy discovery",
        audience="board and executive committee",
    )
    benchmark_outline = build_market_research_outline(research_brief, synthesis=synthesis)

    evidence_items = _evidence_items(documents, transcripts, financial_observations, synthesis)
    themes = _cluster_findings(evidence_items)
    if contract:
        contract.event(
            "findings_clustered",
            {"theme_count": len(themes), "finding_count": len(evidence_items)},
        )

    issue_tree = _build_issue_tree(inputs, themes)
    opportunity_map = _build_opportunity_map(themes)
    roadmap = build_implementation_plan(
        f"Deliver {inputs.get('company', 'client')} strategy recommendations",
        workstreams=[
            {"name": "Cost and margin", "owner": "CFO", "outcomes": ["Validated savings cases"]},
            {"name": "Commercial growth", "owner": "Growth lead", "outcomes": ["Quote-cycle improvements"]},
            {"name": "Technology foundation", "owner": "CIO", "outcomes": ["Automation and data controls"]},
        ],
        timeline_weeks=int(inputs.get("roadmap_weeks") or 12),
    )
    risks = build_risk_register(
        [
            {"risk": "Savings assumptions are not validated by process owners", "impact": 4, "likelihood": 3},
            {"risk": "ERP and cloud data quality slows implementation", "impact": 4, "likelihood": 4},
            {"risk": "Local operating teams resist standardization", "impact": 3, "likelihood": 3},
        ]
    )
    process_map = build_process_map(
        [
            {"label": "Ingest client materials", "owner": "Discovery team"},
            {"label": "Extract facts and pain points", "owner": "Research pod"},
            {"label": "Cluster findings into themes", "owner": "Engagement manager"},
            {"label": "Build board recommendation", "owner": "Partner team"},
            {"label": "Approve implementation roadmap", "owner": "Executive sponsor"},
        ],
        name="Discovery to board recommendation",
    )
    slide_sections = [
        {"title": "Executive Summary", "takeaway": "Three near-term opportunities can improve margin and operating focus.", "bullets": _top_opportunities(opportunity_map)},
        {"title": "Issue Tree", "takeaway": "The opportunity set clusters around cost, growth, operating bottlenecks, risk, and technology gaps.", "bullets": list(issue_tree["branches"])},
        {"title": "Opportunity Map", "takeaway": "Start where evidence is strongest and implementation dependencies are visible.", "bullets": [item["opportunity"] for item in opportunity_map[:5]]},
        {"title": "Roadmap", "takeaway": "Sequence discovery, design, build, validate, and launch over the planning window.", "bullets": [f"{phase['name']}: weeks {phase['start_week']}-{phase['end_week']}" for phase in roadmap["phases"]]},
    ]
    slides = build_slide_outline(
        str(inputs.get("engagement_goal") or "Strategy recommendation"),
        sections=slide_sections,
        audience="board and executive committee",
        max_slides=6,
    )
    report = build_client_report_outline(
        f"{inputs.get('company', 'Client')} strategy recommendation",
        audience="Board and executive committee",
        findings=[item["finding"] for item in evidence_items[:6]],
        recommendations=_top_opportunities(opportunity_map),
    )
    _fill_report_sections(
        report,
        {
            "Executive Summary": " ".join(_executive_summary(inputs, opportunity_map, risks)),
            "Current State": "The discovery packet combines client documents, meeting notes, financial metrics, and benchmark claims.",
            "Implementation Considerations": "Sequence work around owners, evidence confidence, data dependencies, and change-management risk.",
            "Next Steps": [
                "Validate top opportunities with owners.",
                "Confirm savings and growth assumptions.",
                "Prepare the board review pack.",
            ],
        },
    )
    final_artifact = {
        "type": "board_ready_strategy_recommendation",
        "product_name": "AI Strategy Workbench",
        "company": inputs.get("company"),
        "executive_summary": _executive_summary(inputs, opportunity_map, risks),
        "issue_tree": issue_tree,
        "opportunity_map": opportunity_map,
        "market_benchmark_outline": benchmark_outline,
        "first_draft_slide_deck": {
            "slides": slides,
            "markdown": render_deck_markdown(slides),
        },
        "recommended_roadmap": {
            "plan": roadmap,
            "markdown": format_plan_markdown(roadmap),
        },
        "risk_register": risks,
        "discovery_process_map": {
            "process": process_map,
            "mermaid": render_mermaid_flowchart(process_map),
        },
        "evidence_appendix": evidence_items,
        "meeting_summaries": [
            {"summary": summary, "markdown": format_meeting_summary_markdown(summary)}
            for summary in transcripts
        ],
        "financial_profile": financial_profile,
        "client_report_markdown": render_report_markdown(report),
        "quality_review": review_client_report(report),
    }
    if contract:
        contract.event(
            "recommendation_pack_generated",
            {
                "opportunity_count": len(opportunity_map),
                "slide_count": len(slides),
                "roadmap_phase_count": len(roadmap["phases"]),
            },
        )
    return {
        "blueprint": BLUEPRINT_ID,
        "name": BLUEPRINT_NAME,
        "uses_llm": False,
        "uses_simulation": False,
        "llm": {"provider": "deterministic", "calls": 0},
        "metrics": {
            "documents_processed": len(documents),
            "findings_count": len(evidence_items),
            "opportunity_count": len(opportunity_map),
            "roadmap_phase_count": len(roadmap["phases"]),
        },
        "final_artifact": final_artifact,
    }


def _evidence_items(
    documents: list[dict[str, Any]],
    transcripts: list[dict[str, Any]],
    financial_observations: list[str],
    synthesis: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for document in documents:
        for sentence in _sentences(document["text"])[:5]:
            items.append({"finding": sentence, "source": document["source_name"], "type": "document"})
    for summary in transcripts:
        for action in summary.get("action_items", []):
            items.append({"finding": f"{action.get('owner') or 'Unassigned'}: {action.get('task')}", "source": summary["title"], "type": "meeting_action"})
        for decision in summary.get("decisions", []):
            items.append({"finding": decision, "source": summary["title"], "type": "meeting_decision"})
    for observation in financial_observations:
        items.append({"finding": observation, "source": "financial_profile", "type": "kpi"})
    for claim in synthesis.get("claims", [])[:8]:
        items.append({"finding": claim["claim"], "source": claim["source"], "type": "benchmark"})
    return items


def _cluster_findings(evidence_items: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    clusters: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in evidence_items:
        lowered = item["finding"].lower()
        matched = False
        for theme, keywords in THEME_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                clusters[theme].append(item)
                matched = True
        if not matched:
            clusters["cross_cutting"].append(item)
    return dict(clusters)


def _build_issue_tree(inputs: dict[str, Any], themes: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    return {
        "root_question": inputs.get("engagement_goal") or "Where should the enterprise focus next?",
        "branches": {
            theme: {
                "evidence_count": len(items),
                "example_evidence": [item["finding"] for item in items[:3]],
            }
            for theme, items in themes.items()
        },
    }


def _build_opportunity_map(themes: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    opportunities = []
    for theme, items in sorted(themes.items(), key=lambda value: len(value[1]), reverse=True):
        opportunities.append(
            {
                "theme": theme,
                "opportunity": theme.replace("_", " ").title(),
                "evidence_count": len(items),
                "confidence": "high" if len(items) >= 4 else "medium" if len(items) >= 2 else "low",
                "first_move": _first_move(theme),
                "source_refs": sorted({item["source"] for item in items})[:6],
            }
        )
    return opportunities


def _first_move(theme: str) -> str:
    return {
        "cost_reduction": "Validate SG&A and cloud spend reduction cases with owners.",
        "growth": "Prioritize quote-cycle automation around high-value customer segments.",
        "operational_bottlenecks": "Map approval and backlog handoffs before redesigning workflows.",
        "risk": "Create named controls for exception handling and service reliability.",
        "technology_gaps": "Establish ERP data-quality and automation ownership.",
    }.get(theme, "Assign an executive owner and test the evidence base.")


def _top_opportunities(opportunity_map: list[dict[str, Any]]) -> list[str]:
    return [item["first_move"] for item in opportunity_map[:4]]


def _executive_summary(inputs: dict[str, Any], opportunity_map: list[dict[str, Any]], risks: list[dict[str, Any]]) -> list[str]:
    company = inputs.get("company") or "The client"
    top = opportunity_map[0]["opportunity"] if opportunity_map else "operating focus"
    risk = risks[0]["risk"] if risks else "execution risk"
    return [
        f"{company} has a near-term opportunity to improve {top.lower()} with evidence-backed action.",
        "The recommendation pack should move from discovery to owner validation before major investment decisions.",
        f"The main execution risk is {risk.lower()}; the roadmap makes that dependency explicit.",
    ]


def _fill_report_sections(report: dict[str, Any], updates: dict[str, Any]) -> None:
    for section in report.get("sections", []):
        value = updates.get(section.get("title"))
        if isinstance(value, list):
            section["bullets"] = value
        elif value:
            section["narrative"] = str(value)


def _sentences(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", sentence).strip(" -")
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if re.sub(r"\s+", " ", sentence).strip(" -#")
    ]


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
    parser = argparse.ArgumentParser(description="Run the AI Strategy Workbench blueprint.")
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
        "meeting_summary_skill",
        "first_draft_slides_skill",
        "market_research_skill",
        "spreadsheet_analysis_skill",
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
