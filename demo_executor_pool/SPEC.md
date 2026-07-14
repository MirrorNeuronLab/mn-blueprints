# Specification: Executor Pool

- Blueprint id: `demo_executor_pool`
- Standard: `1.0`
- Primary runtime feature: `Executor lease capacity`
- Scenario: Run four logical workers through a two-slot executor pool.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
