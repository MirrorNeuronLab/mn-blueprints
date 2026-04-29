# Divisibility Monitor Example

This is a simple long-lived MirrorNeuron workflow that keeps running until you stop it manually.

**Note:** This uses native agents for fast simulation.

## What it does

1. `question_generator` emits a new random divisibility question every 10 seconds.
2. `answer_agent` answers `yes` or `no` and logs the result.
3. The generator keeps a delayed self-schedule between cycles, so the job stays active without blocking the agent process.

## How to run

From the project root:

```bash
mn validate mn-blueprints/general_native_live_deamon
mn run mn-blueprints/general_native_live_deamon
```

If you want to watch the job after starting it:

```bash
mn monitor
mn job agents <job_id>
mn job events <job_id>
```

## Notes

- This example does not use OpenShell.
- It is intentionally open-ended, so there is no final result summary unless you manually cancel the job.
- It uses `local_restart` recovery, so old interrupted runs are not automatically resumed across fresh local CLI invocations.

## Operations

### Status logging

Blueprint helper scripts and payloads report important running status as JSON lines on stderr. Each line includes `ts`, `level`, `blueprint`, `phase`, and `message`, with optional `details`. This keeps stdout reserved for bundle paths or machine-readable result JSON.

### Quick test mode

Use quick test mode for cheap logic validation before calling paid or slow external systems:

```bash
MN_BLUEPRINT_QUICK_TEST=1 python3 generate_bundle.py --quick-test
```

Generated blueprints shrink worker counts, durations, retries, and delays. LLM/email/API-facing paths use mock or dry-run providers where supported.

### Output contract

CLI output is intentionally uniform:

- stderr: JSON status lines and ASCII progress bars such as `[########--------] 50% phase`.
- stdout: one bundle path, one JSON object, or MirrorNeuron event envelopes.
- events: typed objects with a `type` and `payload` field.

### Shared skills

Reusable helpers live in `mn-skills` instead of being reimplemented inside blueprints:

- `blueprint_support_skill`: logging, progress, quick-test, and manifest helpers.
- `marketing_email_skill`: deterministic customer segmentation, offer selection, and email rendering helpers.
- `email_delivery_skill`: dry-run/live email and Slack delivery wrappers.

