# MirrorNeuron Runtime Demo Blueprints

Runtime demos use Python 3.12, matching the SDK, native services, and Core HostLocal.

Twenty-seven focused, deterministic blueprints for learning and testing one MirrorNeuron runtime feature at a time.

| Blueprint | Category | Primary feature |
|---|---|---|
| `demo_native_beam_agent` | Execution | Native BEAM module agent |
| `demo_hostlocal_worker` | Execution | HostLocal execution |
| `demo_docker_worker` | Execution | DockerWorker execution |
| `demo_openshell_worker` | Execution | OpenShell isolation |
| `demo_python_sdk_workflow` | Execution | Python SDK compilation |
| `demo_dag_linear` | Workflow DAG | Linear DAG |
| `demo_dag_fork_join` | Workflow DAG | Parallel fork/join |
| `demo_dag_scatter_gather` | Workflow DAG | Runtime scatter/gather |
| `demo_dag_conditional_branch` | Workflow DAG | Conditional branching |
| `demo_dynamic_workflow` | Workflow DAG | Bounded dynamic DAG patching |
| `demo_dag_failure_fallback` | Workflow DAG | Failure-triggered fallback |
| `demo_dag_quorum` | Workflow DAG | Quorum trigger |
| `demo_human_approval` | Collaboration | Human-control gate |
| `demo_llm_tool_call` | Collaboration | LLM tool orchestration |
| `demo_mcp_collaboration` | Collaboration | Cross-job MCP collaboration |
| `demo_context_memory_acl` | Memory | Context Engine role ACLs |
| `demo_context_compression` | Memory | CompileContext compression |
| `demo_stream_backpressure` | Runtime Operations | Stream backpressure |
| `demo_executor_pool` | Runtime Operations | Executor lease capacity |
| `demo_service_health` | Runtime Operations | Service registration and health |
| `demo_resource_allocation` | Runtime Operations | Resource-aware placement |
| `demo_retry_recovery` | Runtime Operations | Step retry policy |
| `demo_checkpoint_replay` | Runtime Operations | Checkpoint resume |
| `demo_periodic_schedule` | Runtime Operations | Periodic scheduling |
| `demo_event_trigger` | Runtime Operations | Event-triggered jobs |
| `demo_observability_trace` | Runtime Operations | Run-store observability |
| `demo_canary_deployment` | Runtime Operations | Canary promotion |

## Blueprint repositories

These product blueprints are maintained in their own public repositories and pinned
here as Git submodules. `index.json` controls their catalog publication.

| Blueprint | Repository |
|---|---|
| `financial_advisor` | [mn-blueprint-financial_advisor](https://github.com/MirrorNeuronLab/mn-blueprint-financial_advisor) |
| `research_assistant` | [mn-blueprint-research_assistant](https://github.com/MirrorNeuronLab/mn-blueprint-research_assistant) |
| `microduck_controller` | [mn-blueprint-microduck_controller](https://github.com/MirrorNeuronLab/mn-blueprint-microduck_controller) |

Clone the catalog with its pinned packages:

```bash
git clone --recurse-submodules https://github.com/MirrorNeuronLab/mn-blueprints.git
```

After pulling an existing checkout, initialize or update the recorded commits:

```bash
git submodule update --init --recursive
```

Use `development` for local work in the catalog and each submodule. Create the
branch from the current commit if it does not exist yet. Commit submodule
changes on `development` before committing their updated pins in the catalog.
Submodule URLs use public HTTPS and development origins may use SSH. Local
development reads the checked-out folders without fetching or changing their
revisions.

When the production runtime is ready, run the release script from clean
`development` checkouts with every updated submodule pin committed:

```bash
./scripts/sync-development-to-main.sh --dry-run
./scripts/sync-development-to-main.sh
```

The script fast-forwards local `main` and `origin/main` in each submodule before
updating the catalog. If a push fails, resolve the Git error and rerun the script.

## Validate the catalog

```bash
python3 scripts/verify_catalog.py --validate
python3 scripts/generate_catalog.py --check
```

## Run the suite

Start the local runtime and Context Engine, then run:

```bash
mn runtime start
mn runtime ensure-context-engine
python3 scripts/run_demo_suite.py
```

The first Docker/OpenShell/context run may prepare cached dependencies. Warm batch demos target 10 seconds, operational demos target 20 seconds, and no demo requires a GPU or real model. Service, schedule, event-trigger, human-control, and deployment demos document their operator lifecycle in their own README and SPEC files.

## Canonical packages

`index.json` is an ordered list of published package paths. Names, descriptions,
versions, requirements, and product information come from each package's documents.
Catalog reads validate data without importing Python code or preparing resources.
All folders and ZIPs use `https://mirrorneuron.io/schemas/blueprint/v1/manifest.schema.json`.
Use `mn_sdk.blueprints.read_blueprint`, `resolve_config`, and `compile_blueprint`;
`open_blueprint` adds ZIP extraction and `export_blueprint` preserves the full package.
External dependencies remain declared; offline vendoring is optional.

## Dependency ranges

MirrorNeuron Python dependencies in `dependencies.json`, execution configuration,
and worker requirements use `>=1.3.47`. Bundled demo distributions are versioned
`1.3.47` and their declarations use the same minimum. Third-party libraries retain
their own version families (for example `numpy>=2.3.5,<3.0`). Package identity
versions and container image digests remain concrete artifact identities.

## Runtime activity

Use `mn_sdk.report_activity(message, kind="action", level="info",
owner_blueprint=..., step_id=..., run_dir=...)` for actual domain work and
observed findings. `kind` is `action`, `result`, `finding`, `milestone`, or
`diagnostic`; `level` is `debug`, `info`, `warning`, or `error`.
Use `mn_sdk.activity_operation(message, completed=...)` around a synchronous
domain operation when action/result reporting is sufficient. Do not define
blueprint-local formatters, publishers, stdout prefixes, or event clocks.
The SDK supplies the canonical `mn.runtime.event.v1` envelope with identity,
UTC timestamp, blueprint owner, run, step, and agent attribution. Existing
shell/native protocol records are normalized by Core at publication.
Only report observed facts; unchanged frame sampling and model bookkeeping
belong in diagnostics. Full outputs remain in artifacts.
