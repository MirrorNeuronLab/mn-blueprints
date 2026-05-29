# Cluster Reliability Simulation

`Blueprint ID:` `cluster_reliability_simulation`
`Category:` Engineering - Cluster Reliability Demo
`Default LLM:` Ollama `nemotron3:33b` with deterministic fake LLM support for tests

## One-line value proposition

Use this blueprint to test and demo the advanced cluster reliability controls recently added to MirrorNeuron.

## What it is

This is a special MirrorNeuron blueprint for exercising the runtime itself. It packages a compact service-style workflow that makes scheduling, lifecycle policy, service registration, safe replay, node drain, and maintenance behavior visible in one place.

It is meant to run with mock inputs first, then on a combined cluster with a local node and a remote node such as `192.168.4.173`.

## Who this is for

Runtime engineers, cluster operators, and evaluators who need a repeatable reliability demo before trusting multi-machine agent workloads.

## Why it matters

Cluster reliability is difficult to judge from a static dashboard or a one-shot LLM explanation. Operators need to see placement decisions, recovery policy, drain behavior, and unsafe-work boundaries move through the same runtime path that real workloads use.

## Why this runtime is useful here

MirrorNeuron can place agents on eligible machines, preserve durable state, apply restart and reschedule policies, and pause unsafe recovery for review. This blueprint turns those runtime mechanics into an inspectable test surface, so a small two-box lab can prove what will happen before a service, batch, system, or sysbatch job is trusted.

## How it works

1. Start with a service job using `cluster_recover` and `spread` scheduling.
2. Place lightweight probe agents with CPU, memory, disk, port, and capability requirements.
3. Register a demo service and rehearse service health metadata.
4. Mark replayable probes with idempotency keys so automatic movement is safe.
5. Send unsafe recovery through a manual gate so operators can see where automation stops.
6. Use the config variants to rehearse `service`, `batch`, `system`, and `sysbatch` behavior.
7. Inspect scheduler, policy, drain, maintenance, and recovery evidence through the CLI.

## Example scenario

A local runtime node and `mn2@192.168.4.173` form a combined cluster. The scheduler spreads replayable service work, keeps unsafe work behind review, performs a remote-node drain dry run, allows batch work to finish before a deadline, and leaves the drained node in maintenance until the operator marks it eligible again.

## Inputs

| Input | What it controls | Example | Can customize? |
|---|---|---|---|
| `manifest.json` initial inputs | The default two-node reliability rehearsal. | `two_box_combined_cluster` | Yes |
| `config/default.json` | Scheduler checks, demo variants, run-store, and policy defaults. | `cluster_reliability.demo_variants` | Yes |
| `config/overwrite.json` | Local cluster hostnames, node hints, or budget overrides. | `cluster_reliability.remote_node_hint` | Yes |
| Payload probe | Deterministic JSON report emitted by test agents. | `payloads/reliability_probe/scripts/reliability_demo.py` | Yes |
| Environment variables | Runtime, Redis, and cluster settings used by the CLI. | `MN_CLUSTER_NODES`, `MN_REDIS_URL` | Yes |

## Outputs

| Output | What it means | Where to look |
|---|---|---|
| Scheduler evidence | Placement, resources, constraints, and service-plan checks. | `mn status <job-id>` |
| Reliability evidence | Effective recovery policy, restart/reschedule state, and recovery status. | `mn status <job-id>` |
| Drain evidence | Dry-run or real drain actions and node state. | `mn drain-node`, `mn undrain-node` |
| Final artifact | Demo summary and operator checklist. | `result.json`, `final_artifact.json` |
| Logs and events | Typed runtime and probe events. | `events.jsonl`, runtime logs |

## How to run

Render and validate the blueprint from this repository checkout:

```bash
mn blueprint run cluster_reliability_simulation
```

For a combined cluster rehearsal, start or join the local node and the remote node first, then inspect the cluster:

```bash
mn nodes
mn resource list
mn service list
```

Rehearse maintenance safely before moving work:

```bash
mn maintenance-node mn2@192.168.4.173 --enable --reason "reliability demo cordon"
mn maintenance-node mn2@192.168.4.173 --disable --reason "reliability demo complete"
```

Rehearse drain with a dry run before a real drain:

```bash
mn drain-node mn2@192.168.4.173 --reason "reliability demo drain" --deadline 30s --dry-run
```

## How to customize it

Replace the default node hints with your cluster node names, add capabilities that match your worker pools, tune restart and reschedule windows, and replace the deterministic probe with a real workload that is safe to replay.

A practical customization path is:

1. Replace the mock local and remote node names with the actual `mn nodes` output.
2. Add capabilities such as `gpu`, `edge`, `private-lan`, or `replayable-work` to nodes.
3. Tune the restart and reschedule policies to match the workload risk.
4. Mark every replayable external action with an idempotency key.
5. Keep unsafe writes behind approval or manual recovery.

## What to look for in results

The strongest signal is whether the scheduler avoids ineligible nodes, policy state records attempts correctly, safe work can move, and unsafe work pauses instead of being duplicated.

Also confirm that service, batch, system, and sysbatch variants are represented, because each one has different recovery and drain behavior.

## Investor and evaluator narrative

This blueprint shows MirrorNeuron as a small Nomad-style runtime for AI workflow labs: it is not just a chatbot around work, and it is not only a static dashboard. It demonstrates placement, leases, service health, recovery policy, and operator-controlled movement as product surfaces that make agent infrastructure more trustworthy.

## Runtime features demonstrated

- service and batch reliability behavior
- system and sysbatch demo variants
- spread and binpack scheduling
- resource and capability constraints
- service registry and health checks
- restart and reschedule policies
- cluster recovery metadata
- node maintenance and drain workflows
- safe replay and manual recovery boundaries

## Test coverage

The shared blueprint suite verifies catalog metadata, standard config sections, agent-template rendering, and simulated template behavior. The runtime cluster check for this blueprint should verify combined-node visibility, scheduler placement, service listing, maintenance toggles, and drain dry-run output on local plus `192.168.4.173`.

## Limitations

- The bundled probe is deterministic and lightweight; it is designed to demonstrate runtime controls, not benchmark throughput.
- The base manifest is a service-style test surface; `batch`, `system`, and `sysbatch` are carried as explicit demo variants in config.
- A real drain should only be run after a dry run and after confirming the workload is safe to replay.
- Single Redis remains a development setup; use Redis HA before relying on multi-box recovery for consequential workloads.

## Next steps

- Run the combined-cluster smoke test after syncing this repository to the remote box.
- Add a GPU-constrained variant if the remote worker advertises GPU capacity.
- Add an unsafe external-write fixture to prove manual recovery pauses at the right boundary.
- Capture before and after `mn status` output as release evidence for future reliability changes.
