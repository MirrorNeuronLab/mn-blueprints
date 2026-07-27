# Specification: MCP Job Collaboration

- Blueprint id: `demo_mcp_collaboration`
- Standard: `1.0`
- Primary runtime feature: cross-job MCP collaboration
- Scenario: two separately launched jobs share one goal, expose one MCP server
  each, discover each other through runtime service registration, and exchange
  job status, knowledge, staged results, and final results.
- Storage: one bounded job-scoped SQLite exchange per run.
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
