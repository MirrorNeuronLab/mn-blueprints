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

## Documentation map

- [SPEC.md](SPEC.md): behavior contract, customer outcome, input/output contract, evaluation criteria, and upgrade path.
- [manifest.json](manifest.json): graph, agents, edges, metadata, interface channels, and output contract.
- [config/default.json](config/default.json): default identity, inputs, simulation, LLM, outputs, logging, resources, web UI, and adapters.
- [config/overwrite.json](config/overwrite.json): local override template layered on top of the default config.
- [../BLUEPRINT_STANDARD.md](../BLUEPRINT_STANDARD.md): shared input, output, web UI, logging, resources, and artifact standards.
- [../README.md](../README.md): root catalog, run instructions, and repository structure.
- `payloads/`: worker code, fixtures, policies, or support assets used by the blueprint.
