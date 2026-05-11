# Vendor Decision Agent

`Blueprint ID:` `business_vendor_decision_agent`  
`Category:` business - Business Solution Template  
`Default LLM:` Ollama `nemotron3:33b` metadata, deterministic local artifact generation for tests  

## One-line value proposition

Turn requirements and vendor responses into a scored recommendation and implementation roadmap.

## What it is

This blueprint supports RFP/RFI, vendor comparison, pricing analysis, executive recommendation, and implementation planning work. It ingests business requirements, weighted criteria, vendor responses, pricing tables, and stakeholder notes, then produces an RFP package, comparison matrix, recommendation memo, roadmap, process map, cost/risk model, and negotiation questions.

## Who this is for

CIO offices, procurement, transformation offices, private-equity operating teams, enterprise architecture teams, and teams choosing ERP, CRM, cloud, cybersecurity, AI, robotics, outsourcing, or implementation partners.

## Why it matters

Vendor decisions are often expensive, political, and evidence-heavy. A static dashboard can show scores, and a one-shot LLM can summarize vendor prose, but neither reliably normalizes responses, exposes missing answers, connects risks to implementation, and produces executive-ready artifacts.

## Why this runtime is useful here

MirrorNeuron turns vendor selection into a repeatable workflow with a standard input contract, run ID, event log, and retained final artifact. That makes it easier to compare scenarios, replace mock inputs with real RFP exports, and preserve how the recommendation was reached.

## How it works

1. Load requirements, weighted criteria, vendor responses, pricing, and stakeholder notes.
2. Generate an RFP/RFI package and response template.
3. Normalize vendor scores into a comparison matrix.
4. Score vendors against weighted criteria.
5. Detect vague claims, missing answers, pricing risk, and security gaps.
6. Generate a recommendation memo, roadmap, process map, negotiation questions, and report Markdown.

## Example scenario

A CIO team is choosing an AI-enabled field service platform. BrightOps leads the weighted evaluation because security and implementation scores offset higher cost, while other vendors require clarification on ERP migration estimates and audit-log evidence.

## Inputs

| Input | What it controls | Example | Can customize? |
|---|---|---|---|
| `initiative` | Decision context. | AI-enabled field service platform | Yes |
| `requirements` | Business, security, and implementation needs. | ERP integration, RBAC, offline workflows | Yes |
| `weighted_criteria` | Scoring criteria and weights. | Functional fit, security, speed, cost | Yes |
| `vendors` | Vendor response records and scores. | AtlasFlow, BrightOps, CoreRoute | Yes |
| `pricing_csv` | Cost table for profiling. | Year-one and implementation cost | Yes |
| `stakeholder_notes` | Qualitative concerns. | Security evidence before award | Yes |
| `timeline_weeks` | Roadmap duration. | `14` | Yes |

## Outputs

| Output | What it means | Where to look |
|---|---|---|
| `rfp_rfi_package` | Draft package and response template. | `final_artifact.rfp_rfi_package` |
| `vendor_comparison_matrix` | Weighted scoring and raw matrix. | `final_artifact.vendor_comparison_matrix` |
| `recommendation_memo` | Recommended vendor and rationale. | `final_artifact.recommendation_memo` |
| `implementation_roadmap` | Phased plan and milestones. | `final_artifact.implementation_roadmap` |
| `cost_risk_model` | Pricing profile and risk register. | `final_artifact.cost_risk_model` |
| `negotiation_questions` | Clarifying questions before award. | `final_artifact.negotiation_questions` |

## How to run

```bash
cd business_vendor_decision_agent
python3 payloads/vendor_workflow/scripts/run_blueprint.py \
  --runs-root /tmp/mirror-neuron-runs
```

Run with a real RFP packet:

```bash
python3 payloads/vendor_workflow/scripts/run_blueprint.py \
  --input-file /path/to/vendor_packet.json \
  --runs-root /tmp/mirror-neuron-runs
```

## How to customize it

Replace mock vendors with RFP exports, security questionnaires, pricing sheets, architecture constraints, stakeholder interview notes, and procurement policies. Adjust criteria, weights, missing-answer rules, risk scoring, and roadmap phases for the decision type.

## What to look for in results

Start with the weighted ranking, then inspect missing answers and risk register before trusting the recommendation. A good run highlights both the best vendor and the unresolved questions that should shape negotiation.

## Investor and evaluator narrative

Vendor selection is a high-value transformation workflow with repeatable artifacts and measurable outcomes. The wedge is an RFP copilot that moves from comparison to implementation readiness rather than stopping at text summarization.

## Runtime features demonstrated

- RFP/RFI package generation
- vendor comparison matrix
- weighted scoring
- spreadsheet cost profiling
- implementation roadmap
- process map generation
- code/script scaffold generation

## Test coverage

The worker is deterministic and runs locally without credentials. It follows the blueprint library standards for manifests, config, catalog metadata, run-store artifacts, and product README sections.

## Limitations

- Vendor scoring depends on the quality of supplied scores and responses.
- The default missing-answer detection is rule based.
- Pricing analysis is a first-pass profile, not a complete TCO model.
- Recommendations require human procurement, legal, security, and business review.

## Next steps

- Add adapters for RFP portals, spreadsheets, security questionnaires, and procurement systems.
- Add approval gates for finalist selection.
- Expand TCO and lock-in modeling.
- Connect outputs to implementation-planning, contract-review, and steering-committee workflows.
