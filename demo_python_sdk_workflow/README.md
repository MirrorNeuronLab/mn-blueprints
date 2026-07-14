# Python SDK Workflow

Demonstrates one MirrorNeuron feature: **Python SDK compilation**.

Compile and run a decorated two-agent incident workflow. The checked-in
manifest is a catalog preview; the test below compiles a fresh temporary bundle
and executes that generated bundle.

## Quick test

```bash
python compile_demo.py /tmp/mn-python-sdk-demo
mn blueprint validate /tmp/mn-python-sdk-demo
mn blueprint run --folder /tmp/mn-python-sdk-demo --offline --fake-llm
```

Default inputs are deterministic and require no GPU, external API, downloaded model, or connector account. Use `config/default.json` to select the `json`, `file`, or `env_json` adapter.

## Expected evidence

The run finishes with `final_artifact.json` plus the standard run-store lifecycle, error, timeline, and observability artifacts. Inspect `workflow_state` and `events.jsonl` for the feature-specific runtime evidence.
