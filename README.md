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
python3.11 -m pytest -q
```

## Catalog

| Blueprint | Category | Purpose |
| --- | --- | --- |
| [`lab_experiment_planning_assistant`](lab_experiment_planning_assistant/README.md) | Science | Use this blueprint to choose the next experiment from prior yield, toxicity, cost, and confidence signals before spending lab capacity. |
| [`ai_control_readiness_assistant`](ai_control_readiness_assistant/README.md) | Security | Use this blueprint to turn AI and cyber control requirements into an evidence-backed readiness pack your team can review before audit or launch. |
| [`ai_strategy_advisory_assistant`](ai_strategy_advisory_assistant/README.md) | Business | Use this blueprint to turn messy discovery notes into a board-ready AI strategy recommendation with priorities, risks, and next steps. |
| [`insurance_claim_risk_triage_assistant`](insurance_claim_risk_triage_assistant/README.md) | Finance | Use this blueprint to prioritize claim reviews by combining fraud signals, queue pressure, and adjuster capacity into an auditable triage recommendation. |
| [`climate_resilience_planning_assistant`](climate_resilience_planning_assistant/README.md) | Science | Use this blueprint to compare local flood mitigation plans as rainfall, water levels, pump capacity, and vulnerable assets change. |
| [`demo_closed_loop_agent_runtime`](demo_closed_loop_agent_runtime/README.md) | Engineering | Use this blueprint to understand how a closed-loop agent observes changing work, decides on each tick, and leaves an inspectable action trail. |
| [`demo_cluster_reliability_service`](demo_cluster_reliability_service/README.md) | Engineering | Use this blueprint to test and demo advanced cluster reliability management with Nomad-inspired scheduling, lifecycle, recovery, drain, and service-discovery controls. |
| [`codebase_context_memory_analysis_assistant`](codebase_context_memory_analysis_assistant/README.md) | Engineering | Use this blueprint to see how compressed agent memory helps teams analyze large codebases without flooding every worker with full repository context. |
| [`demo_context_memory_audit`](demo_context_memory_audit/README.md) | Engineering | Use this blueprint to audit how role-specific context packets move through a multi-agent decision process and affect the final recommendation. |
| [`demo_context_memory_compression`](demo_context_memory_compression/README.md) | Engineering | Use this blueprint to test whether compressed working memory keeps a growing LLM workflow useful while reducing context load and cost. |
| [`contract_negotiation_rehearsal_assistant`](contract_negotiation_rehearsal_assistant/README.md) | Engineering | Use this blueprint to model buyer-supplier negotiation rounds and compare offers as demand, price, and capacity change. |
| [`credit_default_warning_assistant`](credit_default_warning_assistant/README.md) | Finance | Use this blueprint to spot borrower default pressure early and compare policy responses before credit risk turns into losses. |
| [`lifecycle_email_growth_assistant`](lifecycle_email_growth_assistant/README.md) | Business | Use this blueprint to plan, generate, check, send, and track lifecycle emails so customer outreach stays timely, governed, and tied to customer state. |
| [`drug_discovery_research_assistant`](drug_discovery_research_assistant/README.md) | Science | Use this blueprint to run a multi-stage drug discovery loop that generates, filters, and evaluates candidates with reviewable evidence. |
| [`ecosystem_intervention_planning_assistant`](ecosystem_intervention_planning_assistant/README.md) | Science | Use this blueprint to explore ecosystem interventions across regions and compare population effects before making policy or field decisions. |
| [`demo_environment_control_loop`](demo_environment_control_loop/README.md) | Engineering | Use this blueprint to experiment with control decisions in a changing environment where load, temperature, reserve, and service levels interact. |
| [`event_stream_triage_assistant`](event_stream_triage_assistant/README.md) | Engineering | Use this blueprint to triage noisy event streams and see how anomaly pressure, queue depth, and false positives change decisions over time. |
| [`facility_safety_monitor_assistant`](facility_safety_monitor_assistant/README.md) | Security | Use this blueprint to watch an approved camera stream, detect visible people, summarize what is observable, and raise safety alerts with a reviewable event trail. |
| [`demo_human_approval_gate`](demo_human_approval_gate/README.md) | Security | Use this blueprint to add a human approval checkpoint before an agent applies high-impact actions, with clear review and audit records. |
| [`demo_human_review_workflow`](demo_human_review_workflow/README.md) | Security | Use this blueprint to run a complete human review loop where requests, decisions, revisions, and applied actions are all captured. |
| [`liquidity_risk_monitoring_assistant`](liquidity_risk_monitoring_assistant/README.md) | Finance | Use this blueprint to monitor market microstructure signals and understand emerging liquidity risk before trades become expensive or fragile. |
| [`demo_live_telemetry_monitor`](demo_live_telemetry_monitor/README.md) | Engineering | Use this blueprint to process live telemetry chunks, detect changing signal patterns, and summarize what operators need to notice. |
| [`demo_llm_tool_orchestration`](demo_llm_tool_orchestration/README.md) | Engineering | Use this blueprint to see an LLM agent call a forecast tool, weigh the result, and choose a resource action you can inspect. |
| [`demo_message_routing_trace`](demo_message_routing_trace/README.md) | Engineering | Use this blueprint to trace how messages move through router and aggregator agents so workflow wiring is easier to debug and explain. |
| [`robot_motion_planning_assistant`](robot_motion_planning_assistant/README.md) | Science | Use this blueprint to visualize shared-world motion planning so you can inspect coordination, conflicts, and route choices between agents. |
| [`demo_native_live_monitor_service`](demo_native_live_monitor_service/README.md) | Engineering | Use this blueprint to run a lightweight native monitor that keeps producing decisions over live state until you stop it. |
| [`network_threat_response_assistant`](network_threat_response_assistant/README.md) | security | This generated blueprint monitors network events, scores suspicious spamware/malware/hack behavior, and writes a dry-run alarm artifact for human review. |
| [`demo_openshell_worker_pipeline`](demo_openshell_worker_pipeline/README.md) | Engineering | Use this blueprint to run shell and Python workers inside isolated execution boundaries while keeping each step traceable. |
| [`outbreak_response_planning_assistant`](outbreak_response_planning_assistant/README.md) | Science | Use this blueprint to compare outbreak response policies as infections, mobility, vaccination, and hospital load evolve. |
| [`demo_parallel_worker_benchmark`](demo_parallel_worker_benchmark/README.md) | Engineering | Use this blueprint to stress-test broad parallel fan-out and measure how deterministic workers behave as runtime scale increases. |
| [`demo_policy_feedback_optimization`](demo_policy_feedback_optimization/README.md) | Engineering | Use this blueprint to tune policy thresholds through repeated feedback so you can compare rewards, incidents, and tradeoffs before deployment. |
| [`portfolio_risk_review_assistant`](portfolio_risk_review_assistant/README.md) | Finance | Use this blueprint to stress a portfolio against crash, rate, and liquidity shocks and review rebalancing choices before taking action. |
| [`pricing_profit_optimization_assistant`](pricing_profit_optimization_assistant/README.md) | Business | Use this blueprint to compare pricing moves against demand, inventory, margin, and competitors before you change prices in the real world. |
| [`demo_python_sdk_research_pipeline`](demo_python_sdk_research_pipeline/README.md) | Engineering | Use this blueprint to author a MirrorNeuron workflow directly in Python and compile it into a runnable blueprint bundle. |
| [`demo_python_sdk_research_service`](demo_python_sdk_research_service/README.md) | Engineering | Use this blueprint to run a Python-defined workflow as a long-lived research service with repeated stateful turns. |
| [`revenue_retention_planning_assistant`](revenue_retention_planning_assistant/README.md) | Business | Use this blueprint to compare retention offers for at-risk customers and choose interventions with clear revenue, churn, and customer-experience tradeoffs. |
| [`sandboxed_codegen_review_assistant`](sandboxed_codegen_review_assistant/README.md) | Security | Use this blueprint to generate, review, and validate code inside a sandboxed LLM loop before trusting the result. |
| [`service_capacity_planning_assistant`](service_capacity_planning_assistant/README.md) | Business | Use this blueprint to test staffing, deflection, and escalation decisions before service queues miss SLA targets. |
| [`demo_state_audit_workflow`](demo_state_audit_workflow/README.md) | Engineering | Use this blueprint to record simulation state changes so every agent decision can be inspected after the run. |
| [`demo_stream_backpressure_service`](demo_stream_backpressure_service/README.md) | Engineering | Use this blueprint to observe bounded queues, slow workers, and retry-later behavior before building live stream workflows. |
| [`supply_chain_resilience_assistant`](supply_chain_resilience_assistant/README.md) | Business | Use this blueprint to rehearse supplier disruption responses and choose actions that protect inventory, fulfillment, and customer service levels. |
| [`traffic_signal_control_assistant`](traffic_signal_control_assistant/README.md) | Science | Use this blueprint to test traffic signal and rerouting controls against speed, incident, volume, and emissions tradeoffs. |
| [`user_activity_rmf_triage_assistant`](user_activity_rmf_triage_assistant/README.md) | general | A local security worker that watches user activity, detects suspicious behavior, asks risky sessions to re-authenticate, and writes RMF/ATO/cATO-ready evidence artifacts. |
| [`vendor_selection_advisor_assistant`](vendor_selection_advisor_assistant/README.md) | Business | Use this blueprint to convert requirements and vendor responses into a scored recommendation, implementation plan, and reviewable decision record. |
| [`property_deal_memory_research_assistant`](property_deal_memory_research_assistant/README.md) | Finance | Use this blueprint to rank property opportunities while preserving useful deal memory across noisy ZIP-code history, broker flow, financing constraints, and past outcomes. |
| [`property_deal_research_assistant`](property_deal_research_assistant/README.md) | Finance | Use this blueprint to rank property acquisition opportunities by ZIP-code demand, price, cap-rate, and risk signals before committing diligence time. |

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
