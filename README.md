# MirrorNeuron Blueprints

`mn-blueprints` is a self-contained runnable MirrorNeuron workflow blueprint catalog. Each blueprint folder includes
its own manifest, configuration, payloads, README, and user-facing `SPEC.md`.

## Quick Start

List available blueprints:

```bash
mn blueprint list
```

Run a catalog blueprint:

```bash
mn run <blueprint_id>
```

Run a checked-in folder directly:

```bash
cd <blueprint_id>
mn run --folder .
```

Run repository tests:

```bash
python3 -m pytest -q
```

## Catalog

| Blueprint | Category | Purpose |
| --- | --- | --- |
| [`adaptive_experiment_planning`](adaptive_experiment_planning/README.md) | Science | Use this blueprint to choose the next experiment from prior yield, toxicity, cost, and confidence signals before spending lab capacity. |
| [`ai_audit_readiness`](ai_audit_readiness/README.md) | Security | Use this blueprint to turn AI and cyber control requirements into an evidence-backed readiness pack your team can review before audit or launch. |
| [`ai_strategy_planning`](ai_strategy_planning/README.md) | Business | Use this blueprint to turn messy discovery notes into a board-ready AI strategy recommendation with priorities, risks, and next steps. |
| [`claim_risk_triage`](claim_risk_triage/README.md) | Finance | Use this blueprint to prioritize claim reviews by combining fraud signals, queue pressure, and adjuster capacity into an auditable triage recommendation. |
| [`climate_resilience_planning_simulation`](climate_resilience_planning_simulation/README.md) | Science | Use this blueprint to compare local flood mitigation plans as rainfall, water levels, pump capacity, and vulnerable assets change. |
| [`closed_loop_agent_runtime`](closed_loop_agent_runtime/README.md) | Engineering | Use this blueprint to understand how a closed-loop agent observes changing work, decides on each tick, and leaves an inspectable action trail. |
| [`cluster_reliability_simulation`](cluster_reliability_simulation/README.md) | Engineering | Use this blueprint to test and demo advanced cluster reliability management with Nomad-inspired scheduling, lifecycle, recovery, drain, and service-discovery controls. |
| [`codebase_memory_compression_analysis`](codebase_memory_compression_analysis/README.md) | Engineering | Use this blueprint to see how compressed agent memory helps teams analyze large codebases without flooding every worker with full repository context. |
| [`context_memory_audit`](context_memory_audit/README.md) | Engineering | Use this blueprint to audit how role-specific context packets move through a multi-agent decision process and affect the final recommendation. |
| [`context_memory_compression`](context_memory_compression/README.md) | Engineering | Use this blueprint to test whether compressed working memory keeps a growing LLM workflow useful while reducing context load and cost. |
| [`contract_negotiation_simulation`](contract_negotiation_simulation/README.md) | Engineering | Use this blueprint to model buyer-supplier negotiation rounds and compare offers as demand, price, and capacity change. |
| [`credit_default_warning`](credit_default_warning/README.md) | Finance | Use this blueprint to spot borrower default pressure early and compare policy responses before credit risk turns into losses. |
| [`customer_lifecycle_email_auto`](customer_lifecycle_email_auto/README.md) | Business | Use this blueprint to plan, generate, check, send, and track lifecycle emails so customer outreach stays timely, governed, and tied to customer state. |
| [`drug_discovery_simulation`](drug_discovery_simulation/README.md) | Science | Use this blueprint to run a multi-stage drug discovery loop that generates, filters, and evaluates candidates with reviewable evidence. |
| [`ecosystem_simulation`](ecosystem_simulation/README.md) | Science | Use this blueprint to explore ecosystem interventions across regions and compare population effects before making policy or field decisions. |
| [`environment_control_simulation`](environment_control_simulation/README.md) | Engineering | Use this blueprint to experiment with control decisions in a changing environment where load, temperature, reserve, and service levels interact. |
| [`event_stream_triage`](event_stream_triage/README.md) | Engineering | Use this blueprint to triage noisy event streams and see how anomaly pressure, queue depth, and false positives change decisions over time. |
| [`facility_safety_video_monitor`](facility_safety_video_monitor/README.md) | Security | Use this blueprint to watch an approved camera stream, detect visible people, summarize what is observable, and raise safety alerts with a reviewable event trail. |
| [`human_approval_gate`](human_approval_gate/README.md) | Security | Use this blueprint to add a human approval checkpoint before an agent applies high-impact actions, with clear review and audit records. |
| [`human_review_workflow`](human_review_workflow/README.md) | Security | Use this blueprint to run a complete human review loop where requests, decisions, revisions, and applied actions are all captured. |
| [`liquidity_risk_monitor`](liquidity_risk_monitor/README.md) | Finance | Use this blueprint to monitor market microstructure signals and understand emerging liquidity risk before trades become expensive or fragile. |
| [`live_telemetry_monitor`](live_telemetry_monitor/README.md) | Engineering | Use this blueprint to process live telemetry chunks, detect changing signal patterns, and summarize what operators need to notice. |
| [`llm_tool_orchestration`](llm_tool_orchestration/README.md) | Engineering | Use this blueprint to see an LLM agent call a forecast tool, weigh the result, and choose a resource action you can inspect. |
| [`message_routing_trace`](message_routing_trace/README.md) | Engineering | Use this blueprint to trace how messages move through router and aggregator agents so workflow wiring is easier to debug and explain. |
| [`motion_planning_simulation`](motion_planning_simulation/README.md) | Science | Use this blueprint to visualize shared-world motion planning so you can inspect coordination, conflicts, and route choices between agents. |
| [`native_live_monitor_service`](native_live_monitor_service/README.md) | Engineering | Use this blueprint to run a lightweight native monitor that keeps producing decisions over live state until you stop it. |
| [`network_threat_monitor`](network_threat_monitor/README.md) | security | This generated blueprint monitors network events, scores suspicious spamware/malware/hack behavior, and writes a dry-run alarm artifact for human review. |
| [`openshell_sandbox_worker_pipeline`](openshell_sandbox_worker_pipeline/README.md) | Engineering | Use this blueprint to run shell and Python workers inside isolated execution boundaries while keeping each step traceable. |
| [`outbreak_response_simulation`](outbreak_response_simulation/README.md) | Science | Use this blueprint to compare outbreak response policies as infections, mobility, vaccination, and hospital load evolve. |
| [`parallel_worker_benchmark`](parallel_worker_benchmark/README.md) | Engineering | Use this blueprint to stress-test broad parallel fan-out and measure how deterministic workers behave as runtime scale increases. |
| [`policy_feedback_optimization_simulation`](policy_feedback_optimization_simulation/README.md) | Engineering | Use this blueprint to tune policy thresholds through repeated feedback so you can compare rewards, incidents, and tradeoffs before deployment. |
| [`portfolio_crash_stress_simulation`](portfolio_crash_stress_simulation/README.md) | Finance | Use this blueprint to stress a portfolio against crash, rate, and liquidity shocks and review rebalancing choices before taking action. |
| [`pricing_profit_simulation`](pricing_profit_simulation/README.md) | Business | Use this blueprint to compare pricing moves against demand, inventory, margin, and competitors before you change prices in the real world. |
| [`python_sdk_research_pipeline`](python_sdk_research_pipeline/README.md) | Engineering | Use this blueprint to author a MirrorNeuron workflow directly in Python and compile it into a runnable blueprint bundle. |
| [`python_sdk_research_service`](python_sdk_research_service/README.md) | Engineering | Use this blueprint to run a Python-defined workflow as a long-lived research service with repeated stateful turns. |
| [`revenue_retention_simulation`](revenue_retention_simulation/README.md) | Business | Use this blueprint to compare retention offers for at-risk customers and choose interventions with clear revenue, churn, and customer-experience tradeoffs. |
| [`sandboxed_codegen_review`](sandboxed_codegen_review/README.md) | Security | Use this blueprint to generate, review, and validate code inside a sandboxed LLM loop before trusting the result. |
| [`service_capacity_simulation`](service_capacity_simulation/README.md) | Business | Use this blueprint to test staffing, deflection, and escalation decisions before service queues miss SLA targets. |
| [`state_audit_simulation`](state_audit_simulation/README.md) | Engineering | Use this blueprint to record simulation state changes so every agent decision can be inspected after the run. |
| [`stream_backpressure_simulation`](stream_backpressure_simulation/README.md) | Engineering | Use this blueprint to observe bounded queues, slow workers, and retry-later behavior before building live stream workflows. |
| [`supply_chain_resilience_simulation`](supply_chain_resilience_simulation/README.md) | Business | Use this blueprint to rehearse supplier disruption responses and choose actions that protect inventory, fulfillment, and customer service levels. |
| [`traffic_control_simulation`](traffic_control_simulation/README.md) | Science | Use this blueprint to test traffic signal and rerouting controls against speed, incident, volume, and emissions tradeoffs. |
| [`user_activity_rmf_triage`](user_activity_rmf_triage/README.md) | general | A local security worker that watches user activity, detects suspicious behavior, asks risky sessions to re-authenticate, and writes RMF/ATO/cATO-ready evidence artifacts. |
| [`vendor_selection_decision`](vendor_selection_decision/README.md) | Business | Use this blueprint to convert requirements and vendor responses into a scored recommendation, implementation plan, and reviewable decision record. |
| [`zip_code_property_memory_ranking`](zip_code_property_memory_ranking/README.md) | Finance | Use this blueprint to rank property opportunities while preserving useful deal memory across noisy ZIP-code history, broker flow, financing constraints, and past outcomes. |
| [`zip_code_property_ranking`](zip_code_property_ranking/README.md) | Finance | Use this blueprint to rank property acquisition opportunities by ZIP-code demand, price, cap-rate, and risk signals before committing diligence time. |

## Folder Contract

Most blueprint folders contain:

| Path | Purpose |
| --- | --- |
| `README.md` | Self-contained quickstart, inspection notes, and validation guidance. |
| `SPEC.md` | User-facing problem, outcome, evaluation criteria, limits, and upgrade path. |
| `TERM.md` | Terms, assumptions, or domain notes when present. |
| `manifest.json` | Runtime graph, entrypoints, metadata, runners, services, and environment access. |
| `config/default.json` | Default launch configuration and mock/sample inputs. |
| `config/overwrite.json` | Optional local overrides. Do not commit customer secrets. |
| `payloads/` | Worker code, prompts, policies, fixtures, and support files. |

## Safety Checklist

- Review `manifest.json`, `payloads/`, and `pass_env` before live runs.
- Start with mock, dry-run, or quick-test settings before enabling real external services.
- Keep customer-specific inputs and secrets in local overrides or environment variables.
- Update the local blueprint README and `SPEC.md` when behavior, inputs, outputs, or limits change.
