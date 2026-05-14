# MirrorNeuron Blueprint Library

Runnable workflow blueprints for MirrorNeuron.

Each blueprint is a deployable workflow folder with a manifest, configuration, payloads, tests, documentation, and a customer-facing `SPEC.md`. Blueprints can run with mock inputs first, then be adapted to real data sources and operational systems. The `SPEC.md` files describe the intended real-world customer problem and expected outcome even when the prototype implementation is still partial.

In this architecture, agents are the working units. A blueprint describes how agents work together: which agent starts, what messages flow between agents, what state and artifacts are produced, and which execution boundaries apply. MirrorNeuron is the runtime system that runs that workflow in an orchestrated way, with scheduling, message routing, run-state tracking, artifact capture, and resource controls.

Shared entries in `mn-agents` are generic agent templates. A blueprint actualizes those templates into customized workflow agents with `uses`, `with`, and `config`, then assembles them like reusable blocks. Control templates coordinate lifecycle, routing, retry, joins, filters, checkpoints, approval, and output fanout. Data templates do the work: Python execution, native modules, LLM decisions/tools, observation, sandboxed code work, edge model inference, and data services. Not every agent should call an LLM. Agents that do call LLMs should reference named LLM config, and agents that generate, review, browse, or execute code should run inside an explicit sandbox. The blueprint should make those choices visible so the same workflow can be tested locally and run reliably on constrained or edge environments.

## Categories

Use these prefixes for new blueprints:

| Prefix | Naming family | Use for |
| --- | --- | --- |
| `general_` | General | Runtime patterns, reusable workflow capabilities, and developer examples. |
| `business_` | Business | Operations, revenue, service, supply chain, safety, and workflow decisions. |
| `finance_` | Finance | Market, portfolio, credit, claims, property, and investment workflows. |
| `science_` | Science | Public health, traffic, climate, lab, ecosystem, and research simulations. |

New finance blueprints should use `finance_`, not `financial_`. Historical aliases remain only for migration.

Category filtering uses the `category` value in `index.json`; `category.json` lists the canonical display names and slugs exposed to clients.

Current filter categories:

| Name | Slug |
| --- | --- |
| Finance | `finance` |
| Business | `business` |
| Science | `science` |
| Security | `security` |
| Engineering | `engineering` |

Example local catalog filter:

```bash
jq -r '.[] | select((.category | ascii_downcase) == "finance") | .id' index.json
```

## Blueprint Catalog

| Blueprint | Spec | Category | Summary |
| --- | --- | --- | --- |
| [`business_context_memory_compression_code_analsysis`](business_context_memory_compression_code_analsysis/README.md) | [SPEC](business_context_memory_compression_code_analsysis/SPEC.md) | Engineering | Large-repo code analysis memory benchmark with bounded context packets. |
| [`business_customer_lifecycle_email_copilot`](business_customer_lifecycle_email_copilot/README.md) | [SPEC](business_customer_lifecycle_email_copilot/SPEC.md) | Business | Lifecycle email workflow with campaign, delivery, reply, and policy state. |
| [`business_dynamic_pricing_profit_optimizer`](business_dynamic_pricing_profit_optimizer/README.md) | [SPEC](business_dynamic_pricing_profit_optimizer/SPEC.md) | Business | Pricing workflow with demand, competitor price, inventory, and revenue state. |
| [`business_facility_safety_video_guardian`](business_facility_safety_video_guardian/README.md) | [SPEC](business_facility_safety_video_guardian/SPEC.md) | Security | Video sampling workflow with alert state and escalation decisions. |
| [`business_revenue_retention_copilot`](business_revenue_retention_copilot/README.md) | [SPEC](business_revenue_retention_copilot/SPEC.md) | Business | Customer health and churn-risk workflow with intervention planning. |
| [`business_service_capacity_command_center`](business_service_capacity_command_center/README.md) | [SPEC](business_service_capacity_command_center/SPEC.md) | Business | Queue, staffing, and SLA workflow for service-capacity decisions. |
| [`business_supply_chain_resilience_war_room`](business_supply_chain_resilience_war_room/README.md) | [SPEC](business_supply_chain_resilience_war_room/SPEC.md) | Business | Inventory, demand, and supplier-delay workflow with mitigation planning. |
| [`business_ai_strategy_workbench`](business_ai_strategy_workbench/README.md) | [SPEC](business_ai_strategy_workbench/SPEC.md) | Business | Enterprise discovery workflow that produces board-ready recommendation artifacts. |
| [`business_ai_control_room`](business_ai_control_room/README.md) | [SPEC](business_ai_control_room/SPEC.md) | Security | AI, cyber, and control readiness workflow with evidence mapping and remediation planning. |
| [`business_vendor_decision_agent`](business_vendor_decision_agent/README.md) | [SPEC](business_vendor_decision_agent/SPEC.md) | Business | Vendor comparison, RFP, scoring, roadmap, and negotiation workflow. |
| [`finance_claim_risk_triage_copilot`](finance_claim_risk_triage_copilot/README.md) | [SPEC](finance_claim_risk_triage_copilot/SPEC.md) | Finance | Claim queue and fraud-signal workflow with triage recommendations. |
| [`finance_credit_default_early_warning_system`](finance_credit_default_early_warning_system/README.md) | [SPEC](finance_credit_default_early_warning_system/SPEC.md) | Finance | Borrower default and credit-policy workflow. |
| [`finance_liquidity_microstructure_radar`](finance_liquidity_microstructure_radar/README.md) | [SPEC](finance_liquidity_microstructure_radar/SPEC.md) | Finance | Market stream workflow with signals, explanations, advice events, and optional Slack alerts. |
| [`finance_portfolio_crash_stress_lab`](finance_portfolio_crash_stress_lab/README.md) | [SPEC](finance_portfolio_crash_stress_lab/SPEC.md) | Finance | Macro shock and portfolio-risk workflow with rebalance recommendations. |
| [`finance_zip_code_property_alpha_engine`](finance_zip_code_property_alpha_engine/README.md) | [SPEC](finance_zip_code_property_alpha_engine/SPEC.md) | Finance | ZIP-code property-market workflow with ranked opportunities. |
| [`finance_zip_code_property_alpha_engine_with_memory`](finance_zip_code_property_alpha_engine_with_memory/README.md) | [SPEC](finance_zip_code_property_alpha_engine_with_memory/SPEC.md) | Finance | Large-context property acquisition workflow with working memory and decision-quality benchmarks. |
| [`general_closed_loop_agent_runtime`](general_closed_loop_agent_runtime/README.md) | [SPEC](general_closed_loop_agent_runtime/SPEC.md) | Engineering | Time-stepped operations queue workflow. |
| [`general_context_memory_audit_pipeline`](general_context_memory_audit_pipeline/README.md) | [SPEC](general_context_memory_audit_pipeline/SPEC.md) | Engineering | Multi-agent context handoff workflow with scoped memory and audit output. |
| [`general_context_memory_compression_lab`](general_context_memory_compression_lab/README.md) | [SPEC](general_context_memory_compression_lab/SPEC.md) | Engineering | Memory compression workflow for bounded prompt budgets. |
| [`general_dynamic_environment_control_loop`](general_dynamic_environment_control_loop/README.md) | [SPEC](general_dynamic_environment_control_loop/SPEC.md) | Engineering | Control-loop workflow over changing metrics and actions. |
| [`general_event_stream_triage_state_machine`](general_event_stream_triage_state_machine/README.md) | [SPEC](general_event_stream_triage_state_machine/SPEC.md) | Engineering | Stateful event stream triage workflow. |
| [`general_human_approval_decision_gate`](general_human_approval_decision_gate/README.md) | [SPEC](general_human_approval_decision_gate/SPEC.md) | Security | Approval-gated decision workflow. |
| [`general_live_telemetry_stream_pipeline`](general_live_telemetry_stream_pipeline/README.md) | [SPEC](general_live_telemetry_stream_pipeline/SPEC.md) | Engineering | Live telemetry stream workflow. |
| [`general_llm_tool_orchestration_loop`](general_llm_tool_orchestration_loop/README.md) | [SPEC](general_llm_tool_orchestration_loop/SPEC.md) | Engineering | Tool-informed planning workflow. |
| [`general_message_routing_trace`](general_message_routing_trace/README.md) | [SPEC](general_message_routing_trace/SPEC.md) | Engineering | Deterministic message-flow trace for the runtime message model. |
| [`general_multi_agent_contract_negotiation_loop`](general_multi_agent_contract_negotiation_loop/README.md) | [SPEC](general_multi_agent_contract_negotiation_loop/SPEC.md) | Engineering | Multi-agent negotiation state workflow. |
| [`general_native_live_monitor_daemon`](general_native_live_monitor_daemon/README.md) | [SPEC](general_native_live_monitor_daemon/SPEC.md) | Engineering | Native BEAM live monitor workflow. |
| [`general_openshell_sandbox_worker_pipeline`](general_openshell_sandbox_worker_pipeline/README.md) | [SPEC](general_openshell_sandbox_worker_pipeline/SPEC.md) | Engineering | Sandboxed worker execution and artifact handoff workflow. |
| [`general_parallel_worker_scale_benchmark`](general_parallel_worker_scale_benchmark/README.md) | [SPEC](general_parallel_worker_scale_benchmark/SPEC.md) | Engineering | Parallel synthetic workload benchmark. |
| [`general_policy_feedback_optimization_loop`](general_policy_feedback_optimization_loop/README.md) | [SPEC](general_policy_feedback_optimization_loop/SPEC.md) | Engineering | Policy adjustment workflow with feedback over time. |
| [`general_python_sdk_live_research_daemon`](general_python_sdk_live_research_daemon/README.md) | [SPEC](general_python_sdk_live_research_daemon/SPEC.md) | Engineering | Long-running Python SDK research workflow. |
| [`general_python_sdk_research_pipeline`](general_python_sdk_research_pipeline/README.md) | [SPEC](general_python_sdk_research_pipeline/SPEC.md) | Engineering | Python-defined staged research workflow. |
| [`general_sandboxed_llm_codegen_review_loop`](general_sandboxed_llm_codegen_review_loop/README.md) | [SPEC](general_sandboxed_llm_codegen_review_loop/SPEC.md) | Security | Sandboxed code generation, review, and validation workflow. |
| [`general_simulation_state_audit_trail`](general_simulation_state_audit_trail/README.md) | [SPEC](general_simulation_state_audit_trail/SPEC.md) | Engineering | State tracking workflow with inspectable transitions. |
| [`general_stream_backpressure_control_loop`](general_stream_backpressure_control_loop/README.md) | [SPEC](general_stream_backpressure_control_loop/SPEC.md) | Engineering | Live stream workflow with bounded queues and backpressure behavior. |
| [`science_adaptive_experiment_discovery_agent`](science_adaptive_experiment_discovery_agent/README.md) | [SPEC](science_adaptive_experiment_discovery_agent/SPEC.md) | Science | Iterative experiment selection workflow. |
| [`science_climate_resilience_planning_engine`](science_climate_resilience_planning_engine/README.md) | [SPEC](science_climate_resilience_planning_engine/SPEC.md) | Science | Weather, flooding, and infrastructure-risk workflow. |
| [`science_drug_discovery_closed_loop_lab`](science_drug_discovery_closed_loop_lab/README.md) | [SPEC](science_drug_discovery_closed_loop_lab/SPEC.md) | Science | Long-running staged discovery workflow. |
| [`science_ecosystem_intervention_sandbox`](science_ecosystem_intervention_sandbox/README.md) | [SPEC](science_ecosystem_intervention_sandbox/SPEC.md) | Science | Multi-region population dynamics workflow. |
| [`science_multi_agent_motion_planning_lab`](science_multi_agent_motion_planning_lab/README.md) | [SPEC](science_multi_agent_motion_planning_lab/SPEC.md) | Science | Multi-agent particle simulation and visualization workflow. |
| [`science_outbreak_response_policy_simulator`](science_outbreak_response_policy_simulator/README.md) | [SPEC](science_outbreak_response_policy_simulator/SPEC.md) | Science | Disease spread and intervention workflow. |
| [`science_urban_traffic_control_lab`](science_urban_traffic_control_lab/README.md) | [SPEC](science_urban_traffic_control_lab/SPEC.md) | Science | Traffic network and incident-control workflow. |
| [`secuirty_rmf_user_activity`](secuirty_rmf_user_activity/README.md) | [SPEC](secuirty_rmf_user_activity/SPEC.md) | Security | User activity stream triage workflow with RMF evidence artifacts and safe response recommendations. |

## Prerequisites

- Python 3.11 or newer.
- MirrorNeuron CLI installed as `mn`.
- Runtime dependencies required by the selected blueprint.
- Optional provider credentials for blueprints that call LLM, Slack, email, web, or other external services.

## Running a Blueprint

Run a catalog blueprint through the CLI:

```bash
mn blueprint run general_message_routing_trace
mn blueprint monitor --follow
```

Run a local blueprint folder:

```bash
mn blueprint run ./general_message_routing_trace
```

Run a shared simulation blueprint directly from its folder:

```bash
cd business_supply_chain_resilience_war_room
python3 payloads/simulation_loop/scripts/run_blueprint.py --mock-llm --steps 3
```

Use a fixed run ID and isolated run store when comparing scenarios:

```bash
python3 payloads/simulation_loop/scripts/run_blueprint.py \
  --mock-llm \
  --run-id supply-chain-review-001 \
  --runs-root /tmp/mirror-neuron-runs \
  --steps 3
```

Run with a local Ollama-compatible endpoint:

```bash
MN_LLM_API_BASE=http://localhost:11434 \
MN_LLM_MODEL=ollama/nemotron3:33b \
python3 payloads/simulation_loop/scripts/run_blueprint.py --steps 3
```

## Output and Run Artifacts

Blueprint runs typically write artifacts under:

```text
~/.mn/runs/<run_id>/
```

Common files:

| File | Purpose |
| --- | --- |
| `run.json` | Run identity and status. |
| `config.json` | Effective configuration. |
| `inputs.json` | Input payload used for the run. |
| `events.jsonl` | Event stream. |
| `result.json` | Machine-readable result. |
| `final_artifact.json` | Final workflow artifact. |
| `job.json` | Runtime job correlation when submitted through the CLI. |
| `web_ui.json` | Local UI or report metadata when available. |

Useful observability commands:

```bash
mn blueprint monitor --follow
mn blueprint tail <run_id>
mn blueprint compare <run_a> <run_b>
mn blueprint export <run_id> --format markdown
mn blueprint export <run_id> --format html
```

## Project Structure

Most blueprint folders contain:

| Path | Purpose |
| --- | --- |
| `manifest.json` | Graph topology, metadata, entrypoints, workers, and output contracts. |
| `config/default.json` | Default inputs, simulation settings, LLM settings, output adapters, and logging config. |
| `config/overwrite.json` | Local customer-specific overwrite values layered on top of `config/default.json` before launch. |
| `scenario.json` | Data-driven simulation metadata, when applicable. |
| `payloads/` | Worker scripts, generated runners, policies, fixtures, and domain assets. |
| `README.md` | Blueprint-specific usage notes and developer/evaluator quickstart. |
| `SPEC.md` | Customer-facing problem statement, outcome definition, evaluation criteria, prototype limits, and upgrade path. |
| `tests/` | Smoke tests or package-specific tests. |

The root `index.json` is the catalog source of truth.

## Agent Workflow Model

Blueprint manifests should treat each node as an actualized agent with a clear job and communication contract. Shared `mn-agents` templates provide generic building blocks; the blueprint gives them concrete roles, configs, message types, and domain payloads. The graph should explain:

- what starts the workflow;
- which message types move between agents;
- which agents are deterministic and which may call an LLM;
- which agents need a sandbox, custom image, service port, or external capability;
- what artifacts and events are expected from each stage;
- how the runtime should remain efficient under local, cloud, or edge constraints.

MirrorNeuron owns execution concerns such as scheduling, retries, pools, event recording, run storage, and resource isolation. Blueprints own the workflow shape and domain intent. Shared templates in `mn-agents` provide reusable agent contracts so those workflows stay consistent and testable.

## Customization

When adapting a blueprint:

1. Replace synthetic inputs with a real adapter while preserving the expected input shape.
2. Tune simulation parameters and action effects using real data or domain review.
3. Update allowed actions, prompts, and final artifact schemas.
4. Add approval gates for irreversible, regulated, or expensive actions.
5. Keep `blueprint_id`, `name`, `run_id`, and run-store artifacts stable for auditability.

## Testing

Run the full blueprint suite:

```bash
python3 -m pytest -q
```

Run optional Ollama smoke tests:

```bash
RUN_OLLAMA_INTEGRATION=1 \
MN_LLM_API_BASE=http://localhost:11434 \
MN_LLM_MODEL=ollama/nemotron3:33b \
python3 -m pytest tests/test_blueprint_library.py -m ollama -q
```

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Blueprint ID is not found | Run `mn blueprint update` and confirm the ID exists in `index.json`. |
| Run artifacts are missing | Check `MN_RUNS_ROOT`, `MN_NO_RUN_STORE`, and write permissions. |
| LLM calls fail | Confirm `MN_LLM_MODEL`, `MN_LLM_API_BASE`, and provider credentials. |
| Local folder run fails | Confirm the folder contains `manifest.json` or valid Python source blueprint metadata. |

## Rename Migration Notes

Historical names are preserved as aliases in the shared support library where needed. New names should use the current category prefixes and the current blueprint directory names listed above.

## Contributing

Keep blueprint folders self-contained, testable, and clear about required inputs and provider credentials. Keep each `SPEC.md` customer-facing: describe the real operational problem, expected outcome, evaluation criteria, prototype limits, and upgrade path without implying unfinished integrations are already production-ready. Put reusable helper code in `mn-skills`, not in one blueprint folder.

## License

No top-level license file is currently present in this repository. Add one before distributing blueprint assets outside the project.
