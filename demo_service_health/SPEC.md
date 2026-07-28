# Specification: Service Health

- Blueprint id: `demo_service_health`
- Standard: `1.0`
- Primary runtime feature: `Service registration and health`
- Scenario: Register and resolve a tiny HTTP health service.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Port isolation: the HTTP listener and runtime service check share the
  configurable `service.port`; test runners must reserve a free port per run.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
