# Context Memory Basic Blueprint

This blueprint demonstrates how to use the **Working Memory Context Engine** (`mn-context-engine`) inside a MirrorNeuron workflow.

## Overview

It consists of two Python workers orchestrated by MirrorNeuron, running inside isolated OpenShell sandboxes:

1.  **Planner Node (`planner.py`)**:
    *   Connects to the Context Engine gRPC server via `host.docker.internal:50052`.
    *   Creates a `Task` memory item (with a goal, priority, and hidden shell command).
    *   Creates a `Hypothesis` memory item.
    *   Links them together in the Working Memory Graph.
    *   Emits a message to trigger the Executor.

2.  **Executor Node (`executor.py`)**:
    *   Wakes up and calls `GetContext` on the Context Engine.
    *   Passes `agent_role="executor"` and `focus_id="task_001"`.
    *   *Magic happens*: The Context Engine filters out the `Hypothesis` (executors don't see hypotheses) and projects the `Task` JSON so the executor sees the exact shell command to run.
    *   Runs the shell command and adds a new `Fact` to the Context Engine containing the output.

## Prerequisites

1.  **Context Engine Running**: The Rust Context Engine must be running on your host machine.
    ```bash
    cd /Users/homer/Projects/Membrane/mn-context-engine
    cargo run --release
    ```

2.  **MirrorNeuron Runtime**: The main `MirrorNeuron` core must be active so `./mn run` works.

## How to Run

1. Validate the blueprint:
   ```bash
   mn validate general_context_memory_basic
   ```

2. Run the blueprint:
   ```bash
   mn run general_context_memory_basic
   ```

3. View events/results:
   ```bash
   mn events <job_id>
   ```

You will see that the Executor's output confirms it only received the `Task` in its context window, successfully executing the command extracted from the working memory graph!

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

