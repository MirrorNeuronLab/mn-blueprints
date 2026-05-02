# Financial Compliance Audit

This blueprint demonstrates the **Context Engineering Layer** applied to a complex financial compliance audit workflow.

## The Core Idea: Spec-Shaped Working Memory

In this multi-agent setup, we do *not* let every agent see everything.
Instead, each agent receives a customized view of the common context via the Working Memory Context Engine.
Each step converts noisy input into a cleaner artifact while preserving traceability through typed memory items, graph links, lifecycle states, confidence scores, and ACL-based projections.

The blueprint now uses the canonical memory types from `SPEC.md`:

- `Task`: the audit goal and workflow focus
- `Evidence`: raw transcript and structured evidence
- `Constraint`: policy document and structured policy
- `Hypothesis`: tested risk assessment
- `Decision`: final decision and critic audit result
- `Fact`: trace events for replay-style inspection

Domain labels such as `raw_transcript`, `structured_policy`, and `risk_assessment` live in `content.artifact_type`. This keeps the engine spec-compliant while still giving each agent precise domain context.

### The Pipeline
1. **Initializer**: Starts the workflow. Connects to the Context Engine, creates the audit `Task`, adds transcript `Evidence` and policy `Constraint`, links them, validates the task, and emits a signal.
2. **Policy Interpreter**:
    * **Sees**: Only the audit task and `policy_document` constraint.
    * **Hidden from it**: The `RawTranscript`. (Prevents bending rules to fit the facts).
    * **Outputs**: `structured_policy` as a validated `Constraint`.
3. **Evidence Extractor**:
    * **Sees**: Only the audit task and `raw_transcript` evidence.
    * **Hidden from it**: The `StructuredPolicy` and `FinalDecision`. (Behaves like a neutral court reporter).
    * **Outputs**: `structured_evidence` as validated `Evidence`.
4. **Risk Classifier**:
    * **Sees**: `structured_evidence` and `structured_policy`.
    * **Hidden from it**: `RawTranscript`. (Removes emotional noise and irrelevant complaints).
    * **Outputs**: `risk_assessment` as a tested `Hypothesis`.
5. **Decision Agent**:
    * **Sees**: `risk_assessment`, `structured_policy`, `structured_evidence`, and non-sensitive trace events.
    * **Outputs**: `final_decision` as a validated `Decision`, then confirms or rejects the risk hypothesis.
6. **Critic / Auditor**:
    * **Sees**: `final_decision`, `structured_evidence`, `structured_policy`, `risk_assessment`, and trace events.
    * **Outputs**: `audit_result` as a validated `Decision`, marks the final decision and task as used, and optionally snapshots context when `MN_CONTEXT_REDIS_URL`, `CONTEXT_REDIS_URL`, or `redis_url` is provided.

## How It Works Technically

The `mn-context-engine` (written in Rust) handles selective context.
Each memory item includes ACL projection metadata like this:

```json
{
  "goal_id": "audit_task_1",
  "artifact_type": "structured_evidence",
  "payload": {"evidence_items": []},
  "source_refs": ["transcript_1"],
  "acl": {
    "allow_roles": ["risk_classifier", "decision_agent", "critic_auditor"],
    "projections": {
      "risk_classifier": ["goal_id", "artifact_type", "payload", "source_refs", "validation"]
    }
  }
}
```

When an agent requests context, the engine first filters by graph relevance, expiration, status, and ACL. It then projects the content fields allowed for that role. Before each LLM-facing turn, agents also call `CompileContext` to receive the current Membrane runtime packet (`objective`, `hard_constraints`, `shared_state`, `retrieved_evidence`, `do_not_lose`, and compression trace) without mutating source memory. The scripts also use versioned lifecycle transitions, for example `draft -> validated`, `draft -> tested -> confirmed`, and `validated -> used`.

## Running the Blueprint

1. Ensure the Context Engine is running:
   ```bash
   cd /Users/homer/Projects/Membrane/mn-context-engine
   MN_CONTEXT_ADDR=127.0.0.1:50052 cargo run --release
   ```

   Agent payloads prefer the current Membrane environment names: `MN_CONTEXT_ADDR` and `MN_CONTEXT_REDIS_URL`. The older `CONTEXT_ENGINE_ADDR` and `CONTEXT_REDIS_URL` names are still accepted as aliases for local compatibility.
   Optional client-side compile request knobs are `MN_CONTEXT_PACKET_TOKEN_BUDGET`, `MN_CONTEXT_PACKET_TARGET_TOKENS`, and `MN_CONTEXT_USE_MODEL_COMPRESSION`.

2. Validate the blueprint:
   ```bash
   mn validate general_context_memory
   ```

3. Run the blueprint:
   ```bash
   mn run general_context_memory
   ```

## Operations

### Status logging

Blueprint helper scripts and payloads report important running status as JSON lines on stderr. Each line includes `ts`, `level`, `blueprint`, `phase`, and `message`, with optional `details`. This keeps stdout reserved for bundle paths or machine-readable result JSON.

### Agent context view logging

Each agent can also log the exact projected context it received from the Context Engine. This uses Python's standard `logging` package with JSON formatting, so it works locally and can later be routed to cloud handlers such as AWS CloudWatch (`watchtower`), Google Cloud Logging (`google-cloud-logging`), or OpenTelemetry without changing agent logic.

It is disabled by default. Enable it for diagnostic runs only:

```bash
MN_CONTEXT_VIEW_LOG=1 \
MN_CONTEXT_VIEW_LOG_DEST=stdout \
mn run general_context_memory
```

For local files with rotation:

```bash
MN_CONTEXT_VIEW_LOG=1 \
MN_CONTEXT_VIEW_LOG_DEST=file \
MN_CONTEXT_VIEW_LOG_FILE=/tmp/mn-context-agent/context_views.jsonl \
mn run general_context_memory
```

Supported destinations:

- `stdout`: JSON logs to stderr, useful for containers and cloud log collectors.
- `file`: rotating JSONL file via `logging.handlers.RotatingFileHandler`.
- `both`: writes to stderr and file.
- `cloud`: currently aliases stdout/stderr, ready for a future cloud logging handler.

Useful limits:

- `MN_CONTEXT_VIEW_LOG_MAX_BYTES`: file rotation size, default `10485760`.
- `MN_CONTEXT_VIEW_LOG_BACKUP_COUNT`: rotated file count, default `5`.
- `MN_CONTEXT_VIEW_LOG_LEVEL`: default `INFO`.

Each record has `event=agent_context_view`, `job_id`, `agent_role`, `focus_id`, `returned_count`, and the list of projected items. The helper strips `acl` before logging so debug output reflects agent-visible content.

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
