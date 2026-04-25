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
    * **Outputs**: `audit_result` as a validated `Decision`, marks the final decision and task as used, and optionally snapshots context when `CONTEXT_REDIS_URL` or `redis_url` is provided.

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

When an agent requests context, the engine first filters by graph relevance, expiration, status, and ACL. It then projects the content fields allowed for that role. The scripts also use versioned lifecycle transitions, for example `draft -> validated`, `draft -> tested -> confirmed`, and `validated -> used`.

## Running the Blueprint

1. Ensure the Context Engine is running:
   ```bash
   cd /Users/homer/Projects/Membrane/mn-context-engine
   PROTOC=/Users/homer/.mirror_neuron/protoc_install/bin/protoc cargo run --release
   ```

2. Validate the blueprint:
   ```bash
   mn validate finance_compliance_audit_with_context_memory
   ```

3. Run the blueprint:
   ```bash
   mn run finance_compliance_audit_with_context_memory
   ```
