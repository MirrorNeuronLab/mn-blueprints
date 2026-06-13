# User Activity RMF Triage Assistant

`Blueprint ID:` `user_activity_rmf_triage_assistant`
`Category:` `Security`

A local security worker that watches user activity, detects suspicious behavior, asks risky sessions to re-authenticate, and writes RMF/ATO/cATO-ready evidence artifacts.

## What It Does

This folder is a self-contained MirrorNeuron blueprint. It defines the runtime
manifest, default configuration, payload code, local documentation, and any
fixtures needed to review or run the workflow from this checkout.

## Quick Start

Run from the catalog:

```bash
mn run user_activity_rmf_triage_assistant
```

Run directly from this folder:

```bash
mn run --folder .
```

Inspect recent run state:

```bash
mn blueprint monitor --follow
```

## Inputs And Configuration

- `manifest.json`: graph shape, entrypoints, runtime metadata, runners, services, and environment access.
- `config/default.json`: default launch configuration and mock/sample input settings.
- `config/overwrite.json`: optional local overrides layered on defaults.
- `payloads/`: worker scripts, policies, fixtures, prompts, and support files used by this blueprint.

## Outputs

Most runs write artifacts under `~/.mn/runs/<run_id>/`. Common files include
`events.jsonl`, `result.json`, `final_artifact.json`, worker logs, and generated
reports when the blueprint produces them.

## Safety Checklist

- Review `manifest.json` and `payloads/` before running with real data.
- Check `pass_env`, provider credentials, Slack/email/web adapters, and any shell or OpenShell runners.
- Start with mock, dry-run, or quick-test configuration before live external integrations.
- Keep local customer overrides out of committed defaults.

## Local Documentation

- [SPEC](SPEC.md)
- [TERM](TERM.md)
- [License](LICENSE.md)

- [Manifest](manifest.json)
- [Default config](config/default.json)

## Validation

Run repository-level tests from `mn-blueprints` after changing catalog metadata,
manifest structure, payload behavior, or shared fixtures:

```bash
cd ..
python3.11 -m pytest -q
```

## One-line value proposition

Review suspicious user activity, recommend safe step-up authentication, and produce RMF/ATO/cATO evidence artifacts.

## What it is

This blueprint is a security triage assistant packaged as a MirrorNeuron workflow with actor-style runtime metadata, deterministic scoring code, sample events, and reviewable output artifacts.

## Who this is for

It is for SaaS, GovTech, defense-tech, compliance, and platform teams that need user-activity decisions to be inspectable before any live response is taken.

## Why it matters

Identity events often require fast action, but response steps such as session revocation or step-up authentication still need evidence, policy context, and auditability.

## Why this runtime is useful here

MirrorNeuron keeps event loading, risk scoring, response choice, and artifact writing observable through run-store events and a final artifact instead of hiding the decision in a one-off script.

## How it works

The RMF triage analyst actor normalizes sample activity events, scores risk signals, builds a triage state, chooses a dry-run response policy, and writes decision and evidence artifacts.

## Example scenario

A high-risk event stream includes a new-location login, a new device, API-key creation, and a large data download; the assistant recommends step-up authentication and records candidate compliance mappings.

## How to run

Run from the catalog with `mn run user_activity_rmf_triage_assistant` or from this folder with `mn run --folder .`.

## How to customize it

Replace the sample JSONL input with identity provider, SaaS audit, GitHub audit, CloudTrail, or application activity streams, then tune thresholds and response policy in configuration.

## What to look for in results

Review `security_decision.json`, `evidence_report.json`, `incident_summary.md`, and the run-store event log for risk signals, caveats, and dry-run response instructions.

## Investor and evaluator narrative

This shows how MirrorNeuron can replace a static dashboard or one-shot LLM security review with a repeatable assistant workflow that keeps evidence, human-control boundaries, and production-ready audit hooks visible.

## Runtime features demonstrated

The blueprint demonstrates actor-style workflow manifests, event normalization, deterministic risk scoring, human-control policy, artifact records, and run-store observability.

## Test coverage

Local tests cover normalization, high-risk scoring, report writing, and end-to-end worker execution.

## Limitations

The included mappings are candidate evidence artifacts and do not prove compliance or authorize live external action without customer-specific policy review.

## Next steps

Connect real event adapters, add organization-specific controls, calibrate thresholds on historical incidents, and wire approved response systems behind a human gate.
