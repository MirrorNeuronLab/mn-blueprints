# General Openshell LLM Codegen

This blueprint demonstrates an advanced multi-agent workflow using MirrorNeuron and OpenShell to perform safe, iterative Large Language Model (LLM) code generation and validation.

## What it does

This workflow represents a complex self-improving loop:

1. **Iterative Generation and Review**: The pipeline executes three distinct rounds of code generation and review.
   - An LLM agent (`codegen`) writes Python code based on the initial requirements or previous reviews.
   - A secondary LLM agent (`review`) acts as a strict code reviewer, analyzing the generated code and providing concrete suggestions and identifying risks.
   - This creates an adversarial, multi-shot improvement process.
2. **Tool Creation**: The AI is tasked with solving an interesting problem that requires it to not just use standard libraries, but actually **build a new tool during runtime**. It dynamically generates a bash script to handle log filtering using standard Unix tools (`grep`/`awk`) and then executes it to assist its own Python logic.
3. **Isolated Sandbox Validation**: Finally, the `validator` node executes the LLM-generated code against test cases. Because LLM output is unpredictable and executing it directly on a host machine is dangerous, all nodes (including the LLM processing nodes and the final validator) run inside isolated **OpenShell Sandboxes**.
   - Network egress is explicitly restricted to only allow outbound traffic to Google's API endpoints via the `api-egress.yaml` policy.
   - The validation phase asserts that the dynamically generated helper bash script was created correctly, and that the code outputs the expected results.

## Why it's important

This blueprint showcases:
- **Safety**: Untrusted, LLM-generated code is executed inside a fully isolated OpenShell container, preventing host machine contamination.
- **Resilience**: The iterative review rounds give the LLM multiple chances to refine complex logic before it hits final validation.
- **Dynamic Capabilities**: It demonstrates the AI acting as a tool-maker, rather than just a tool-user, extending its own capabilities dynamically.

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

