# MirrorNeuron Blueprint Library

Runnable workflow blueprints for MirrorNeuron.

Each blueprint is a deployable workflow folder with a manifest, configuration, payloads, tests, documentation, and a customer-facing `SPEC.md`. Blueprints can run with mock inputs first, then be adapted to real data sources and operational systems. The `SPEC.md` files describe the intended real-world customer problem and expected outcome even when the prototype implementation is still partial.

In this architecture, agents are the working units. A blueprint describes how agents work together: which agent starts, what messages flow between agents, what state and artifacts are produced, and which execution boundaries apply. MirrorNeuron is the runtime system that runs that workflow in an orchestrated way, with scheduling, message routing, run-state tracking, artifact capture, and resource controls.

Shared entries in `mn-agents` are generic agent templates. A blueprint actualizes those templates into customized workflow agents with `uses`, `with`, and `config`, then assembles them like reusable blocks. Control templates coordinate lifecycle, routing, retry, joins, filters, checkpoints, approval, and output fanout. Data templates do the work: Python execution, native modules, LLM decisions/tools, observation, sandboxed code work, edge model inference, and data services. Not every agent should call an LLM. Agents that do call LLMs should reference named LLM config, and agents that generate, review, browse, or execute code should run inside an explicit sandbox. The blueprint should make those choices visible so the same workflow can be tested locally and run reliably on constrained or edge environments.

## Categories

Use descriptive blueprint IDs that tell end users what the workflow does. Do not prefix IDs with the category; category filtering comes from metadata and `index.json`.

| Category | Use for |
| --- | --- |
| General | Runtime patterns, reusable workflow capabilities, and developer examples. |
| Business | Operations, revenue, service, supply chain, safety, and workflow decisions. |
| Finance | Market, portfolio, credit, claims, property, and investment workflows. |
| Science | Public health, traffic, climate, lab, ecosystem, and research simulations. |

Simulation-oriented blueprint IDs should end with `_simulation`; document or email automation blueprint IDs should end with `_auto`.

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
| [`codebase_memory_compression_analysis`](codebase_memory_compression_analysis/README.md) | [SPEC](codebase_memory_compression_analysis/SPEC.md) | Engineering | Large-repo code analysis memory benchmark with bounded context packets. |
| [`customer_lifecycle_email_auto`](customer_lifecycle_email_auto/README.md) | [SPEC](customer_lifecycle_email_auto/SPEC.md) | Business | Lifecycle email workflow with campaign, delivery, reply, and policy state. |
| [`pricing_profit_simulation`](pricing_profit_simulation/README.md) | [SPEC](pricing_profit_simulation/SPEC.md) | Business | Pricing workflow with demand, competitor price, inventory, and revenue state. |
| [`facility_safety_video_monitor`](facility_safety_video_monitor/README.md) | [SPEC](facility_safety_video_monitor/SPEC.md) | Security | Video sampling workflow with alert state and escalation decisions. |
| [`revenue_retention_simulation`](revenue_retention_simulation/README.md) | [SPEC](revenue_retention_simulation/SPEC.md) | Business | Customer health and churn-risk workflow with intervention planning. |
| [`service_capacity_simulation`](service_capacity_simulation/README.md) | [SPEC](service_capacity_simulation/SPEC.md) | Business | Queue, staffing, and SLA workflow for service-capacity decisions. |
| [`supply_chain_resilience_simulation`](supply_chain_resilience_simulation/README.md) | [SPEC](supply_chain_resilience_simulation/SPEC.md) | Business | Inventory, demand, and supplier-delay workflow with mitigation planning. |
| [`ai_strategy_planning`](ai_strategy_planning/README.md) | [SPEC](ai_strategy_planning/SPEC.md) | Business | Enterprise discovery workflow that produces board-ready recommendation artifacts. |
| [`ai_audit_readiness`](ai_audit_readiness/README.md) | [SPEC](ai_audit_readiness/SPEC.md) | Security | AI, cyber, and control readiness workflow with evidence mapping and remediation planning. |
| [`vendor_selection_decision`](vendor_selection_decision/README.md) | [SPEC](vendor_selection_decision/SPEC.md) | Business | Vendor comparison, RFP, scoring, roadmap, and negotiation workflow. |
| [`claim_risk_triage`](claim_risk_triage/README.md) | [SPEC](claim_risk_triage/SPEC.md) | Finance | Claim queue and fraud-signal workflow with triage recommendations. |
| [`credit_default_warning`](credit_default_warning/README.md) | [SPEC](credit_default_warning/SPEC.md) | Finance | Borrower default and credit-policy workflow. |
| [`liquidity_risk_monitor`](liquidity_risk_monitor/README.md) | [SPEC](liquidity_risk_monitor/SPEC.md) | Finance | Market stream workflow with signals, explanations, advice events, and optional Slack alerts. |
| [`portfolio_crash_stress_simulation`](portfolio_crash_stress_simulation/README.md) | [SPEC](portfolio_crash_stress_simulation/SPEC.md) | Finance | Macro shock and portfolio-risk workflow with rebalance recommendations. |
| [`zip_code_property_ranking`](zip_code_property_ranking/README.md) | [SPEC](zip_code_property_ranking/SPEC.md) | Finance | ZIP-code property-market workflow with ranked opportunities. |
| [`zip_code_property_memory_ranking`](zip_code_property_memory_ranking/README.md) | [SPEC](zip_code_property_memory_ranking/SPEC.md) | Finance | Large-context property acquisition workflow with working memory and decision-quality benchmarks. |
| [`closed_loop_agent_runtime`](closed_loop_agent_runtime/README.md) | [SPEC](closed_loop_agent_runtime/SPEC.md) | Engineering | Time-stepped operations queue workflow. |
| [`cluster_reliability_simulation`](cluster_reliability_simulation/README.md) | [SPEC](cluster_reliability_simulation/SPEC.md) | Engineering | Combined-cluster reliability management demo for scheduling, recovery, drain, and maintenance. |
| [`context_memory_audit`](context_memory_audit/README.md) | [SPEC](context_memory_audit/SPEC.md) | Engineering | Multi-agent context handoff workflow with scoped memory and audit output. |
| [`context_memory_compression`](context_memory_compression/README.md) | [SPEC](context_memory_compression/SPEC.md) | Engineering | Memory compression workflow for bounded prompt budgets. |
| [`environment_control_simulation`](environment_control_simulation/README.md) | [SPEC](environment_control_simulation/SPEC.md) | Engineering | Control-loop workflow over changing metrics and actions. |
| [`event_stream_triage`](event_stream_triage/README.md) | [SPEC](event_stream_triage/SPEC.md) | Engineering | Stateful event stream triage workflow. |
| [`human_approval_gate`](human_approval_gate/README.md) | [SPEC](human_approval_gate/SPEC.md) | Security | Approval-gated decision workflow. |
| [`live_telemetry_monitor`](live_telemetry_monitor/README.md) | [SPEC](live_telemetry_monitor/SPEC.md) | Engineering | Live telemetry stream workflow. |
| [`llm_tool_orchestration`](llm_tool_orchestration/README.md) | [SPEC](llm_tool_orchestration/SPEC.md) | Engineering | Tool-informed planning workflow. |
| [`message_routing_trace`](message_routing_trace/README.md) | [SPEC](message_routing_trace/SPEC.md) | Engineering | Deterministic message-flow trace for the runtime message model. |
| [`contract_negotiation_simulation`](contract_negotiation_simulation/README.md) | [SPEC](contract_negotiation_simulation/SPEC.md) | Engineering | Multi-agent negotiation state workflow. |
| [`native_live_monitor_service`](native_live_monitor_service/README.md) | [SPEC](native_live_monitor_service/SPEC.md) | Engineering | Native BEAM live monitor workflow. |
| [`openshell_sandbox_worker_pipeline`](openshell_sandbox_worker_pipeline/README.md) | [SPEC](openshell_sandbox_worker_pipeline/SPEC.md) | Engineering | Sandboxed worker execution and artifact handoff workflow. |
| [`parallel_worker_benchmark`](parallel_worker_benchmark/README.md) | [SPEC](parallel_worker_benchmark/SPEC.md) | Engineering | Parallel synthetic workload benchmark. |
| [`policy_feedback_optimization_simulation`](policy_feedback_optimization_simulation/README.md) | [SPEC](policy_feedback_optimization_simulation/SPEC.md) | Engineering | Policy adjustment workflow with feedback over time. |
| [`python_sdk_research_service`](python_sdk_research_service/README.md) | [SPEC](python_sdk_research_service/SPEC.md) | Engineering | Long-running Python SDK research workflow. |
| [`python_sdk_research_pipeline`](python_sdk_research_pipeline/README.md) | [SPEC](python_sdk_research_pipeline/SPEC.md) | Engineering | Python-defined staged research workflow. |
| [`sandboxed_codegen_review`](sandboxed_codegen_review/README.md) | [SPEC](sandboxed_codegen_review/SPEC.md) | Security | Sandboxed code generation, review, and validation workflow. |
| [`state_audit_simulation`](state_audit_simulation/README.md) | [SPEC](state_audit_simulation/SPEC.md) | Engineering | State tracking workflow with inspectable transitions. |
| [`stream_backpressure_simulation`](stream_backpressure_simulation/README.md) | [SPEC](stream_backpressure_simulation/SPEC.md) | Engineering | Live stream workflow with bounded queues and backpressure behavior. |
| [`adaptive_experiment_planning`](adaptive_experiment_planning/README.md) | [SPEC](adaptive_experiment_planning/SPEC.md) | Science | Iterative experiment selection workflow. |
| [`climate_resilience_planning_simulation`](climate_resilience_planning_simulation/README.md) | [SPEC](climate_resilience_planning_simulation/SPEC.md) | Science | Weather, flooding, and infrastructure-risk workflow. |
| [`drug_discovery_simulation`](drug_discovery_simulation/README.md) | [SPEC](drug_discovery_simulation/SPEC.md) | Science | Long-running staged discovery workflow. |
| [`ecosystem_simulation`](ecosystem_simulation/README.md) | [SPEC](ecosystem_simulation/SPEC.md) | Science | Multi-region population dynamics workflow. |
| [`motion_planning_simulation`](motion_planning_simulation/README.md) | [SPEC](motion_planning_simulation/SPEC.md) | Science | Multi-agent particle simulation and visualization workflow. |
| [`outbreak_response_simulation`](outbreak_response_simulation/README.md) | [SPEC](outbreak_response_simulation/SPEC.md) | Science | Disease spread and intervention workflow. |
| [`traffic_control_simulation`](traffic_control_simulation/README.md) | [SPEC](traffic_control_simulation/SPEC.md) | Science | Traffic network and incident-control workflow. |
| [`user_activity_rmf_triage`](user_activity_rmf_triage/README.md) | [SPEC](user_activity_rmf_triage/SPEC.md) | Security | User activity stream triage workflow with RMF evidence artifacts and safe response recommendations. |

## Prerequisites

- Python 3.11 or newer.
- MirrorNeuron CLI installed as `mn`.
- Runtime dependencies required by the selected blueprint.
- Optional provider credentials for blueprints that call LLM, Slack, email, web, or other external services.

## Running a Blueprint

Run a catalog blueprint through the CLI:

```bash
mn blueprint run message_routing_trace
mn blueprint monitor --follow
```

Run a local blueprint folder:

```bash
mn blueprint run ./message_routing_trace
```

Run a shared simulation blueprint directly from its folder:

```bash
cd supply_chain_resilience_simulation
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
| `manifest.json` | Graph topology, metadata, entrypoints, workers, runtime requirements, input validation, and output contracts. |
| `config/default.json` | Default inputs, simulation settings, LLM settings, output adapters, and logging config. |
| `config/overwrite.json` | Local customer-specific overwrite values layered on top of `config/default.json` before launch. |
| `scenario.json` | Data-driven simulation metadata, when applicable. |
| `payloads/` | Worker scripts, generated runners, policies, fixtures, and domain assets. |
| `scripts/pre-launch.sh` | Optional host-side setup hook started before run validation/submission for long-lived services required by the run. |
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
