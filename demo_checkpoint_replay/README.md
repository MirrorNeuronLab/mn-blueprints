# Checkpoint Replay

Demonstrates one MirrorNeuron feature: **Checkpoint resume**.

Checkpoint processed event IDs and ignore replayed duplicates.

## Quick test

```bash
mn blueprint validate .
mn blueprint run --folder . --offline --fake-llm
```

Default inputs are deterministic and require no GPU, external API, downloaded model, or connector account. Use `config/default.json` to select the `json`, `file`, or `env_json` adapter.

## Expected evidence

The run finishes with `final_artifact.json` plus the standard run-store
lifecycle, error, timeline, and observability artifacts. The terminal
checkpoint summary records the persisted executor state and the number of
replayed duplicates ignored, so the evidence remains durable after output
copy-back.
