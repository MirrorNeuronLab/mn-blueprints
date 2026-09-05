# Specification: Stream Backpressure

- Blueprint id: `demo_stream_backpressure`
- Standard: `1.0`
- Primary runtime feature: `Stream backpressure`
- Scenario: Process a finite burst through a bounded queue and report pressure handling.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, all ten emitted items drain through the
  bounded queue with no duplicates, terminal artifacts retain both burst and
  drain evidence, and the runtime reaches the expected terminal state.

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
