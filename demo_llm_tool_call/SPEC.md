# Specification: LLM Tool Call

- Blueprint id: `demo_llm_tool_call`
- Standard: `1.0`
- Primary runtime feature: `LLM tool orchestration`
- Scenario: Use a deterministic fake model decision to call a local forecast tool.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
