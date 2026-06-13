# Network Threat Response Assistant

`Blueprint ID:` `network_threat_response_assistant`
`Category:` `security`

This generated blueprint monitors network events, scores suspicious spamware/malware/hack behavior, and writes a dry-run alarm artifact for human review.

## What It Does

This folder is a self-contained MirrorNeuron blueprint. It defines the runtime
manifest, default configuration, payload code, local documentation, and any
fixtures needed to review or run the workflow from this checkout.

## Quick Start

Run from the catalog:

```bash
mn run network_threat_response_assistant
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

Monitor suspicious network events, score likely malware or intrusion behavior, and create a dry-run alarm artifact for human review.

## What it is

This blueprint is a network threat response assistant packaged as a MirrorNeuron workflow with sample network events, payload code, runtime metadata, and local validation tests.

## Who this is for

It is for security teams, platform operators, and evaluators who need a repeatable threat-triage workflow before wiring live response systems.

## Why it matters

Network alarms are noisy, and unsafe automation can overreact. This workflow keeps signal scoring, response recommendations, and required human approval visible.

## Why this runtime is useful here

MirrorNeuron records input resolution, actor execution, alarm decisions, artifacts, and events so reviewers can inspect why an alarm was raised before taking action.

## How it works

The threat monitoring actor reads network events, scores suspicious patterns, prepares an alarm decision, and writes a final artifact that requires human approval before response.

## Example scenario

A synthetic event stream includes suspicious traffic patterns; the assistant raises a high-risk alarm and records the evidence needed for a security reviewer.

## How to run

Run from the catalog with `mn run network_threat_response_assistant` or from this folder with `mn run --folder .`.

## How to customize it

Replace `inputs/sample_network_events.jsonl` with approved telemetry, tune scoring thresholds, and connect alerts or response systems only after policy review.

## What to look for in results

Check `final_artifact.json`, the alarm status, risk level, evidence fields, and whether the artifact clearly requires approval before response.

## Investor and evaluator narrative

This demonstrates how a security workflow can replace a static dashboard or one-shot LLM escalation with an auditable actor runtime that produces clear alarm evidence and controlled response boundaries.

## Runtime features demonstrated

The blueprint demonstrates actor-style workflow manifests, local input adapters, payload execution, final artifacts, event logs, and dry-run security response policy.

## Test coverage

Local tests verify that the sample network event stream triggers the expected alarm, risk level, approval requirement, and final artifact.

## Limitations

The sample detector is intentionally local and deterministic. Production use needs calibrated detections, telemetry validation, retention policy, and reviewed response playbooks.

## Next steps

Connect live telemetry adapters, add richer detection rules, add approval routing, and validate decisions against historical incident data.
