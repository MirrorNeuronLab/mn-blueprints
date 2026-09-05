# Specification: Checkpoint Replay

- Blueprint id: `demo_checkpoint_replay`
- Standard: `1.0`
- Primary runtime feature: `Checkpoint resume`
- Scenario: Checkpoint processed event IDs and ignore replayed duplicates.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, persisted executor state reports one
  ignored replayed event, the terminal event stream retains that duplicate
  evidence, and the runtime reaches the expected terminal state.

## Blueprint package format

This blueprint uses the canonical blueprint/v1 format in both folders and ZIPs.
`manifest.json` contains identity, semantic release version, and document references.
`workflow.json` owns logical topology and policies; `execution.json` owns workers,
resources, and services; `contracts.json` owns input/output and artifact contracts.
Platform descriptors live in `extensions/`, package requirements in
`dependencies.json` when present, and operator defaults in `config/default.json`.
The SDK reads these documents together and compiles the Core execution artifact.
A ZIP contains the same files as the folder. Local overrides and invocation
configuration are resolved by the SDK before launch.
