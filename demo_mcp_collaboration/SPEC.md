# Specification: MCP Job Collaboration

- Blueprint id: `demo_mcp_collaboration`
- Standard: `1.0`
- Primary runtime feature: cross-job MCP collaboration
- Scenario: two separately launched jobs share one goal, expose one MCP server
  each, discover each other through runtime service registration, and exchange
  job status, knowledge, staged results, and final results.
- Storage: one bounded job-scoped SQLite exchange per run.
- Dependencies: the canonical MCP client/server skill source packages are
  blueprint payloads; no MirrorNeuron skill index lookup is required.
- MCP authority: peer access is read-only; only the owning job publishes to its
  local store.
- Discovery: passing `mn-job-collaboration` services filtered by `goal_id` and
  excluding the caller's `job_id`.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters
  are also supported.
- Output: peer snapshots/update journals, the local exchange database, and
  standard run-store artifacts.
- Runtime budget: 30 seconds after warm setup, no GPU, model, or public network.
- Port rule: concurrent same-node jobs require distinct configured ports.
- Authentication: loopback may be unauthenticated; non-loopback use requires a
  bearer token supplied outside manifests and artifacts.
- Success: both paired runs discover a peer, read at least one staged peer
  record over MCP, publish a final local result, and complete.

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
