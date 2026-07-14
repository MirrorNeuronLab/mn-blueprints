# Context Compression

Demonstrates one MirrorNeuron feature: **CompileContext compression**.

Compress a context packet while preserving goals and source references.

## Quick test

```bash
mn blueprint validate .
mn blueprint run --folder . --offline --fake-llm
```

Default inputs are deterministic and require no GPU, external API, downloaded model, or connector account. Use `config/default.json` to select the `json`, `file`, or `env_json` adapter.

## Expected evidence

The run finishes with `final_artifact.json` plus the standard run-store lifecycle, error, timeline, and observability artifacts. Inspect `workflow_state` and `events.jsonl` for the feature-specific runtime evidence.
