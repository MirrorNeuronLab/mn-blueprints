# DAG flow patterns demo

`demo_dag_flow_patterns` is a small, runtime-format MirrorNeuron blueprint.
Every executor calls `payloads/dag_demo_step.py`, which emits a structured
hello-world result. A few named steps also emit intentional control events so
the runtime can demonstrate branching, scatter mapping, guards, and handled
failure triggers.

## Run it

From this folder, run the bundle through the MN runtime. `run.py` sends the
manifest and every file from `payloads/` directly to the Core gRPC `SubmitJob`
endpoint; `run.sh` waits for the resulting runtime job. The entrypoint is
`start`; it fans out into all independent examples and a terminal `report_sink`
completes the job after `finish`.

```bash
./run.sh
```

The top-level `dag_demo_start` trigger demonstrates the event-driven entry
path. Use an event with `source: demo` where event triggers are configured.

## Patterns in the graph

| Pattern | Steps / configuration |
| --- | --- |
| Linear pipeline | `linear_a → linear_b → linear_c` |
| Fan-out and fan-in | `fork_a → [fork_b, fork_c, fork_d] → fan_in_join` |
| Scatter–gather | `scatter_source → scatter_worker[*] → scatter_collect` |
| Conditional branch | `branch_router` selects `branch_left`; `branch_join` uses `none_failed_min_one_success` |
| Short circuit | `short_circuit_guard` skips `guard_leaf` with `skip_downstream: true` |
| Any success | `any_success_join` uses `one_success` |
| Any completion | `any_done_join` uses `one_done` with one intentional handled failure |
| Failure handler | `failure_handler` uses `one_failed` after `failure_source` fails intentionally |
| Wait for everything | `all_done_cleanup` uses `all_done` |
| Fallback chain | `fallback_primary → fallback_secondary → fallback_emergency`, using `one_failed` |
| Quorum | `quorum_join` uses `quorum_success` with quorum `2` |
| Setup–work–teardown | `setup → work → teardown`, with `teardown` using `all_done` |
| Wait for external event | `sensor_wait → sensor_continue` is the sensor-shaped path; this demo simulates the arrival with a hello-world worker |
| Event-driven DAG | top-level `dag_demo_start` trigger |

Each executor has `runner_module: MirrorNeuron.Runner.HostLocal`,
`upload_path: dag_demo_step.py`, and `workdir: /sandbox/job`; this
is what turns the declarative graph into an executable job. Core receives
`payloads/dag_demo_step.py`, copies it into the sandbox, and then invokes
`python3 dag_demo_step.py`.

## Inspecting results

The most useful events are `workflow_step_scattered`, `workflow_step_branch`,
`workflow_step_skipped`, `workflow_step_failed`, and `workflow_step_triggered`.
Mapped workers are stored as `scatter_worker[0]`, `scatter_worker[1]`, and
`scatter_worker[2]` in the durable workflow state.
