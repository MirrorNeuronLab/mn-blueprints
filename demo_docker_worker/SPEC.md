# Specification: Docker Worker

- Blueprint id: `demo_docker_worker`
- Standard: `1.0`
- Primary runtime feature: `DockerWorker execution`
- Scenario: Compute and verify a checksum in a minimal Alpine container.
- Inputs: deterministic mock object; `json`, `file`, and `env_json` adapters are also supported.
- Output: compact JSON result and standard local run-store artifacts.
- Runtime budget: 20 seconds after warm setup, no GPU, and no public network dependency.
- Success: manifest validation passes, the runtime reaches the expected terminal state, and feature-specific events or allocation state are present.
