# Security RMF User Activity Response Worker

`Blueprint ID:` `secuirty_rmf_user_activity`  
`Spec name:` `security_user_activity_response_worker`  
`Base blueprint:` `general_event_stream_triage_state_machine`  
`Default mode:` dry run

## One-line value proposition

A local security worker that watches user activity, detects suspicious behavior, asks risky sessions to re-authenticate, and writes RMF/ATO/cATO-ready evidence artifacts.

## What it is

This blueprint implements the v1 worker described in [SPEC.md](SPEC.md). It reads JSON or JSONL user activity events, normalizes them into a common schema, scores deterministic risk signals, updates a simple user/session triage state, chooses safe response actions, and writes structured evidence artifacts.

The worker is local-first and dry-run by default. It outputs response instructions such as `step_up_authentication_required` instead of directly changing identity-provider state.

## Who this is for

Small security-conscious teams, GovTech and defense-tech startups, regulated SaaS teams, compliance consultants, and internal platform/security teams that need repeatable evidence from real user activity.

## Why it matters

User activity can turn risky quickly: a new device, a new location, API key creation, MFA changes, and large data movement are more meaningful together than alone. A static dashboard can show each event, and a one-shot LLM can summarize a log slice, but neither maintains state or produces an audit-ready decision trail by default.

This blueprint turns those events into a risk decision, a safe response instruction, and candidate evidence mappings for compliance review.

## Why this runtime is useful here

MirrorNeuron is useful here because suspicious activity is a stateful event-stream problem. The base state-machine pattern groups events by user and session, tracks risk pressure over time, and keeps every decision tied to source events. That makes the result easier to review than an isolated alert or free-form summary.

## How it works

1. Load JSON or JSONL user activity events.
2. Normalize each event into the v1 event schema.
3. Score deterministic risk signals with configurable weights.
4. Maintain a triage state for the user/session under review.
5. Map the risk level to safe response actions.
6. Write `security_decision.json`, `evidence_report.json`, and `incident_summary.md`.

## Example scenario

Alice logs in from a known device with MFA, then a second session appears from a new location on an unknown device. That session creates an API key and downloads 800 files. The worker raises the session to high risk, recommends step-up authentication, and records the source events as candidate RMF/ATO/cATO evidence.

## Inputs

| Input | What it controls | Example | Can customize? |
|---|---|---|---|
| `--events` | JSON or JSONL activity file. | `inputs/sample_events_high_risk.jsonl` | Yes |
| `--config` | Risk thresholds, signal weights, response policy, and reporting options. | `config.example.json` | Yes |
| `--mode` | Overrides `dry_run` or future execution mode. | `dry_run` | Yes |
| `--output-dir` | Where report artifacts are written. | `outputs/` | Yes |

## Outputs

| Output | What it means |
|---|---|
| `security_decision.json` | Machine-readable risk score, risk level, signals, decision, and response instruction. |
| `evidence_report.json` | Detailed audit evidence with event IDs, candidate control-family mappings, and compliance caveat. |
| `incident_summary.md` | Human-readable report for security, compliance, or leadership review. |

## How to run

```bash
cd mn-blueprints/secuirty_rmf_user_activity
python3 src/main.py \
  --events inputs/sample_events_high_risk.jsonl \
  --config config.example.json \
  --output-dir outputs
```

Run the unit tests:

```bash
python3 -m pytest tests -q
```

## How to customize it

Replace the sample activity stream with your own IdP, application, audit-log, or SaaS events while preserving the normalized event shape. Tune `risk_thresholds`, `signal_weights`, and `response_policy` in `config.example.json`, then replace dry-run instructions with approved connectors after human approval and safety controls are in place.

## What to look for in results

Inspect the risk signals first, then the response instruction, then the evidence list. A useful run should show exactly which event IDs drove the score and should avoid unsupported compliance claims.

## Investor and evaluator narrative

This blueprint packages a concrete regulated-buyer workflow: continuous user-activity monitoring plus audit-ready evidence. It is intentionally narrow enough to be safe in v1, but it can grow into identity-provider connectors, GitHub/AWS audit-log ingestion, ticket creation, and continuous cATO monitoring.

## Runtime features demonstrated

- event stream normalization
- deterministic security risk scoring
- user/session triage state
- safe response policy
- dry-run execution mode
- candidate RMF/ATO/cATO evidence artifacts

## Test coverage

The included tests cover event normalization with missing optional fields, risk scoring for the high-risk sample, state transitions, high-risk response mapping, dry-run behavior, report generation, and the compliance caveat.

## Limitations

- This blueprint produces candidate evidence for compliance review. It does not grant RMF, ATO, cATO, FedRAMP, CMMC, or any other authorization by itself.
- The v1 worker does not replace a SIEM, SOC, identity provider, or incident response platform.
- External response actions are not executed in dry-run mode.
- Destructive actions such as account locking, global session revocation, permission removal, and API key revocation are reserved for future approved connectors.

## Next steps

- Connect a real activity source such as Okta, Auth0, Microsoft Entra ID, GitHub audit logs, or AWS CloudTrail.
- Add human approval gates for high-impact response actions.
- Add specific NIST SP 800-53 or SP 800-171 control mappings after compliance review.
- Run continuously through a daemon or scheduler once the event source and output review workflow are validated.

