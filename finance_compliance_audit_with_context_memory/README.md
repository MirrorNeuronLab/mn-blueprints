# Financial Compliance Audit

This blueprint demonstrates the **Context Engineering Layer** applied to a complex financial compliance audit workflow.

## The Core Idea: Role-Based Isolation

In this multi-agent setup, we do *not* let every agent see everything. 
Instead, each agent receives a customized view of the common context via the Working Memory Context Engine. 
Each step converts noisy input into a cleaner artifact.

### The Pipeline
1. **Initializer**: Starts the workflow. Connects to the Context Engine, pushes a `RawTranscript` and a `PolicyDocument`, and emits a signal.
2. **Policy Interpreter**:
    * **Sees**: Only `PolicyDocument`. 
    * **Hidden from it**: The `RawTranscript`. (Prevents bending rules to fit the facts).
    * **Outputs**: `StructuredPolicy`.
3. **Evidence Extractor**:
    * **Sees**: Only `RawTranscript`.
    * **Hidden from it**: The `StructuredPolicy` and `FinalDecision`. (Behaves like a neutral court reporter).
    * **Outputs**: `StructuredEvidence`.
4. **Risk Classifier**:
    * **Sees**: `StructuredEvidence` and `StructuredPolicy`.
    * **Hidden from it**: `RawTranscript`. (Removes emotional noise and irrelevant complaints).
    * **Outputs**: `RiskAssessment`.
5. **Decision Agent**:
    * **Sees**: `RiskAssessment`, `StructuredPolicy`, and `StructuredEvidence`.
    * **Outputs**: `FinalDecision`.
6. **Critic / Auditor**:
    * **Sees**: `FinalDecision`, `StructuredEvidence`, `StructuredPolicy`, `RiskAssessment`.
    * **Outputs**: `AuditResult`.

## How It Works Technically

The `mn-context-engine` (written in Rust) handles the context projection.
Inside `src/core.rs`, the `get_context` function explicitly drops memory nodes that the requesting `agent_role` shouldn't see:

```rust
// Strict role-based isolation
if agent_role == "evidence_extractor" && !["RawTranscript", "Task"].contains(&item.item_type.as_str()) { continue; }
if agent_role == "policy_interpreter" && !["PolicyDocument", "Task"].contains(&item.item_type.as_str()) { continue; }
if agent_role == "risk_classifier" && !["StructuredEvidence", "StructuredPolicy", "Task"].contains(&item.item_type.as_str()) { continue; }
// ...
```

When an agent requests context, it only receives exactly what it needs to perform its specific duty.

## Running the Blueprint

1. Ensure the Context Engine is running:
   ```bash
   cd /Users/homer/Projects/Membrane/mn-context-engine
   cargo run --release
   ```

2. Validate the blueprint:
   ```bash
   mn validate finance_compliance_audit_with_context_memory
   ```

3. Run the blueprint:
   ```bash
   mn run financie_compliance_audit_with_context_memory
   ```
