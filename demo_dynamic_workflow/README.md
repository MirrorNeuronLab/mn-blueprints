# Dynamic Workflow

Demonstrates one MirrorNeuron feature: **bounded dynamic DAG patching**.

The fixed workflow is `inspect_context → write_report`. With the default input,
`inspect_context` finds an evidence gap and atomically replaces the direct edge
with:

```text
inspect_context → followup_research_1 → verify_evidence_1 → write_report
```

All dynamic work uses templates and workers admitted before the run. The demo
is deterministic, offline, and makes no model or network calls.

## Quick test

```bash
mn blueprint validate .
mn blueprint run --folder . --offline --fake-llm
```

To keep the original fixed path:

```bash
mn blueprint run --folder . --offline --fake-llm \
  --set inputs.payload.evidence_gap=false
```

## Expected evidence

The default `final_artifact.json` records graph revision `1`, patch id
`evidence-gap-1`, the two inserted steps, and verified evidence. Runtime events
include `workflow_graph_patch_applied`. The no-gap override records revision
`0`, no patch id, and no inserted steps.
