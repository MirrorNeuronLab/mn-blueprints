# Specification: DAG Failure Fallback

- Blueprint id: `demo_dag_failure_fallback`
- Standard: `1.0`
- Primary runtime feature: `Failure-triggered fallback`
- Scenario: Fail a primary lookup and recover through a fallback step.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
