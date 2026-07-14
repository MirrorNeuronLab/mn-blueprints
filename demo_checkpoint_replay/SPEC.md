# Specification: Checkpoint Replay

- Blueprint id: `demo_checkpoint_replay`
- Standard: `1.0`
- Primary runtime feature: `Checkpoint resume`
- Scenario: Checkpoint processed event IDs and ignore replayed duplicates.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
