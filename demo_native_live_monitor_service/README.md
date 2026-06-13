# Demo: Native Live Monitor Service

`Blueprint ID:` `demo_native_live_monitor_service`
`Category:` `Engineering`

Use this blueprint to run a lightweight native monitor that keeps producing decisions over live state until you stop it.

## What It Does

This folder is a self-contained MirrorNeuron blueprint. It defines the runtime
manifest, default configuration, payload code, local documentation, and any
fixtures needed to review or run the workflow from this checkout.

## Quick Start

Run from the catalog:

```bash
mn run demo_native_live_monitor_service
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

Run this blueprint to turn a repeatable operational decision into an auditable MirrorNeuron workflow with clear inputs, outputs, and runtime artifacts.

## What it is

This blueprint is a workflow-first package with manifest metadata, runtime bindings, payload assets, configuration, and local documentation for running the scenario from this checkout.

## Who this is for

It is for teams that need a coordinated workflow rather than a static dashboard or a one-shot LLM answer.

## Why it matters

The workflow helps replace manual handoffs with observable steps, durable artifacts, and checks that can be reviewed after each run.

## Why this runtime is useful here

MirrorNeuron separates input resolution, worker execution, and final artifact writing so the run can be monitored, replayed, and inspected without hiding decisions inside one prompt.

## How it works

The input adapter resolves mock, JSON, file, or environment-provided inputs. The runtime executes the workflow workers declared in `manifest.json`, records events, and writes the final result to the local run store.

## Example scenario

An evaluator runs the blueprint with sample inputs, reviews the generated result, checks the event stream, and compares the workflow output against the expected decision or simulation outcome.

## How to run

Run from the catalog with `mn run demo_native_live_monitor_service` or from this folder with `mn run --folder .`.

## How to customize it

Adjust `config/default.json` for reusable defaults, use `config/overwrite.json` for local overrides, and update payload code or prompts when changing worker behavior.

## What to look for in results

Check that the output matches the input scenario, that the event log shows the expected workflow progression, and that warnings or uncertainty notes are easy to trace.

## Investor and evaluator narrative

This blueprint shows how MirrorNeuron can replace brittle scripts, static dashboards, and one-shot LLM workflows with a packaged runtime contract that produces inspectable results.

## Runtime features demonstrated

The blueprint demonstrates workflow-first manifests, input and output contracts, runtime worker bindings, local run-store artifacts, and service registration metadata.

## Test coverage

Catalog tests validate manifest shape, documentation standards, scenario fixtures, bundle generation, and compatibility with the shared blueprint support tooling.

## Limitations

Sample inputs and local fixtures are intended for evaluation. Live data, credentials, and external services should be configured deliberately before production use.

## Next steps

Tune the scenario inputs, connect approved live services, and add domain-specific assertions or review gates for production workflows.
