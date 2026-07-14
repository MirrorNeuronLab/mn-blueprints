# Specification: Context Memory ACL

- Blueprint id: `demo_context_memory_acl`
- Standard: `1.0`
- Primary runtime feature: `Context Engine role ACLs`
- Scenario: Prove that a restricted role cannot retrieve private memory.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
