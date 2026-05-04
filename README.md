# MirrorNeuron Blueprint Library

MirrorNeuron blueprints are deployable intelligence workflows, not static prompt examples. Each blueprint puts LLM agents inside a changing system so users can watch state evolve, inspect decisions, and review a structured final artifact.

The library is organized around the runtime thesis: `LLM agents + dynamic system simulation + decision loops over time`. Blueprints run out of the box with mock data, then give developers a clear path to real adapters, production configuration, run tracking, and workflow integration.

## Category standard

Use these prefixes for new blueprints:

| Prefix | Category | Use for |
|---|---|---|
| `general_` | General | Runtime patterns, developer workflows, reusable agent-loop capabilities. |
| `business_` | Business | Operations, revenue, service, supply chain, safety, and workflow decisions. |
| `finance_` | Finance | Market, portfolio, credit, claims, and investment decisions. |
| `science_` | Science | Public health, traffic, climate, lab, ecosystem, and research simulations. |

Current finance blueprints use the `finance_` prefix. Historical `financial_*` aliases remain documented only as migration aliases where needed, but new blueprints should use `finance_`.

## Blueprint portfolio

| Blueprint | Category | Target user | Problem solved | Simulation type | LLM agent role | Output |
|---|---|---|---|---|---|---|
| [`business_customer_lifecycle_email_copilot`](business_customer_lifecycle_email_copilot/README.md) | business | Growth, lifecycle marketing, and customer success teams. | Customer outreach changes as replies, segments, policies, and delivery state evolve; static templates miss timing, context, and governance. | Lifecycle campaign loop with inbox and delivery state. | Campaign planner, copywriter, policy checker, delivery executor, inbox responder. | Prepared emails, sent-event logs, reply handling events, and campaign summaries. |
| [`business_dynamic_pricing_profit_optimizer`](business_dynamic_pricing_profit_optimizer/README.md) | business | Pricing teams, category managers, and revenue management leaders. | Pricing is dynamic and coupled: competitors, demand, inventory, and margin move together faster than static rules can explain. | Demand, competitor price, inventory, and revenue simulation. | Pricing strategy agent. | Pricing recommendation with revenue and inventory tradeoffs. |
| [`business_facility_safety_video_guardian`](business_facility_safety_video_guardian/README.md) | business | Facilities, security, safety operations, and property management teams. | Video monitoring is continuous, noisy, and operationally sensitive; teams need stateful alerts, cooldowns, and explainable observations rather than raw frames. | Video stream sampling with alert state. | Safety observation and escalation agent. | Detection events, alert decisions, and notification payloads. |
| [`business_revenue_retention_copilot`](business_revenue_retention_copilot/README.md) | business | Revenue operations, customer success, and growth teams. | Churn risk changes with sentiment, product issues, and budget constraints; one-shot LLM suggestions do not show cost or state tradeoffs. | Customer health and churn-risk simulation. | Customer retention strategist. | Retention intervention plan with expected churn and budget tradeoffs. |
| [`business_service_capacity_command_center`](business_service_capacity_command_center/README.md) | business | Contact-center leaders, workforce managers, and customer operations teams. | Staffing decisions are expensive and time-sensitive; dashboards show queue waits but do not simulate next-interval choices. | Queue, staffing, and SLA simulation. | Workforce management agent. | Staffing forecast and capacity action plan. |
| [`business_supply_chain_resilience_war_room`](business_supply_chain_resilience_war_room/README.md) | business | Supply chain operators, procurement leaders, and operations executives. | Demand spikes and supplier delays compound over time; static dashboards show the fire but do not test mitigation paths. | Inventory, demand, and supplier-delay simulation. | Supply chain disruption response agent. | Disruption response plan with action history and supplier-lane ranking. |
| [`finance_claim_risk_triage_copilot`](finance_claim_risk_triage_copilot/README.md) | finance | Insurance claims leaders, SIU teams, adjuster operations, and insurtech builders. | Claims queues evolve continuously; teams need to balance fast settlement, fraud risk, loss ratio, and adjuster capacity. | Claim queue and fraud-signal simulation. | Insurance claim risk triage agent. | Claim triage report with prioritized segments and review actions. |
| [`finance_credit_default_early_warning_system`](finance_credit_default_early_warning_system/README.md) | finance | Credit-risk teams, lenders, fintech underwriters, and portfolio analysts. | Borrower behavior, rates, approvals, and yield interact over time; static scorecards miss policy tradeoffs under changing conditions. | Borrower default and credit policy simulation. | Credit risk decision agent. | Credit risk decision report with policy action history. |
| [`finance_liquidity_microstructure_radar`](finance_liquidity_microstructure_radar/README.md) | finance | Trading teams, market-risk analysts, and fintech product evaluators. | Markets evolve tick by tick; spreads, depth, momentum, and volatility interact faster than static dashboards or one-shot summaries can capture. | Live market stream and exchange-style signal simulation. | Signal analyzer, market explainer, advisor agent. | Market signals, risk explanations, advice events, and optional Slack alerts. |
| [`finance_portfolio_crash_stress_lab`](finance_portfolio_crash_stress_lab/README.md) | finance | Portfolio managers, wealth advisors, risk officers, and fintech evaluators. | Risk changes path-dependently during shocks; one summary cannot show how hedges, cash, and defensive moves alter the next state. | Macro shock and portfolio risk simulation. | Portfolio stress-test analyst. | Portfolio risk report and rebalance recommendation. |
| [`finance_zip_code_property_alpha_engine`](finance_zip_code_property_alpha_engine/README.md) | finance | Real-estate investors, acquisition analysts, and property-tech teams. | Property opportunities change with rates, inventory, rents, neighborhood demand, and liquidity; static comps cannot rank next-best actions. | ZIP-code property market simulation. | Real estate investment analyst. | Ranked opportunities and bid/watchlist recommendation. |
| [`general_closed_loop_agent_runtime`](general_closed_loop_agent_runtime/README.md) | general | Developers, evaluators, and technical buyers learning the closed-loop agent model. | Most LLM demos stop after one answer; real operations require repeated observations, decisions, state updates, and traceable outcomes. | Time-stepped operations queue simulation. | Operations loop controller. | Simulation summary with action history, state deltas, and next steps. |
| [`general_context_memory_audit_pipeline`](general_context_memory_audit_pipeline/README.md) | general | Developers and compliance teams evaluating context-engine governance. | Agents should not all see the same raw context; serious workflows need scoped memory, traceability, and final decisions that cite structured evidence. | Multi-agent context handoff with scoped memory. | Policy interpreter, evidence extractor, risk classifier, decision agent, critic. | Traceable audit decision and critic report. |
| [`general_context_memory_compression_lab`](general_context_memory_compression_lab/README.md) | general | Developers building long-context agent systems with bounded prompt budgets. | Long-running agents accumulate more context than a model can safely consume; compression must preserve pinned facts, constraints, and decision traces. | Growing memory graph with compression pressure. | Context researcher, expander, challenger, compressor, briefing author. | Compressed context handoff and final briefing. |
| [`general_dynamic_environment_control_loop`](general_dynamic_environment_control_loop/README.md) | general | Developers and operators testing control-loop blueprints before adding domain data. | Operational systems are coupled and time-varying; one-shot advice cannot show how a control action changes the next state. | Closed-loop control simulation. | Dynamic environment controller. | Control summary with metric trajectory and recommended action. |
| [`general_event_stream_triage_state_machine`](general_event_stream_triage_state_machine/README.md) | general | Developers building alerting, stream processing, and incident triage agents. | Event streams are noisy and bursty; teams need agents that maintain state and route actions as conditions change. | Stateful event stream simulation. | Event stream triage agent. | Event stream report with queue state, triage actions, and ranked partitions. |
| [`general_human_approval_decision_gate`](general_human_approval_decision_gate/README.md) | general | Developers and governance teams designing approval-gated agent workflows. | Enterprise agents often recommend actions that should not execute automatically; approval state must be part of the runtime loop. | Approval-gated decision simulation. | Decision support agent. | Approval memo with recommended and applied actions. |
| [`general_live_telemetry_stream_pipeline`](general_live_telemetry_stream_pipeline/README.md) | general | Developers building event-stream workflows and runtime observability paths. | Streaming systems require backpressure-aware routing, stateful workers, and outputs that remain interpretable as events arrive. | Live telemetry stream. | Stream processor and summarizer. | Signal summary and stream result artifacts. |
| [`general_llm_tool_orchestration_loop`](general_llm_tool_orchestration_loop/README.md) | general | Developers adding tools, forecasts, or deterministic calculators to agent workflows. | LLMs are more useful when they can combine reasoning with tools and then observe whether the tool-informed decision worked. | Tool-informed resource simulation. | Tool-using planning agent. | Tool-use trace and resource recommendation. |
| [`general_message_routing_trace`](general_message_routing_trace/README.md) | general | Developers learning the runtime message model. | Agent graphs are hard to debug unless developers can see message types, edges, and completion behavior clearly. | Deterministic message-flow trace. | Router and aggregator agents. | Completed route with aggregated payload. |
| [`general_multi_agent_contract_negotiation_loop`](general_multi_agent_contract_negotiation_loop/README.md) | general | Developers building multi-agent workflows and procurement teams evaluating negotiation automation. | Negotiation is dynamic: positions change as demand, capacity, and costs move, so static summaries cannot capture the next best move. | Multi-agent negotiation state simulation. | Negotiation mediator agent. | Negotiation brief with agreement score, action history, and ranked deal terms. |
| [`general_native_live_monitor_daemon`](general_native_live_monitor_daemon/README.md) | general | Runtime evaluators comparing native BEAM agents with external worker processes. | Some simulations and monitors need low-overhead native agents that can run continuously and emit structured updates. | Live native signal monitor. | Native BEAM monitoring agents. | Streaming monitor events and summaries. |
| [`general_openshell_sandbox_worker_pipeline`](general_openshell_sandbox_worker_pipeline/README.md) | general | Developers evaluating sandboxed worker execution and artifact handoff patterns. | Teams need to run untrusted or heterogeneous tasks without losing observability, output contracts, or retry behavior. | Static worker pipeline with deterministic generated input. | Sandboxed worker executor. | Worker metrics and a Python-generated report. |
| [`general_parallel_worker_scale_benchmark`](general_parallel_worker_scale_benchmark/README.md) | general | Platform teams testing scheduler throughput, worker pools, and aggregation behavior. | Agent systems need to prove they can dispatch many bounded tasks and collect results reliably before being trusted with larger workloads. | Parallel synthetic workload sweep. | Parallel executor workers plus reducer. | Scale summary and worker completion metrics. |
| [`general_policy_feedback_optimization_loop`](general_policy_feedback_optimization_loop/README.md) | general | Developers and policy owners testing adaptive decision rules. | Policies that look good once can fail over time; users need to see reward, coverage, and incidents evolve under each adjustment. | Policy feedback simulation. | Policy optimization agent. | Policy recommendation with reward trajectory and action history. |
| [`general_python_sdk_live_research_daemon`](general_python_sdk_live_research_daemon/README.md) | general | Developers building live monitors, scheduled analysis loops, or long-running research agents. | Many agent workflows need to keep running, react to new events, and maintain operational state rather than finish after one request. | Live daemon loop with repeated inputs. | Python daemon coordinator. | Ongoing events and final cancellation-safe state. |
| [`general_python_sdk_research_pipeline`](general_python_sdk_research_pipeline/README.md) | general | Python developers who want agent workflows without hand-writing manifests. | Developers need a low-friction path from Python functions to distributed runtime agents while keeping retry, timeout, and graph semantics explicit. | Deterministic staged workflow. | Python-defined research agents. | Saved research summary and final workflow result. |
| [`general_sandboxed_llm_codegen_review_loop`](general_sandboxed_llm_codegen_review_loop/README.md) | general | Engineering teams evaluating safe LLM coding workflows. | One-shot code generation is risky; production teams need review, validation, isolation, and iterative improvement before executing generated code. | Iterative code-review decision loop. | Codegen agent, review agent, validator. | Generated code, review history, and validation result. |
| [`general_simulation_state_audit_trail`](general_simulation_state_audit_trail/README.md) | general | Developers and evaluators who need inspectable state transitions. | Dynamic systems are hard to trust unless users can see what changed, why an action was chosen, and how the next state moved. | State tracking and checkpoint simulation. | State tracking analyst. | State tracking report with deltas and ranked subsystems. |
| [`general_stream_backpressure_control_loop`](general_stream_backpressure_control_loop/README.md) | general | Platform teams designing reliable live agent systems. | Real event streams overload workers; agent runtimes need visible backpressure and safe rejection semantics. | Live stream with bounded queues. | Live source, slow processor, metrics sink. | Backpressure metrics and stream processing report. |
| [`science_adaptive_experiment_discovery_agent`](science_adaptive_experiment_discovery_agent/README.md) | science | Lab researchers, R&D teams, computational scientists, and scientific AI builders. | Experiment planning is sequential; each result changes the next best experiment and the cost-risk tradeoff. | Iterative experiment outcome simulation. | Experimental design scientist. | Experiment optimization plan with ranked experiment options. |
| [`science_climate_resilience_planning_engine`](science_climate_resilience_planning_engine/README.md) | science | Municipal resilience teams, infrastructure planners, utilities, and climate-risk analysts. | Climate events unfold over time and stress infrastructure unevenly; static risk maps do not recommend operational mitigations during a scenario. | Weather, flooding, and infrastructure vulnerability simulation. | Climate resilience planning advisor. | Local climate mitigation plan with ranked assets. |
| [`science_drug_discovery_closed_loop_lab`](science_drug_discovery_closed_loop_lab/README.md) | science | Computational biology researchers and scientific AI platform evaluators. | Discovery workflows are iterative: candidate generation, scoring, extraction, and review need to repeat as new evidence arrives. | Long-running scientific pipeline loop. | Scientific manager and staged worker agents. | Candidate artifacts, stage logs, and discovery summaries. |
| [`science_ecosystem_intervention_sandbox`](science_ecosystem_intervention_sandbox/README.md) | science | Ecologists, conservation analysts, simulation researchers, and education teams. | Ecological systems change through local interactions, migration, resources, and mutation; interventions need scenario testing before field action. | Multi-region population dynamics. | World coordinator, regional agents, leaderboard summarizer. | Regional outcomes, population rankings, and ecosystem summary. |
| [`science_multi_agent_motion_planning_lab`](science_multi_agent_motion_planning_lab/README.md) | science | Robotics researchers, simulation developers, and multi-agent systems educators. | Multi-agent coordination depends on changing positions, goals, and collisions; users need visual traces, not only scalar metrics. | Multi-agent particle environment. | World simulator and visualization summarizer. | Simulation summary and visual artifacts. |
| [`science_outbreak_response_policy_simulator`](science_outbreak_response_policy_simulator/README.md) | science | Public-health planners, epidemiology teams, campus operations, and policy analysts. | Outbreak response depends on time-varying spread and healthcare load; static dashboards cannot test policy consequences before action. | Disease spread and intervention simulation. | Public-health intervention advisor. | Public-health intervention plan with state trajectory. |
| [`science_urban_traffic_control_lab`](science_urban_traffic_control_lab/README.md) | science | City traffic teams, transportation researchers, smart-city operators, and mobility startups. | Traffic control decisions are coupled and time-sensitive; dashboards show congestion but do not reason over next-state control options. | Traffic network and incident-control simulation. | Traffic systems control advisor. | Traffic control plan with corridor ranking and action history. |

## How to choose a blueprint

Start with the decision you want to improve:

- Choose `business_` when the value is operational: service level, revenue, capacity, retention, pricing, safety, or supply resilience.
- Choose `finance_` when the value is risk or opportunity: liquidity, default pressure, portfolio shocks, claims triage, or property acquisition.
- Choose `science_` when the value is policy, control, experiment selection, or intervention planning inside a modeled environment.
- Choose `general_` when you want to learn or reuse a runtime capability before adding a domain model.

Run the blueprint with mock data first. Then inspect `timeline`, `state_changes`, `events.jsonl`, and `final_artifact.json`. The goal is to understand the loop before replacing the data.

## How to run

Shared simulation blueprints can be run directly from their folder:

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

Portfolio-level run observation commands:

```bash
mn blueprint list
mn blueprint monitor --follow
mn blueprint tail <run_id>
mn blueprint compare <run_a> <run_b>
mn blueprint export <run_id> --format markdown
```

Live Ollama run:

```bash
MN_LLM_API_BASE=http://192.168.4.173:11434 \
MN_LLM_MODEL=ollama/nemotron3:33b \
python3 payloads/simulation_loop/scripts/run_blueprint.py --steps 3
```

## What to customize

1. Replace synthetic inputs with a real adapter while preserving the input shape.
2. Tune simulation parameters and action effects using historical data or domain experts.
3. Update the LLM agent role, allowed actions, and final artifact schema.
4. Add human approval for irreversible, regulated, or costly decisions.
5. Connect final artifacts to the workflow system where decisions are reviewed or executed.
6. Keep `blueprint_id`, `name`, `run_id`, and run-store artifacts stable for auditability.

## Why this matters for evaluators

The portfolio shows why MirrorNeuron is differentiated from dashboards and chatbots. Dashboards show state, and chatbots explain state, but these blueprints let agents act inside a simulated system and then observe the consequences. That makes the runtime useful for vertical products where delayed effects, policy tradeoffs, and auditability matter.

The strongest commercial wedges are the blueprints with expensive recurring decisions: supply-chain resilience, revenue retention, service capacity, dynamic pricing, property acquisition, portfolio stress, claims triage, climate planning, and adaptive experimentation.

## Developer architecture

Every blueprint folder contains:

- `manifest.json` with graph topology, metadata, entrypoints, workers, and output contracts.
- `description` in the manifest as a short plain-text explanation of what the blueprint is.
- `config/default.json` with standard identity, mock inputs, simulation settings, LLM settings, outputs, logging, and adapter declarations.
- `scenario.json` for data-driven simulation blueprints, including metrics, actions, default inputs, agent role, and final artifact type.
- `product.json` for portfolio positioning, including target users, commercial value, customization path, simulation type, and output narrative.
- `payloads/` with worker scripts, generated runners, policies, fixtures, or domain assets.
- `README.md` with what the blueprint is, why it matters, how to run it, what to customize, and how to interpret outputs.

The shared execution support lives in `mn-skills/blueprint_support_skill`. This repository intentionally contains blueprint assets only: manifests, configs, payloads, docs, and tests.

## Tests

Run the full blueprint suite:

```bash
python3 -m pytest -q
```

Run optional Ollama smoke tests explicitly:

```bash
RUN_OLLAMA_INTEGRATION=1 \
MN_LLM_API_BASE=http://192.168.4.173:11434 \
MN_LLM_MODEL=ollama/nemotron3:33b \
python3 -m pytest tests/test_blueprint_library.py -m ollama -q
```

## Rename migration notes

Old names are preserved as aliases in `mn_blueprint_support.product_catalog.LEGACY_ALIASES` where the shared runner can resolve them. New category naming uses `finance_`, not `financial_`.

| Old name | New name | Reason |
|---|---|---|
| `business_email_campaign_deamon` | `business_customer_lifecycle_email_copilot` | Frames email automation as lifecycle growth orchestration. |
| `business_pricing_strategy_simulation` | `business_dynamic_pricing_profit_optimizer` | Connects pricing simulation to margin and profit outcomes. |
| `video_safety_door_monitor_deamon` | `business_facility_safety_video_guardian` | Moves the video safety workflow into a business operations category. |
| `business_customer_churn_intervention` | `business_revenue_retention_copilot` | Positions churn reduction as revenue retention. |
| `business_call_center_staffing_simulation` | `business_service_capacity_command_center` | Targets service leaders managing SLA and capacity tradeoffs. |
| `business_supply_chain_disruption_response` | `business_supply_chain_resilience_war_room` | Names the high-urgency operator workflow for disruption response. |
| `finance_insurance_claim_risk_triage` | `finance_claim_risk_triage_copilot` | Names the adjuster and SIU prioritization workflow. |
| `finance_credit_risk_simulation` | `finance_credit_default_early_warning_system` | Turns a simulation into an early-warning risk workflow. |
| `financial_market_realtime_advisor_deamon` | `finance_liquidity_microstructure_radar` | Repositions the market daemon around liquidity and microstructure risk. |
| `finance_portfolio_stress_test` | `finance_portfolio_crash_stress_lab` | Makes crash and rate-shock planning explicit. |
| `finance_real_estate_opportunity_finder` | `finance_zip_code_property_alpha_engine` | Frames real-estate search as market alpha discovery. |
| `general_agent_loop_demo` | `general_closed_loop_agent_runtime` | Reframes the demo as the core closed-loop runtime pattern. |
| `general_context_memory_basic` | `general_context_memory_audit_pipeline` | Positions the context-memory workflow as an audit pipeline. |
| `general_context_memory_advanced` | `general_context_memory_compression_lab` | Highlights compression and context packet behavior under pressure. |
| `general_dynamic_environment_demo` | `general_dynamic_environment_control_loop` | Emphasizes control over a changing system. |
| `general_event_stream_processing` | `general_event_stream_triage_state_machine` | Focuses on stateful event triage, not generic processing. |
| `general_human_in_the_loop_decision` | `general_human_approval_decision_gate` | Names the approval-gated decision workflow. |
| `general_stream_basic_deamon` | `general_live_telemetry_stream_pipeline` | Clarifies that the blueprint demonstrates live telemetry stream handling. |
| `general_llm_tool_use_demo` | `general_llm_tool_orchestration_loop` | Makes tool orchestration and feedback loops explicit. |
| `general_test_message_flow` | `general_message_routing_trace` | Removes test/demo positioning and focuses on message routing traceability. |
| `general_multi_agent_negotiation` | `general_multi_agent_contract_negotiation_loop` | Makes the multi-agent negotiation outcome concrete. |
| `general_native_live_deamon` | `general_native_live_monitor_daemon` | Fixes the daemon typo and names the live native-agent monitoring value. |
| `general_openshell_worker_basic` | `general_openshell_sandbox_worker_pipeline` | Repositioned from a basic worker example to a sandboxed execution pipeline. |
| `general_prime_sweep_scale` | `general_parallel_worker_scale_benchmark` | Frames the blueprint around parallel runtime scale rather than prime numbers. |
| `general_policy_optimization_demo` | `general_policy_feedback_optimization_loop` | Clarifies that policies are optimized through feedback. |
| `general_python_defined_advanced_deamon` | `general_python_sdk_live_research_daemon` | Fixes the daemon typo and emphasizes the live Python workflow loop. |
| `general_python_defined_basic` | `general_python_sdk_research_pipeline` | Clarifies that this is a Python SDK workflow users can adapt. |
| `general_openshell_llm_codegen` | `general_sandboxed_llm_codegen_review_loop` | Highlights sandboxed LLM generation, review, and validation. |
| `general_simulation_state_tracking` | `general_simulation_state_audit_trail` | Frames state tracking as an audit trail users can inspect. |
| `general_stream_live_backpressure_deamon` | `general_stream_backpressure_control_loop` | Fixes daemon wording and makes backpressure control the value. |
| `science_lab_experiment_optimizer` | `science_adaptive_experiment_discovery_agent` | Highlights adaptive experiment selection over static optimization. |
| `science_climate_risk_local_planning` | `science_climate_resilience_planning_engine` | Frames climate risk as actionable resilience planning. |
| `science_drug_discovery_deamon` | `science_drug_discovery_closed_loop_lab` | Fixes daemon wording and names the closed-loop scientific workflow. |
| `science_ecosystem_simulation` | `science_ecosystem_intervention_sandbox` | Makes ecosystem management and intervention testing explicit. |
| `science_mpe_simple_push_visualization` | `science_multi_agent_motion_planning_lab` | Removes simple/demo wording and emphasizes multi-agent planning. |
| `science_flu_spread_intervention_simulation` | `science_outbreak_response_policy_simulator` | Names the policy decision this outbreak model supports. |
| `science_traffic_congestion_control` | `science_urban_traffic_control_lab` | Targets city traffic teams and control-room experimentation. |
