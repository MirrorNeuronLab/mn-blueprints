# MirrorNeuron Blueprint Standard

MirrorNeuron blueprints are deployable intelligence workflows. Each blueprint is expected to run with synthetic data immediately, then graduate to real inputs, external systems, and production observability without changing its public contract.

The standard exists to make the library more than a set of demos: every blueprint has a stable identity, a configurable execution model, clear input and output interfaces, and a run record that can be audited after execution.

The reusable implementation lives in focused modules under `mn-skills/blueprint_support_skill/src/mn_blueprint_support/`. `standard.py` remains a compatibility facade that re-exports the public contract, while implementation lives in modules such as `config.py`, `input_adapters.py`, `run_store.py`, `runtime.py`, `worker_contract.py`, `observability.py`, `web_ui.py`, `cli_runtime.py`, `llm.py`, `scenarios.py`, `product_catalog.py`, `catalog_loader.py`, `solution_runner.py`, and `scaffold.py`.

The shared skill owns the reusable framework pieces: blueprint metadata loading, stable identity, config merging, input adapters, output adapter resolution, run-store artifacts, logging helpers, runtime context, common CLI execution, first-run setup, local user config persistence, and run observability. The root `index.json` owns portfolio/product catalog data, while blueprint folders own concrete scenario and runtime data through `scenario.json`, `manifest.json`, and `config/default.json`.

All local user state defaults to `~/.mn`: runs live in `~/.mn/runs`, local config lives in `~/.mn/config.json`, and support logs live in `~/.mn/logs`. Older legacy-home references should be treated as migrated to `~/.mn`.

## Architecture

Each blueprint is separated into seven concerns:

| Concern | Source | Purpose |
|---|---|---|
| Metadata | Root `index.json`, `manifest.json`, `config/default.json`, and blueprint `README.md` | Describes the product use case, target users, graph topology, runtime features, and output contract. |
| Config | `config/default.json` plus `mn_blueprint_support.config.load_config` | Controls how the blueprint runs without changing code. |
| Inputs | `inputs` config section, payload fixtures, and `mn_blueprint_support.input_adapters.resolve_input_overrides` | Defines where data comes from. Defaults to mock data and supports real adapters. |
| Simulation / logic | Worker payloads, blueprint-owned `scenario.json`, or specialized code | Evolves domain state over time. |
| Optimization | Optional blueprint-owned `scenario.json` model declarations, such as Pyomo linear programs | Solves constrained action plans before agent explanation or execution. |
| LLM agents | `llm` config section and worker prompts | Observes state, reasons about decisions, and returns structured actions or reports. |
| Outputs | `outputs` config section and `mn_blueprint_support.run_store.RunStore` | Writes results, final artifacts, and machine-readable execution records. |
| Logging | `logging` config section, `events.jsonl`, and `mn_blueprint_support.log_status` | Captures what happened during execution for debugging, audit, and analytics. |
| Web UI | `web_ui` config section and `mn_blueprint_support.web_ui` | Registers live input GUIs, customer dashboards, or static HTML output reports. |

## Shared Skill APIs

| Need | Shared API |
|---|---|
| Blueprint metadata | `BlueprintMetadata.from_manifest()` |
| Runtime context | `create_runtime_context()` and `BlueprintRuntimeContext` |
| Specialized worker contract | `create_worker_run_contract_from_environment()` for sandbox payloads that need the same run IDs, inputs, event logs, and final artifacts |
| CLI execution | `run_blueprint_cli()` and `build_cli_parser()` |
| First-run setup | `interactive_first_run_setup()` |
| Local user config | `UserConfigStore`, `load_user_config()`, `save_user_config()` |
| Run observability | `list_runs()`, `load_run()`, `read_run_events()`, `summarize_run()` |
| Web UI input/output | `WebInputField`, `launch_gradio_input_app()`, `collect_gradio_input()`, `write_static_run_report()`, `register_web_ui()` |
| Blueprint creation | `scaffold_blueprint()` |
| Config UX | `config_summary()`, `validate_config()`, `validate_blueprint_directory()` |

## Stable Identity

Every run has three identity fields:

| Field | Description |
|---|---|
| `blueprint_id` | Stable unique machine identifier, such as `finance_portfolio_crash_stress_lab`. |
| `name` | Human-readable label, such as `Portfolio Crash Stress Lab`. |
| `run_id` | Unique execution ID. It can be supplied by the caller or generated automatically. |

The result object returns these under `identity`, and the same `run_id` is used as the directory name in the global run store.

## Category Prefixes

New blueprints use one of four category prefixes: `general_`, `business_`, `finance_`, or `science_`. Finance blueprints are standardized on `finance_`; historical `financial_*` names should be treated only as migration aliases.

Every `manifest.json` also includes a short top-level `description` field so registry users can understand the blueprint without opening the full README.

## Configuration

Every blueprint includes `config/default.json` with these sections:

| Section | Description |
|---|---|
| `metadata` | Target user, category, problem solved, and customization target. |
| `identity` | `blueprint_id`, readable `name`, and optional `run_id`. |
| `inputs` | Input adapter and default payload. |
| `simulation` | Dynamic state model, deterministic seed behavior, metrics, and action metadata where applicable. |
| `llm` | Agent role, model, Ollama endpoint, mock mode, and responsibilities. |
| `outputs` | Output adapter, global run root, and final artifact contract. |
| `logging` | Event names, JSONL logging behavior, and log level. |
| `real_adapters` | Built-in extension points for replacing mocked data. |
| `interfaces` | Declared identity fields, config sections, input adapters, and run artifacts. |
| `execution_model` | Ordered lifecycle stages from metadata load to final artifact write. |

Callers can override configuration with `--config`, `--config-json`, `--run-id`, `--runs-root`, `--input-file`, `--input-json`, or equivalent Python arguments.

## Input Adapters

Blueprints default to mocked or synthetic inputs so they run out of the box.

| Adapter | Use case |
|---|---|
| `mock` | Use bundled synthetic payloads. |
| `json` | Use an inline JSON object. |
| `file` | Load a local JSON file. |
| `env_json` | Load JSON from `MN_BLUEPRINT_INPUT_JSON` or a configured environment variable. |

Production teams should replace mocked generators with CRM, ERP, market-data, sensor, claims, lab, ticketing, warehouse, or database adapters while preserving the same input shape used by the simulation loop.

## Execution Model

The standard observe-decide-act execution model is:

1. Load metadata from the manifest and product catalog.
2. Resolve configuration from defaults and caller overrides.
3. Load inputs through the selected adapter.
4. Create or reuse `run_id`.
5. Start the global run store.
6. Observe the current simulated or live system state.
7. Call the LLM agent with role, state, valid actions, and fallback policy.
8. Apply the selected decision to the simulation or workflow.
9. Emit structured events for each meaningful transition.
10. Write `result.json` and `final_artifact.json`.

Data-driven simulation blueprints use the full shared loop in `mn_blueprint_support.solution_runner`. A scenario can optionally declare an optimization model, such as a Pyomo linear program, and the shared loop will attach the optimized variables, objective, constraints, and expected outcome to the observation and final artifact. Specialized blueprints that run sandbox payloads use `mn_blueprint_support.worker_contract` to keep the same run IDs, config snapshots, input records, events, result artifacts, and final artifacts even when their internal simulation code is custom.

## Global Run Store

By default, every run writes to:

```text
~/.mn/runs/<run_id>/
```

Support status logs use the same home:

```text
~/.mn/logs/blueprint-support.log
```

Each completed run contains:

| Artifact | Description |
|---|---|
| `run.json` | Run identity, status, timestamps, and artifact paths. |
| `config.json` | Resolved runtime configuration used for this execution. |
| `inputs.json` | Effective inputs after adapter and caller overrides. |
| `events.jsonl` | Append-only event stream for the run. |
| `result.json` | Full structured result object. |
| `final_artifact.json` | User-facing recommendation, report, forecast, or plan. |

For tests and local experimentation, pass `--runs-root <path>` to isolate output. Pass `--no-run-store` only when stdout is enough and audit artifacts are not needed.

## Local User Config

Reusable first-run setup and local config persistence live in `mn_blueprint_support.user_config`. The default path is:

```text
~/.mn/config.json
```

It can be overridden with `MN_CONFIG_PATH` or `--user-config`. Shared CLI runners support:

```bash
python3 payloads/simulation_loop/scripts/run_blueprint.py --setup
python3 payloads/simulation_loop/scripts/run_blueprint.py --setup --non-interactive-setup
```

The local config stores default LLM, output, and logging preferences that can be merged into blueprint runs without editing individual blueprint files.

## Run Observability

The shared skill exposes run inspection helpers:

- `list_runs()` for recent run summaries.
- `load_run()` for full run records.
- `read_run_events()` for `events.jsonl`.
- `summarize_run()` for compact reporting.

Shared CLI runners expose the same behavior:

```bash
python3 payloads/simulation_loop/scripts/run_blueprint.py --list-runs
python3 payloads/simulation_loop/scripts/run_blueprint.py --show-run <run_id>
```

## Blueprint Creation UX

The shared skill can scaffold a new blueprint with standard identity, config, manifest, README, runnable placeholder payload, and smoke test from Python automation:

```python
from mn_blueprint_support import scaffold_blueprint

scaffold_blueprint(
    "general_customer_signal_lab",
    root=".",
    description="Explore customer signals with a dynamic agent loop.",
)
```

The scaffold is intentionally runnable but lightweight: it proves the config, input adapter, run-store, and monitoring path, then gives developers a clear place to replace placeholder simulation logic with domain behavior.

## Config UX

Users inspect the actual resolved config after a run through the global run store:

```bash
mn blueprint run general_customer_signal_lab
mn blueprint export <run_id> --format markdown
mn blueprint tail <run_id>
```

These commands surface the input adapter, output adapter, run root, LLM mode/model, decisions, events, and final artifacts without requiring users to read every JSON field by hand.

## LLM Configuration

LLM-backed blueprints default to Ollama:

```text
api_base: http://192.168.4.173:11434
model: ollama/nemotron3:33b
```

Fast tests use the deterministic fake LLM adapter. Optional integration tests can be enabled with:

```bash
RUN_OLLAMA_INTEGRATION=1 \
LITELLM_API_BASE=http://192.168.4.173:11434 \
LITELLM_MODEL=ollama/nemotron3:33b \
python3 -m pytest tests/test_blueprint_library.py -m ollama -q
```

## Testing Contract

The shared tests verify that every blueprint:

- Has a loadable manifest and `config/default.json`.
- Declares standard identity, config, input, output, and execution interfaces.
- Runs end to end with a fake LLM where the shared simulation runner applies.
- Accepts required inputs and real-input adapter overrides.
- Changes simulation state over time.
- Exercises the LLM decision path.
- Writes global run artifacts with event logs.
- Produces a structured final artifact.
- Keeps live Ollama tests optional and explicitly marked.

## Production Extension Path

To adapt a blueprint for a real deployment:

1. Replace synthetic inputs with a real adapter.
2. Calibrate simulation parameters with historical data or domain experts.
3. Narrow the agent action schema to approved operational actions.
4. Add human approval for irreversible or regulated decisions.
5. Connect outputs to the existing workflow system.
6. Add evaluation metrics and alerting around run outcomes.
7. Keep the run-store contract stable so runs remain auditable across blueprint versions.
