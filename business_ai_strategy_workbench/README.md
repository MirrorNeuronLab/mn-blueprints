# AI Strategy Workbench

`Blueprint ID:` `business_ai_strategy_workbench`  
`Category:` business - Business Solution Template  
`Default LLM:` Ollama `nemotron3:33b` metadata, deterministic local artifact generation for tests  

## One-line value proposition

Compress enterprise discovery into a board-ready strategy recommendation pack.

## What it is

This blueprint turns client documents, interview transcripts, financial snapshots, and market notes into a first-draft strategy workbench output: executive summary, issue tree, opportunity map, board-slide outline, roadmap, risk register, and evidence appendix.

It uses reusable `mn-skills` for document reading, meeting summarization, market research synthesis, spreadsheet analysis, first-draft slides, process maps, implementation plans, and client reports.

## Who this is for

Large enterprise strategy teams, CFO offices, corporate development, private-equity operating teams, and transformation offices.

## Why it matters

Discovery and synthesis consume weeks of junior-consultant effort. A static dashboard can show documents or metrics, and a one-shot LLM can summarize a packet, but neither maintains a reusable evidence trail from source material to board recommendation. This blueprint keeps the evidence, themes, roadmap, and report artifacts together.

## Why this runtime is useful here

MirrorNeuron makes the work auditable. The worker resolves configuration, loads mock or real input packets, writes run artifacts, emits events, and stores `final_artifact.json` so users can compare discovery runs and inspect how recommendations were assembled.

## How it works

1. Load a synthetic or real client-discovery packet.
2. Normalize documents and extract outlines/chunks.
3. Summarize meeting transcripts and action items.
4. Profile financial CSV inputs.
5. Synthesize market notes and benchmark claims.
6. Cluster evidence into strategic themes.
7. Generate an issue tree, opportunity map, roadmap, slide outline, process map, risk register, and client report Markdown.

## Example scenario

Northstar Industrial has revenue growth, rising SG&A, manual quote approvals, uneven ERP data quality, and fragmented operating processes. The blueprint produces a board-ready recommendation pack focused on margin, growth, operating bottlenecks, risk, and technology gaps.

## Inputs

| Input | What it controls | Example | Can customize? |
|---|---|---|---|
| `company` | Client name for report artifacts. | `Northstar Industrial` | Yes |
| `engagement_goal` | Root question for the issue tree. | `Find board-ready opportunities` | Yes |
| `documents` | Client documents with `name` and `text`. | Annual report excerpt | Yes |
| `meeting_transcripts` | Interview or workshop transcripts. | Finance and operations notes | Yes |
| `financials_csv` | KPI or financial table. | SG&A, cycle time, cloud waste | Yes |
| `market_notes` | Benchmark/source claims. | Analyst or interview notes | Yes |
| `roadmap_weeks` | Planning horizon. | `12` | Yes |

## Outputs

| Output | What it means | Where to look |
|---|---|---|
| `executive_summary` | Board-level recommendation bullets. | `final_artifact.executive_summary` |
| `issue_tree` | Theme branches and evidence examples. | `final_artifact.issue_tree` |
| `opportunity_map` | Prioritized opportunities with confidence and source refs. | `final_artifact.opportunity_map` |
| `first_draft_slide_deck` | Slide objects plus Markdown. | `final_artifact.first_draft_slide_deck` |
| `recommended_roadmap` | Implementation plan and Markdown. | `final_artifact.recommended_roadmap` |
| `evidence_appendix` | Source-linked findings. | `final_artifact.evidence_appendix` |

## How to run

```bash
cd business_ai_strategy_workbench
python3 payloads/advisory_workflow/scripts/run_blueprint.py \
  --runs-root /tmp/mirror-neuron-runs
```

Run with a real packet:

```bash
python3 payloads/advisory_workflow/scripts/run_blueprint.py \
  --input-file /path/to/discovery_packet.json \
  --runs-root /tmp/mirror-neuron-runs
```

## How to customize it

Replace the mock packet with client document exports, transcript files, financial tables, process maps, policy repositories, and market research notes. Tune the theme keywords, output schema, stakeholder language, roadmap workstreams, and risk scoring to match the engagement method your team already uses.

## What to look for in results

Check whether evidence flows cleanly from source documents into themes, opportunities, slides, and the roadmap. The strongest runs have source refs for major claims, a clear issue tree, a short opportunity map, and a roadmap that names owners and dependencies.

## Investor and evaluator narrative

This compresses the strategy-discovery layer that sits below partner judgment. The product wedge is not a generic chatbot; it is a repeatable evidence-to-recommendation workflow for consulting, PE value creation, and transformation offices.

## Runtime features demonstrated

- document ingestion
- meeting summarization
- spreadsheet profiling
- market research synthesis
- first-draft slide outlines
- implementation roadmap generation
- run-store audit artifacts

## Test coverage

The worker is deterministic and can be run locally without credentials. The blueprint conforms to the shared manifest, config, README, catalog, and run-store conventions used by the blueprint library tests.

## Limitations

- Mock data is simplified for fast local runs.
- Generated artifacts are first drafts and require expert review.
- The default theme clustering is keyword based.
- Outputs are decision-support artifacts, not professional advice.

## Next steps

- Add file adapters for PDFs, DOCX exports, and spreadsheet uploads.
- Add organization-specific benchmark libraries.
- Add human review gates for partner/steering committee approval.
- Connect final artifacts to slide-generation or document-generation workflows.
