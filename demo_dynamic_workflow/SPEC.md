# Specification: Dynamic Workflow

- Blueprint id: `demo_dynamic_workflow`
- Standard: `1.0`
- Primary runtime feature: `Bounded dynamic DAG patching`
- Fixed path: `inspect_context → write_report`
- Adaptive region: `research_followups` using `replace_path`
- Templates: `followup_research` and `verify_evidence`
- Default: apply patch `evidence-gap-1` and execute both inserted instances
- Override: `inputs.payload.evidence_gap=false` retains the fixed direct path
- Output: deterministic final artifact and standard local run-store artifacts
- Runtime budget: 20 seconds after warm setup, no GPU, model, or network
- Success: validation passes; default revision is `1`; verified evidence and the
  sanitized applied-patch event are present; no-gap revision is `0`
