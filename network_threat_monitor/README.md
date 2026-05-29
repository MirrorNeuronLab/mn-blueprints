# Network Threat Monitor

`Blueprint ID:` `network_threat_monitor`

This generated blueprint monitors network events, scores suspicious spamware/malware/hack behavior, and writes a dry-run alarm artifact for human review.

## How To Run

```bash
cd mn-blueprints/network_threat_monitor
python3 payloads/network_monitor/scripts/run_blueprint.py \
  --events inputs/sample_network_events.jsonl \
  --runs-root /tmp/mirror-neuron-runs
```

The runner writes `run.json`, `config.json`, `inputs.json`, `events.jsonl`, `result.json`, and `final_artifact.json` under the selected run root.

## Safety

This blueprint does not block traffic, isolate hosts, change firewall policy, or disable accounts. It produces decision-support artifacts and requires human approval before any real response action.

## Reference Blueprints

- `user_activity_rmf_triage`
- `ai_audit_readiness`
- `facility_safety_video_monitor`

## Selected Agents

- `mn-agents.control_lifecycle`
- `mn-agents.control_router`
- `mn-agents.control_output_fanout`
- `mn-agents.control_input_listener`
- `mn-agents.data_observer`
- `mn-agents.control_approval_gate`
- `mn-agents.data_python_executor`
- `mn-agents.control_join`
- `mn-agents.data_module`

## Selected Skills

- `blueprint_support_skill`
- `email_delivery_skill`
