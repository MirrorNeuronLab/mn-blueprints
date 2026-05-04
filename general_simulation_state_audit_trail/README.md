# Simulation State Audit Trail

`Blueprint ID:` `general_simulation_state_audit_trail`  
`Category:` general - General Runtime Pattern  
`Default LLM:` Ollama `nemotron3:33b` with deterministic fake LLM support for tests

## One-line value proposition

Track simulation state deltas so every agent decision is explainable after the run.

## What it is

This blueprint is a reusable MirrorNeuron solution template for a reusable runtime capability that developers can adapt before adding domain data. It ships with mock or synthetic inputs so it runs immediately, and it defines a path for replacing those inputs with production data while keeping the same blueprint identity, configuration model, and output contract.

## Who this is for

Developers and evaluators who need inspectable state transitions.

## Why it matters

Dynamic systems are hard to trust unless users can see what changed, why an action was chosen, and how the next state moved. A static dashboard can show the current state, and a one-shot LLM prompt can summarize it, but neither tests what happens after a decision is applied. This blueprint makes the feedback loop visible: state changes, the agent observes it, the agent chooses an action, and the system evolves again.

## Why this runtime is useful here

MirrorNeuron is useful here because it combines LLM reasoning with dynamic system simulation. The agent is placed inside a changing environment instead of outside it as a commentator. Each run has stable identity fields, configurable inputs, structured events, and an auditable final artifact, so teams can compare scenarios, debug decisions, and graduate from mock data to real adapters.

## How it works

1. Load mock or adapter-provided inputs for state tracking and checkpoint simulation.
2. Initialize time-varying state with metrics such as `state_drift`, `measurement_confidence`, `intervention_count`, `stability_score`.
3. Advance the environment one step with deterministic seeded drift and volatility.
4. Ask the `State tracking analyst` to observe the current state, compare valid actions, and choose among `checkpoint_state`, `stabilize_system`, `hold_policy`.
5. Apply the selected action back into the simulated system so the next observation changes.
6. Write a structured final artifact for `state tracking report` with action history, state deltas, ranked options, and next steps.

## Example scenario

State drift increases, confidence changes, and the agent chooses checkpoints or stabilization actions while preserving a timeline.

## Inputs

| Input | What it controls | Example | Can customize? |
|---|---|---|---|
| `steps` | Scenario control, seed, or domain input. | 5 | Yes |
| `seed` | Scenario control, seed, or domain input. | 42 | Yes |
| `checkpoint_every_steps` | Scenario control, seed, or domain input. | 2 | Yes |
| `initial_state_drift` | Override the starting value for state drift. | 22 | Yes |
| `initial_measurement_confidence` | Override the starting value for measurement confidence. | 83 | Yes |
| `initial_intervention_count` | Override the starting value for intervention count. | 2 | Yes |
| `initial_stability_score` | Override the starting value for stability score. | 76 | Yes |

## Outputs

| Output | What it means | Where to look |
|---|---|---|
| `timeline` | Step-by-step observations, LLM decisions, applied actions, and state after each update. | `timeline[0].decision.action` |
| `state_changes` | Start, end, and delta for every simulated metric. | `drawdown_pct: 4.0 -> 6.2` |
| `final_artifact` | The user-facing state tracking report with deltas and ranked subsystems. | `recommended_action`, `ranked_options`, `next_steps` |
| `llm` | Provider, model, call count, and fallback metadata for the agent path. | `ollama/nemotron3:33b` or fake test client |
| Run directory | Auditable artifacts written under the global run store. | `run.json`, `events.jsonl`, `result.json` |

## How to run

Run a fast deterministic simulation with the fake LLM path:

```bash
cd general_simulation_state_audit_trail
python3 payloads/simulation_loop/scripts/run_blueprint.py \
  --mock-llm \
  --steps 3 \
  --runs-root /tmp/mirror-neuron-runs
```

Run the same blueprint against Ollama:

```bash
MN_LLM_API_BASE=http://192.168.4.173:11434 \
MN_LLM_MODEL=ollama/nemotron3:33b \
python3 payloads/simulation_loop/scripts/run_blueprint.py --steps 3
```

Inspect saved runs:

```bash
python3 payloads/simulation_loop/scripts/run_blueprint.py --list-runs
python3 payloads/simulation_loop/scripts/run_blueprint.py --show-run <run_id>
```

Run the shared repository tests:

```bash
cd ..
python3 -m pytest -q
```

## How to customize it

Add domain state fields, checkpoints, persistence, audit metadata, and evaluation metrics for your environment.

A practical customization path is:

1. Replace the mock input source with your system of record while preserving the input shape.
2. Calibrate simulation parameters and action effects with historical data or domain experts.
3. Update the LLM agent role, responsibilities, and allowed action schema.
4. Extend `final_artifact` so it matches the report, ticket, plan, or recommendation your team already uses.
5. Connect outputs to the review, approval, alerting, or execution system where real decisions happen.

## What to look for in results

Inspect `timeline` to see each observation and decision, `state_changes` to verify the simulated `stability_score` and `state_drift` moved over time, and `final_artifact` to review the recommended action and ranked tracked subsystem options.

The strongest signal is not only the final recommendation. Look for whether the state trajectory, agent rationale, applied actions, and output artifact tell a coherent story that a domain user could review.

## Investor and evaluator narrative

Traceability turns agent simulations into enterprise-grade decision records rather than black-box demos. The product lesson is that this is not just a chatbot around data. It is a repeatable pattern for vertical workflows where simulation, state, and agent decisions create a more defensible user experience than static analytics alone.

## Runtime features demonstrated

- state tracking
- history
- state deltas
- audit trail

## Test coverage

The shared test suite verifies manifest loading, standard config sections, mock inputs, deterministic fake LLM execution where applicable, state changes over time, CLI execution for shared runners, run-store artifacts, and structured final outputs. This blueprint is covered by runtime capability tests, manifest validation, and smoke tests for the relevant worker path. Optional Ollama tests are marked separately so local development stays fast.

## Limitations

- Mock data and simplified dynamics are included for repeatable local runs.
- Outputs are decision-support artifacts, not production advice.
- Domain assumptions should be validated before connecting real systems or acting on recommendations.
- Specialized worker blueprints may require the MirrorNeuron runtime or optional local services to execute the full graph.

## Next steps

- Connect a real data adapter and keep the input contract stable.
- Add scenario comparison, dashboards, or persisted memory for repeated runs.
- Add human approval gates for high-impact actions.
- Track evaluation metrics that compare simulated recommendations against known outcomes.
- Move operational logs and final artifacts into your team's normal review workflow.
