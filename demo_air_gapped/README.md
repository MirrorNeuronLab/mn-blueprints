# Air-Gapped Blueprint Demo

This blueprint carries its own Python skill, two agent packages, worker code,
sample input, and a Gemma 4 E2B GGUF model. It is designed to demonstrate a
complete MirrorNeuron workflow with no network access after export.

## Contents

- `payloads/skills/demo_airgap_skill`: source-form skill package
- `payloads/agents/demo_airgap_analyzer_agent`: source-form analyzer agent
- `payloads/agents/demo_airgap_reporter_agent`: source-form reporter agent
- `payloads/models/gemma4-e2b`: model, multimodal projector, and model license
- `payloads/worker`: standard-library-only workflow worker and run-store writer
- `payloads/data/note.txt`: sample note

## Run

```bash
mn blueprint validate .
mn blueprint run --folder .
```

To prove a paused job can move to a disconnected machine:

```bash
mn job pause <job-id>
mn job backup <job-id> --air-gapped --output ./backups
mn job restore demo_air_gapped --input ./backups/<backup>.mn-airgap-backup.zip

# Or run the extracted capsule directly:
unzip ./backups/*mn-airgap-backup.zip -d ./restored
MN_OFFLINE=1 mn blueprint run --folder ./restored/bundle
```

The target machine must have the same operating-system/architecture family,
MirrorNeuron, Python, Docker Desktop, and Docker Model Runner installed. It
does not need internet access.

## Input

Set `MN_BLUEPRINT_INPUT_JSON` to replace the bundled note:

```bash
export MN_BLUEPRINT_INPUT_JSON='{"note":"A local operator saw elevated latency after a cache rollout."}'
```

## Expected result

The analyzer agent invokes the bundled Docker Model Runner model. The reporter
agent converts that response into `result.json` and `final_artifact.json` under
the normal MirrorNeuron run directory.
