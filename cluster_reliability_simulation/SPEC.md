# Cluster Reliability Simulation SPEC

## Purpose

Build a special MirrorNeuron blueprint for testing and demonstrating cluster reliability management features on a small combined cluster. The blueprint focuses on recently added Nomad-inspired behavior: job type semantics, resource-aware placement, lifecycle policies, service health, automatic recovery, drain, and maintenance.

## Customer Problem

Runtime operators need a repeatable way to prove that a cluster will place work correctly, move only replayable work, avoid ineligible nodes, and pause unsafe recovery for review. Unit tests are necessary but do not give a product evaluator or operator a clear rehearsal path.

## Expected Outcome

A successful demo shows:

- both local and remote runtime nodes are visible;
- scheduler planning respects resources, capabilities, constraints, and strategy;
- service jobs persist restart and reschedule policy metadata;
- service, batch, system, and sysbatch behavior is represented in the test plan;
- maintenance stops new placements without moving current work;
- drain dry runs report what would move or wait;
- unsafe recovery is represented as manual review rather than automatic replay.

## Reliability Features Covered

| Feature | Demo surface |
|---|---|
| `service` job type | Base manifest uses long-running service semantics. |
| `batch` job type | Config demo variant defines finite drain behavior. |
| `system` job type | Config demo variant defines one copy per eligible node. |
| `sysbatch` job type | Config demo variant defines one completion per eligible node. |
| Spread scheduling | Base manifest uses `scheduler_strategy: spread`. |
| Binpack scheduling | Config scheduler check covers batch binpack rehearsal. |
| Resources | Nodes request CPU, memory, disk, and a demo port. |
| Constraints | Manifest includes node-role and capability constraints. |
| Restart policies | Job and node-level restart policies cover constant, exponential, and fibonacci delay functions. |
| Reschedule policies | Service unlimited and batch bounded reschedule policies are included. |
| Service discovery | Demo service declarations and optional health checks are present. |
| Safe replay | Replayable probes include idempotency markers. |
| Manual recovery | Unsafe recovery gate requires review. |
| Maintenance | Runbook covers cordon and uncordon. |
| Drain | Runbook covers dry-run, deadline, batch waiting, and completion into maintenance. |

## Prototype Limits

This blueprint is a controlled reliability lab. It does not guarantee exactly-once delivery, consensus workflow replay, or production-grade Redis availability. It should not be used to justify automatic movement of unsafe external side effects without additional workload-specific testing.

## Upgrade Path

1. Add real cluster node names and capabilities from `mn nodes`.
2. Add a rendered-manifest cluster placement test for every target worker pool.
3. Add a recoverable workload that writes durable snapshots.
4. Add a failure drill for executor-node loss and coordinator-node loss.
5. Promote Redis to Sentinel HA before treating the cluster as production-like.
