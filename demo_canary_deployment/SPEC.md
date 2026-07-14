# Specification: Canary Deployment

- Blueprint id: `demo_canary_deployment`
- Standard: `1.0`
- Primary runtime feature: `Canary promotion`
- Scenario: Promote a healthy candidate revision of a tiny service.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
