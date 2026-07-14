# Specification: Python SDK Workflow

- Blueprint id: `demo_python_sdk_workflow`
- Standard: `1.0`
- Primary runtime feature: `Python SDK compilation`
- Scenario: Compile and run a decorated two-agent incident workflow.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
