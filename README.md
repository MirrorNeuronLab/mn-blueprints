# MirrorNeuron Runtime Demo Blueprints

Twenty-five focused, deterministic blueprints for learning and testing one MirrorNeuron runtime feature at a time.

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
| `demo_dag_failure_fallback` | Workflow DAG | Failure-triggered fallback |
| `demo_dag_quorum` | Workflow DAG | Quorum trigger |
| `demo_human_approval` | Collaboration | Human-control gate |
| `demo_llm_tool_call` | Collaboration | LLM tool orchestration |
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
