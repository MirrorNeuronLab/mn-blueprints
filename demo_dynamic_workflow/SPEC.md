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

## Blueprint package format

This blueprint uses the canonical blueprint/v1 format in both folders and ZIPs.
`manifest.json` contains identity, semantic release version, and document references.
`workflow.json` owns logical topology and policies; `execution.json` owns workers,
resources, and services; `contracts.json` owns input/output and artifact contracts.
Platform descriptors live in `extensions/`, package requirements in
`dependencies.json` when present, and operator defaults in `config/default.json`.
The SDK reads these documents together and compiles the Core execution artifact.
A ZIP contains the same files as the folder. Local overrides and invocation
configuration are resolved by the SDK before launch.
