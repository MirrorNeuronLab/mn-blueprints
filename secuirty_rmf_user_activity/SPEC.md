# SPEC.md — `security_user_activity_response_worker`

## 1. Blueprint Summary

**Blueprint name:** `security_user_activity_response_worker`

**Base blueprint:** `general_event_stream_triage_state_machine`

**Purpose:**

Build a MirrorNeuron blueprint that monitors user activity events, detects suspicious behavior, triggers a safe step-up authentication response, and produces RMF/ATO/cATO-ready evidence artifacts.

The first version should focus on a simple but valuable security workflow:

> Detect suspicious user activity → report the finding → ask the user to log in again → preserve an audit-ready evidence trail.

This blueprint is not intended to replace a SIEM, identity provider, SOC, or full incident-response platform. It is an on-edge AI security worker that performs continuous user-activity triage and creates structured security evidence.

---

## 2. Product Positioning

### One-line description

A local AI security worker that watches user activity, detects suspicious behavior, asks risky sessions to re-authenticate, and writes RMF/ATO/cATO-ready evidence.

### Target users

- Small teams selling into government, defense, aerospace, or regulated industries
- GovTech / defense-tech startups preparing for RMF, ATO, cATO, FedRAMP, or CMMC conversations
- Security-conscious SaaS teams without a full SOC
- Compliance consultants who need repeatable evidence from real security activity
- Internal platform/security teams that want lightweight continuous monitoring artifacts

### Core value

The worker turns live user activity into:

1. A security decision
2. A safe response action
3. A structured audit artifact
4. A reusable compliance evidence record

---

## 3. Scope

### In scope for v1

The v1 blueprint should support:

- Reading a stream or batch of user activity events
- Normalizing those events into a common schema
- Scoring suspicious activity
- Maintaining a simple risk state per user/session
- Choosing one of a small set of safe actions
- Producing a structured incident/evidence report
- Supporting dry-run mode before executing real response actions
- Generating JSON and Markdown output artifacts

### Out of scope for v1

The v1 blueprint should not attempt to:

- Replace an enterprise SIEM
- Automatically lock or delete accounts
- Automatically terminate all sessions without human approval
- Perform forensic investigation
- Make final ATO authorization decisions
- Claim full RMF, FedRAMP, CMMC, or cATO compliance by itself
- Integrate with every identity provider on day one

---

## 4. Primary Use Case

### Scenario

A user logs in from New York. Shortly afterward, the same account logs in from a distant region, creates an API key, disables MFA, or downloads an unusual amount of data.

The worker should:

1. Detect the abnormal pattern
2. Assign a risk level
3. Record the evidence
4. Ask the user to log in again if the risk is high enough
5. Produce an audit-ready report

### Example narrative

```text
User alice@example.com logs in successfully from New York.
Seven minutes later, the same account logs in from an unfamiliar IP range.
The account then creates a new API key and downloads 800 files.
The worker raises the account risk to HIGH.
The worker triggers step-up authentication by asking the user to log in again.
The worker writes an evidence report showing what happened, why it mattered, and what response was taken.
```

---

## 5. High-Level Workflow

```text
User activity events
    ↓
Normalize event stream
    ↓
Group by user / session / account
    ↓
Score suspicious behavior
    ↓
Update triage state
    ↓
Choose response action
    ↓
Execute or simulate response
    ↓
Generate RMF/ATO/cATO evidence artifact
```

---

## 6. Event Inputs

### Supported event types for v1

```text
login_success
login_failed
logout
new_device_login
new_location_login
impossible_travel
unusual_ip
mfa_disabled
mfa_challenge_failed
password_reset
role_change
permission_change
api_key_created
api_key_used
large_data_download
admin_action
session_refresh
sensitive_file_access
```

### Minimum event schema

Each event should normalize into this schema:

```json
{
  "event_id": "evt_001",
  "timestamp": "2026-05-11T14:30:00Z",
  "event_type": "login_success",
  "user_id": "user_123",
  "user_email": "alice@example.com",
  "session_id": "sess_abc",
  "source_ip": "203.0.113.10",
  "geo": {
    "country": "US",
    "region": "NY",
    "city": "New York"
  },
  "device_id": "device_001",
  "user_agent": "Mozilla/5.0",
  "resource": "web_app",
  "metadata": {
    "mfa_used": true,
    "auth_provider": "example_idp"
  }
}
```

### Input formats

The blueprint should support at least:

- JSON file input
- JSONL event stream input
- Synthetic demo events
- Optional HTTP webhook input in a later version

---

## 7. Risk Signals

The worker should detect risk signals from event patterns.

### v1 risk signals

| Signal | Description | Example |
|---|---|---|
| New device | User logs in from an unseen device | First login from unknown laptop |
| New location | User logs in from an unusual location | Normal location: NYC; new login: overseas |
| Impossible travel | Two logins are too far apart in too little time | NYC login, then Berlin login 10 minutes later |
| Repeated failures | Many failed logins before success | 12 failed logins, then success |
| MFA disabled | User disables MFA or changes MFA settings | `mfa_disabled` event |
| Sensitive action after risky login | Risky login followed by admin or data access | New IP then API key creation |
| Large download | User downloads unusually many files | 800 files in 10 minutes |
| Privilege change | User gains admin or elevated permission | role changed to admin |
| API key creation | User creates new credential | new long-lived API token |
| Unusual activity rate | Event volume is much higher than baseline | 20x normal request rate |

---

## 8. Risk Scoring

### Risk levels

```text
LOW
MEDIUM
HIGH
CRITICAL
```

### Suggested scoring rules for v1

The v1 scoring system should be simple, transparent, and configurable.

Example scoring:

| Signal | Points |
|---|---:|
| New device login | +15 |
| New location login | +15 |
| Impossible travel | +40 |
| Repeated failed logins | +20 |
| MFA disabled | +40 |
| API key created after risky login | +25 |
| Large data download | +30 |
| Privilege change | +35 |
| Sensitive file access after risky login | +25 |
| Known safe device | -10 |
| MFA success | -10 |

### Risk threshold defaults

| Score | Risk level |
|---:|---|
| 0–24 | LOW |
| 25–49 | MEDIUM |
| 50–79 | HIGH |
| 80+ | CRITICAL |

These thresholds should be configurable in `config.json`.

---

## 9. Triage State Machine

The blueprint should adapt the state-machine pattern from `general_event_stream_triage_state_machine`.

### State per user/session

```json
{
  "user_id": "user_123",
  "session_id": "sess_abc",
  "current_risk_score": 65,
  "current_risk_level": "HIGH",
  "open_signals": [
    "new_location_login",
    "api_key_created_after_risky_login"
  ],
  "last_action": "step_up_authentication_required",
  "last_updated": "2026-05-11T14:35:00Z"
}
```

### State transitions

| Current state | Trigger | Next state | Action |
|---|---|---|---|
| Normal | Low-risk event | Normal | Log only |
| Normal | Medium-risk signal | Watch | Notify or mark for review |
| Watch | More suspicious activity | High Risk | Require re-login |
| High Risk | Critical action detected | Critical | Require MFA + notify admin |
| High Risk | User successfully re-authenticates | Resolved | Close event with evidence |
| Critical | Human confirms incident | Incident | Create incident record |

---

## 10. Response Actions

The v1 blueprint should support safe response actions only.

### Action list

```text
log_only
notify_user
notify_admin
step_up_authentication_required
require_mfa_challenge
create_incident_ticket
human_review_required
```

### Default action policy

| Risk level | Default action |
|---|---|
| LOW | `log_only` |
| MEDIUM | `notify_admin` or `notify_user` |
| HIGH | `step_up_authentication_required` |
| CRITICAL | `require_mfa_challenge` + `notify_admin` + `create_incident_ticket` |

### Step-up authentication behavior

The first supported response should be:

```text
Ask the user to log in again before continuing.
```

The blueprint should output a response instruction, not directly force identity-provider changes unless a connector is configured.

Example response instruction:

```json
{
  "action": "step_up_authentication_required",
  "user_id": "user_123",
  "session_id": "sess_abc",
  "message": "We noticed unusual activity. Please log in again to continue.",
  "requires_mfa": true,
  "reason": "High-risk activity pattern detected"
}
```

---

## 11. Human Approval and Safety

### Dry-run mode

The blueprint must support dry-run mode.

In dry-run mode, the worker should:

- Detect suspicious activity
- Recommend actions
- Generate reports
- Not execute external response actions

### Human approval mode

For high-impact actions, the worker should support human approval.

Actions requiring approval by default:

```text
account_lock
global_session_revocation
permission_removal
api_key_revocation
```

These actions are out of scope for v1 execution, but the spec should reserve room for them in future versions.

### Safety principle

The worker should prefer reversible, low-risk responses first:

```text
log → notify → step-up login → MFA challenge → human review
```

---

## 12. RMF/ATO/cATO Evidence Mapping

The blueprint should generate evidence that supports continuous monitoring, access control, audit logging, incident response, and risk management.

### Example control families

The output should support mapping to generic control families such as:

```text
Access Control
Identification and Authentication
Audit and Accountability
Incident Response
System and Communications Protection
Security Assessment and Authorization
Continuous Monitoring
Risk Assessment
```

### Important note

The blueprint should not claim that these mappings prove compliance. It should describe them as:

```text
candidate evidence mappings for compliance review
```

### Evidence artifact fields

```json
{
  "artifact_type": "security_user_activity_evidence_report",
  "generated_at": "2026-05-11T14:40:00Z",
  "user_id": "user_123",
  "session_id": "sess_abc",
  "risk_level": "HIGH",
  "risk_score": 65,
  "suspicious_activity": [
    "new_location_login",
    "api_key_created_after_risky_login",
    "large_data_download"
  ],
  "decision": "step_up_authentication_required",
  "response_taken": "user_asked_to_login_again",
  "evidence": [
    {
      "event_id": "evt_001",
      "event_type": "login_success",
      "timestamp": "2026-05-11T14:20:00Z"
    },
    {
      "event_id": "evt_002",
      "event_type": "api_key_created",
      "timestamp": "2026-05-11T14:28:00Z"
    }
  ],
  "candidate_control_mappings": [
    "Access Control",
    "Identification and Authentication",
    "Audit and Accountability",
    "Incident Response",
    "Continuous Monitoring"
  ],
  "human_review_required": false,
  "summary": "High-risk user activity detected. Step-up authentication was required."
}
```

---

## 13. Output Artifacts

The blueprint should produce three output files per run.

### 1. `security_decision.json`

Machine-readable decision output.

### 2. `evidence_report.json`

Detailed audit and compliance evidence artifact.

### 3. `incident_summary.md`

Human-readable report for security, compliance, or leadership review.

Example Markdown structure:

```markdown
# Suspicious User Activity Report

## Summary
High-risk user activity was detected for alice@example.com. The worker required the user to log in again.

## Risk Level
HIGH

## Suspicious Signals
- New location login
- API key created after risky login
- Large data download

## Response Taken
The user was asked to log in again with MFA.

## Evidence
- evt_001: login_success at 2026-05-11T14:20:00Z
- evt_002: api_key_created at 2026-05-11T14:28:00Z

## Candidate RMF/ATO/cATO Evidence Mapping
- Access Control
- Identification and Authentication
- Audit and Accountability
- Incident Response
- Continuous Monitoring

## Recommended Follow-up
Review API key usage and confirm whether the activity was legitimate.
```

---

## 14. Blueprint File Structure

Suggested directory structure:

```text
security_user_activity_response_worker/
  README.md
  SPEC.md
  manifest.json
  config.example.json
  inputs/
    sample_events.jsonl
    sample_events_high_risk.jsonl
  prompts/
    normalize_event.md
    risk_scorer.md
    triage_decision.md
    evidence_report_writer.md
  schemas/
    event.schema.json
    decision.schema.json
    evidence_report.schema.json
  src/
    main.py
    event_loader.py
    normalizer.py
    risk_scorer.py
    state_machine.py
    response_policy.py
    report_writer.py
  outputs/
    .gitkeep
  tests/
    test_risk_scorer.py
    test_state_machine.py
    test_response_policy.py
    test_report_writer.py
```

---

## 15. `manifest.json`

Example manifest:

```json
{
  "blueprint_id": "security_user_activity_response_worker",
  "name": "Security User Activity Response Worker",
  "version": "0.1.0",
  "description": "Detects suspicious user activity, recommends step-up authentication, and generates RMF/ATO/cATO-ready evidence artifacts.",
  "entrypoint": "src/main.py",
  "inputs": {
    "events": "inputs/sample_events.jsonl",
    "config": "config.example.json"
  },
  "outputs": {
    "security_decision": "outputs/security_decision.json",
    "evidence_report": "outputs/evidence_report.json",
    "incident_summary": "outputs/incident_summary.md"
  },
  "tags": [
    "security",
    "user-activity-monitoring",
    "continuous-monitoring",
    "rmf",
    "ato",
    "cato",
    "incident-response"
  ]
}
```

---

## 16. `config.example.json`

```json
{
  "mode": "dry_run",
  "risk_thresholds": {
    "low": 0,
    "medium": 25,
    "high": 50,
    "critical": 80
  },
  "signal_weights": {
    "new_device_login": 15,
    "new_location_login": 15,
    "impossible_travel": 40,
    "repeated_failed_logins": 20,
    "mfa_disabled": 40,
    "api_key_created_after_risky_login": 25,
    "large_data_download": 30,
    "privilege_change": 35,
    "sensitive_file_access_after_risky_login": 25,
    "known_safe_device": -10,
    "mfa_success": -10
  },
  "response_policy": {
    "low": ["log_only"],
    "medium": ["notify_admin"],
    "high": ["step_up_authentication_required"],
    "critical": ["require_mfa_challenge", "notify_admin", "create_incident_ticket"]
  },
  "require_human_approval_for": [
    "account_lock",
    "global_session_revocation",
    "permission_removal",
    "api_key_revocation"
  ],
  "reporting": {
    "write_json": true,
    "write_markdown": true,
    "include_candidate_control_mappings": true
  }
}
```

---

## 17. Agent/Module Responsibilities

### 1. Event Loader

Loads events from JSON or JSONL.

Responsibilities:

- Validate file exists
- Read events
- Preserve original event IDs
- Pass raw events to normalizer

### 2. Event Normalizer

Converts raw events into the standard event schema.

Responsibilities:

- Normalize timestamps
- Normalize event types
- Extract user/session/IP/device fields
- Preserve unknown metadata

### 3. Risk Scorer

Computes risk signals and risk score.

Responsibilities:

- Detect event-level risk signals
- Detect sequence-level patterns
- Apply configurable weights
- Return score and explanation

### 4. Triage State Machine

Maintains user/session risk state.

Responsibilities:

- Group events by user/session
- Update risk state over time
- Track open signals
- Track previous actions
- Mark resolved events

### 5. Response Policy Engine

Chooses response actions.

Responsibilities:

- Convert risk level into action
- Respect dry-run mode
- Require approval for high-impact actions
- Produce response instruction

### 6. Evidence Report Writer

Creates audit-ready artifacts.

Responsibilities:

- Write `security_decision.json`
- Write `evidence_report.json`
- Write `incident_summary.md`
- Include candidate RMF/ATO/cATO evidence mappings

---

## 18. Prompt Files

The blueprint may use LLM prompts for explanation and reporting, but the core risk scoring should remain deterministic and testable.

### `prompts/risk_scorer.md`

Purpose:

```text
Explain why the detected event pattern is suspicious using the provided deterministic signals and scores. Do not invent events or controls. Only use supplied evidence.
```

### `prompts/triage_decision.md`

Purpose:

```text
Summarize the triage decision. Explain the risk level, selected response action, and whether human review is required. Do not make final compliance claims.
```

### `prompts/evidence_report_writer.md`

Purpose:

```text
Generate a concise audit-ready report from the structured decision object. Include evidence, response taken, and candidate control mappings. Avoid unsupported claims.
```

---

## 19. Sample Input

`inputs/sample_events_high_risk.jsonl`

```jsonl
{"event_id":"evt_001","timestamp":"2026-05-11T14:00:00Z","event_type":"login_success","user_id":"user_123","user_email":"alice@example.com","session_id":"sess_001","source_ip":"198.51.100.10","geo":{"country":"US","region":"NY","city":"New York"},"device_id":"device_known","metadata":{"mfa_used":true}}
{"event_id":"evt_002","timestamp":"2026-05-11T14:08:00Z","event_type":"new_location_login","user_id":"user_123","user_email":"alice@example.com","session_id":"sess_002","source_ip":"203.0.113.55","geo":{"country":"DE","region":"BE","city":"Berlin"},"device_id":"device_unknown","metadata":{"mfa_used":false}}
{"event_id":"evt_003","timestamp":"2026-05-11T14:10:00Z","event_type":"api_key_created","user_id":"user_123","user_email":"alice@example.com","session_id":"sess_002","source_ip":"203.0.113.55","geo":{"country":"DE","region":"BE","city":"Berlin"},"device_id":"device_unknown","metadata":{"key_type":"long_lived"}}
{"event_id":"evt_004","timestamp":"2026-05-11T14:12:00Z","event_type":"large_data_download","user_id":"user_123","user_email":"alice@example.com","session_id":"sess_002","source_ip":"203.0.113.55","geo":{"country":"DE","region":"BE","city":"Berlin"},"device_id":"device_unknown","metadata":{"file_count":800}}
```

---

## 20. Expected Output Example

### `security_decision.json`

```json
{
  "user_id": "user_123",
  "user_email": "alice@example.com",
  "session_id": "sess_002",
  "risk_score": 70,
  "risk_level": "HIGH",
  "signals": [
    "new_location_login",
    "new_device_login",
    "api_key_created_after_risky_login",
    "large_data_download"
  ],
  "decision": "step_up_authentication_required",
  "response_instruction": {
    "message": "We noticed unusual activity. Please log in again to continue.",
    "requires_mfa": true
  },
  "human_review_required": false,
  "mode": "dry_run"
}
```

---

## 21. Tests

### Required unit tests

- Event normalization handles missing optional fields
- Risk scoring detects new location
- Risk scoring detects large download
- Risk scoring detects API key creation after risky login
- State machine upgrades from normal to high risk
- Response policy maps HIGH to step-up authentication
- Dry-run mode does not execute external action
- Evidence report includes all source event IDs
- Markdown report is generated

### Required integration test

Run the blueprint against `sample_events_high_risk.jsonl` and verify:

- Risk level is HIGH or CRITICAL
- Response is `step_up_authentication_required` or stronger
- Evidence report is generated
- Candidate control mappings are present
- Output does not claim formal compliance certification

---

## 22. Acceptance Criteria

The blueprint is complete when:

1. A developer can run the blueprint locally with sample events.
2. The worker detects suspicious user activity.
3. The worker recommends asking the user to log in again.
4. The worker outputs a machine-readable security decision.
5. The worker outputs an audit-ready evidence report.
6. The worker outputs a human-readable incident summary.
7. Dry-run mode is supported by default.
8. Risk thresholds are configurable.
9. Tests cover scoring, state transitions, response policy, and report generation.
10. The README clearly explains that this blueprint supports evidence generation but does not grant RMF/ATO/cATO compliance by itself.

---

## 23. Future Extensions

Possible v2 features:

- Identity provider connector: Okta, Auth0, Microsoft Entra ID, Google Workspace
- GitHub audit log connector
- AWS CloudTrail connector
- Slack or email notification connector
- Jira / Linear / GitHub Issues ticket creation
- Session revocation with human approval
- API key revocation with human approval
- User/entity behavior analytics baseline
- IP reputation integration
- Device trust integration
- Control mapping to specific NIST SP 800-53 or NIST SP 800-171 controls
- cATO dashboard output
- Continuous mode using MirrorNeuron daemon runtime

---

## 24. Recommended README Pitch

```text
# Security User Activity Response Worker

A MirrorNeuron blueprint for continuous user-activity monitoring and safe security response.

This worker watches user activity events, detects suspicious behavior, asks risky sessions to re-authenticate, and writes audit-ready evidence artifacts for RMF/ATO/cATO workflows.

It is designed for small teams that need practical security monitoring and compliance evidence without sending sensitive logs to a cloud-only AI service.
```

---

## 25. Design Principles

1. **Local-first:** Sensitive activity logs should be able to stay inside the user's environment.
2. **Safe by default:** Prefer re-authentication and notification before destructive actions.
3. **Evidence-first:** Every decision should cite the events that caused it.
4. **Deterministic core:** Risk scoring and state transitions should be testable without an LLM.
5. **LLM for explanation:** Use AI to summarize, explain, and draft reports, not to invent facts.
6. **Compliance-aware, not compliance-claiming:** Produce candidate evidence, not formal authorization.
7. **Continuous-ready:** Design the workflow so it can later run as a long-lived daemon.

