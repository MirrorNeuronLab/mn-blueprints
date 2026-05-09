# MirrorNeuron Blueprint Library

Runnable workflow blueprints for MirrorNeuron.

Each blueprint is a deployable workflow folder with a manifest, configuration, payloads, tests, and documentation. Blueprints can run with mock inputs first, then be adapted to real data sources and operational systems.

## Categories

Use these prefixes for new blueprints:

| Prefix | Category | Use for |
| --- | --- | --- |
| `general_` | General | Runtime patterns, reusable workflow capabilities, and developer examples. |
| `business_` | Business | Operations, revenue, service, supply chain, safety, and workflow decisions. |
| `finance_` | Finance | Market, portfolio, credit, claims, property, and investment workflows. |
| `science_` | Science | Public health, traffic, climate, lab, ecosystem, and research simulations. |

New finance blueprints should use `finance_`, not `financial_`. Historical aliases remain only for migration.

## Blueprint Catalog

| Blueprint | Category | Summary |
| --- | --- | --- |
| [`business_customer_lifecycle_email_copilot`](business_customer_lifecycle_email_copilot/README.md) | Business | Lifecycle email workflow with campaign, delivery, reply, and policy state. |
| [`business_dynamic_pricing_profit_optimizer`](business_dynamic_pricing_profit_optimizer/README.md) | Business | Pricing workflow with demand, competitor price, inventory, and revenue state. |
| [`business_facility_safety_video_guardian`](business_facility_safety_video_guardian/README.md) | Business | Video sampling workflow with alert state and escalation decisions. |
| [`business_revenue_retention_copilot`](business_revenue_retention_copilot/README.md) | Business | Customer health and churn-risk workflow with intervention planning. |
| [`business_service_capacity_command_center`](business_service_capacity_command_center/README.md) | Business | Queue, staffing, and SLA workflow for service-capacity decisions. |
| [`business_supply_chain_resilience_war_room`](business_supply_chain_resilience_war_room/README.md) | Business | Inventory, demand, and supplier-delay workflow with mitigation planning. |
| [`finance_claim_risk_triage_copilot`](finance_claim_risk_triage_copilot/README.md) | Finance | Claim queue and fraud-signal workflow with triage recommendations. |
| [`finance_credit_default_early_warning_system`](finance_credit_default_early_warning_system/README.md) | Finance | Borrower default and credit-policy workflow. |
| [`finance_liquidity_microstructure_radar`](finance_liquidity_microstructure_radar/README.md) | Finance | Market stream workflow with signals, explanations, advice events, and optional Slack alerts. |
| [`finance_portfolio_crash_stress_lab`](finance_portfolio_crash_stress_lab/README.md) | Finance | Macro shock and portfolio-risk workflow with rebalance recommendations. |
| [`finance_zip_code_property_alpha_engine`](finance_zip_code_property_alpha_engine/README.md) | Finance | ZIP-code property-market workflow with ranked opportunities. |
| [`general_closed_loop_agent_runtime`](general_closed_loop_agent_runtime/README.md) | General | Time-stepped operations queue workflow. |
| [`general_context_memory_audit_pipeline`](general_context_memory_audit_pipeline/README.md) | General | Multi-agent context handoff workflow with scoped memory and audit output. |
| [`general_context_memory_compression_lab`](general_context_memory_compression_lab/README.md) | General | Memory compression workflow for bounded prompt budgets. |
| [`general_dynamic_environment_control_loop`](general_dynamic_environment_control_loop/README.md) | General | Control-loop workflow over changing metrics and actions. |
| [`general_event_stream_triage_state_machine`](general_event_stream_triage_state_machine/README.md) | General | Stateful event stream triage workflow. |
| [`general_human_approval_decision_gate`](general_human_approval_decision_gate/README.md) | General | Approval-gated decision workflow. |
| [`general_live_telemetry_stream_pipeline`](general_live_telemetry_stream_pipeline/README.md) | General | Live telemetry stream workflow. |
| [`general_llm_tool_orchestration_loop`](general_llm_tool_orchestration_loop/README.md) | General | Tool-informed planning workflow. |
| [`general_message_routing_trace`](general_message_routing_trace/README.md) | General | Deterministic message-flow trace for the runtime message model. |
| [`general_multi_agent_contract_negotiation_loop`](general_multi_agent_contract_negotiation_loop/README.md) | General | Multi-agent negotiation state workflow. |
| [`general_native_live_monitor_daemon`](general_native_live_monitor_daemon/README.md) | General | Native BEAM live monitor workflow. |
| [`general_openshell_sandbox_worker_pipeline`](general_openshell_sandbox_worker_pipeline/README.md) | General | Sandboxed worker execution and artifact handoff workflow. |
| [`general_parallel_worker_scale_benchmark`](general_parallel_worker_scale_benchmark/README.md) | General | Parallel synthetic workload benchmark. |
| [`general_policy_feedback_optimization_loop`](general_policy_feedback_optimization_loop/README.md) | General | Policy adjustment workflow with feedback over time. |
| [`general_python_sdk_live_research_daemon`](general_python_sdk_live_research_daemon/README.md) | General | Long-running Python SDK research workflow. |
| [`general_python_sdk_research_pipeline`](general_python_sdk_research_pipeline/README.md) | General | Python-defined staged research workflow. |
| [`general_sandboxed_llm_codegen_review_loop`](general_sandboxed_llm_codegen_review_loop/README.md) | General | Sandboxed code generation, review, and validation workflow. |
| [`general_simulation_state_audit_trail`](general_simulation_state_audit_trail/README.md) | General | State tracking workflow with inspectable transitions. |
| [`general_stream_backpressure_control_loop`](general_stream_backpressure_control_loop/README.md) | General | Live stream workflow with bounded queues and backpressure behavior. |
| [`science_adaptive_experiment_discovery_agent`](science_adaptive_experiment_discovery_agent/README.md) | Science | Iterative experiment selection workflow. |
| [`science_climate_resilience_planning_engine`](science_climate_resilience_planning_engine/README.md) | Science | Weather, flooding, and infrastructure-risk workflow. |
| [`science_drug_discovery_closed_loop_lab`](science_drug_discovery_closed_loop_lab/README.md) | Science | Long-running staged discovery workflow. |
| [`science_ecosystem_intervention_sandbox`](science_ecosystem_intervention_sandbox/README.md) | Science | Multi-region population dynamics workflow. |
| [`science_multi_agent_motion_planning_lab`](science_multi_agent_motion_planning_lab/README.md) | Science | Multi-agent particle simulation and visualization workflow. |
| [`science_outbreak_response_policy_simulator`](science_outbreak_response_policy_simulator/README.md) | Science | Disease spread and intervention workflow. |
| [`science_urban_traffic_control_lab`](science_urban_traffic_control_lab/README.md) | Science | Traffic network and incident-control workflow. |

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
| `scenario.json` | Data-driven simulation metadata, when applicable. |
| `payloads/` | Worker scripts, generated runners, policies, fixtures, and domain assets. |
| `README.md` | Blueprint-specific usage notes. |
| `tests/` | Smoke tests or package-specific tests. |

The root `index.json` is the catalog source of truth.

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

Keep blueprint folders self-contained, testable, and clear about required inputs and provider credentials. Put reusable helper code in `mn-skills`, not in one blueprint folder.

## License

No top-level license file is currently present in this repository. Add one before distributing blueprint assets outside the project.
