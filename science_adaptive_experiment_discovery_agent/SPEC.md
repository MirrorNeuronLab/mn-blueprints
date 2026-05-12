# Adaptive Experiment Discovery Agent SPEC

## What We Want To Achieve

Build a reviewable scientific planning workflow that helps Lab researchers, R&D teams, computational scientists, and scientific AI builders move from raw signals to an explainable recommendation. Select the next lab experiment from prior simulated yield, toxicity, cost, and evidence confidence. The target customer should understand what changed, why the system recommended an action, and what evidence a human should review before acting.

## Customer Problem

Experiment planning is sequential; each result changes the next best experiment and the cost-risk tradeoff. In a real customer environment, the pain is not only producing an answer; it is preserving context across changing inputs, exposing tradeoffs, and creating an audit trail that business, technical, or governance stakeholders can trust.

## Design Details

The blueprint is organized as a MirrorNeuron workflow with stable identity, configurable inputs, structured events, and a final artifact. The main agent role is Experimental design scientist. The workflow uses iterative experiment outcome simulation and demonstrates iterative experiments, LLM scientist, optimization loop, and structured plan.

The design is intentionally adapter-friendly. The prototype can run with bundled, mock, or synthetic data even when the current code has not implemented every production integration. The customer-facing contract stays centered on the same concepts: load inputs, observe current state, choose or score an action, emit traceable events, and write an artifact a reviewer can inspect.

A representative scenario is: A synthetic enzyme candidate shows mixed yield and toxicity, and the scientist agent chooses pH refinement, temperature sweep, or catalyst switch.

## Input

The prototype accepts configuration for scenario identity, run controls, and domain inputs. Current adapters include `mock`, `json`, `file`, and `env_json`, so evaluators can start locally and later replace sample data with production data while preserving the same blueprint identity and output shape.

Important state inputs include `yield_pct`, `toxicity_score`, `experiment_cost`, and `evidence_confidence`. Where the blueprint uses an action loop, the current action space includes `explore_high_temp`, `refine_ph`, and `switch_catalyst`. For production use, the same contract should be fed by customer system-of-record data, business rules, approval policies, thresholds, and any regulated or safety-critical constraints needed for the operating environment.

## Output: Expected Customer Outcome

The expected customer outcome is experiment optimization plan with ranked experiment options. A useful run should show the starting context, the observations made during the workflow, the action or recommendation rationale, and the final artifact that a domain owner can review.

The customer should be able to answer: what happened, which inputs mattered, what the system recommended, what changed over time, what risks or exceptions remain, and what a human team should do next.

## Evaluation Criteria

- Decision quality: confirm the recommendation is plausible for the observed state, customer constraints, and available actions.
- Scenario sensitivity: verify that outputs change appropriately when inputs, thresholds, seed values, or operating assumptions change.
- State trajectory: inspect whether `yield_pct`, `toxicity_score`, `experiment_cost`, and `evidence_confidence` move coherently across the workflow rather than appearing as disconnected summaries.
- Traceability: confirm every recommendation can be tied back to inputs, events, intermediate decisions, and final artifact fields.
- Human review fit: check whether the artifact matches the language, evidence, and next-step format the target team already uses.
- Operational readiness: validate latency, reliability, adapter behavior, permissions, privacy, and approval gates before using real customer data.
- Outcome measurement: compare recommendations against historical cases, expert review, known policies, or measured business outcomes.

## Result Artifacts To Inspect

Inspect the event stream for observations, decisions, errors, and handoffs. Inspect the result payload and final artifact for the recommended action, ranked options or findings, supporting rationale, state changes, and next steps.

When using the local run store, inspect `run.json`, `config.json`, `inputs.json`, `events.jsonl`, `result.json`, and `final_artifact.json`. These artifacts are the review surface for debugging the workflow, comparing scenarios, and deciding whether the blueprint is ready for a real adapter.

## Prototype Limits

The current blueprint is a product-facing template and may include mock data, deterministic simulation, simplified policies, placeholder integrations, or partial worker coverage. It is designed to show the customer problem, target workflow, and expected artifact even where production implementation still needs hardening.

Outputs are decision-support artifacts. They should not be treated as final financial advice, medical guidance, safety certification, compliance approval, or executable operating instruction without customer validation and human approval.

## Upgrade Path To Real Customer Use

Replace synthetic outcomes with LIMS/ELN data, assay results, cost models, safety constraints, and Bayesian or active-learning tools. Add customer-specific policies, review gates, exception handling, retention rules, and monitoring dashboards. Calibrate the workflow against historical data and expert judgment, then track acceptance rate, correction rate, latency, incident reduction, cost impact, and other outcome metrics that prove whether the workflow is helping.

## Product Narrative

Adaptive experimentation is a high-value scientific workflow where closed-loop agents can shorten discovery cycles.
