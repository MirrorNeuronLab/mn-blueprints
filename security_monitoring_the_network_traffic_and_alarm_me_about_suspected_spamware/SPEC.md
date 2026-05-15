# Monitoring the network traffic and alarm me about suspected spamware SPEC

## Goal

Monitoring the network traffic and alarm me about suspected spamware or hack behavior.

## Customer Problem

Network telemetry, DNS events, endpoint labels, and authentication events are noisy. Operators need a small workflow that highlights suspicious behavior, explains which signals fired, and produces an alarm artifact without taking irreversible action.

## Inputs

- JSONL network flow events
- DNS events
- endpoint detection labels
- login or authentication events

## Output

The blueprint emits a security alarm artifact with risk level, risk score, triggered signals, source event IDs, and recommended next steps.

## Evaluation Criteria

- Suspicious sample events produce a high or critical alarm.
- Benign events do not trigger destructive recommendations.
- Every alarm traces back to source event IDs.
- Response actions remain dry-run unless explicitly approved outside the blueprint.

## Prototype Limits

The bundled runner is a deterministic mock implementation. It is suitable for local validation and blueprint review, not production packet capture or SIEM replacement.
