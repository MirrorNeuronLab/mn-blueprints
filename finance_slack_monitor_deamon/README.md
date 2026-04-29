# Slack Money Monitor Example

This is a long-lived, continuous MirrorNeuron workflow that monitors a Slack channel and responds to specific messages. 

## What it does

1. **`ingress` (Router)**: Starts the workflow by passing the initial target channel to the sensor.
2. **`slack_sensor` (Module)**: Schedules its own polling cycle from inside the agent and polls the `conversations.history` Slack API every 3 seconds using the `:httpc` Erlang built-in. It automatically resolves channel names (like `#claw`) to their internal Slack IDs and emits `slack_message` events when it receives new messages.
3. **`money_detector` (Module)**: Subscribes to the slack messages and runs a regex (`~r/\$\d+/`) to look for the "$" sign followed by numbers. If matched, it uses the Slack `chat.postMessage` API to post the reply: *"PLEASE NO TALK ABOUT MONEY"* back into the channel.

## How to run

To start the monitor:
```bash
SLACK_DEFAULT_CHANNEL="#claw" SLACK_BOT_TOKEN="<your slack bot oauth token>" ./run_monitor.sh
```
Or use the MirrorNeuron CLI directly from the project root:
```bash
SLACK_DEFAULT_CHANNEL="#claw" SLACK_BOT_TOKEN="<your slack bot oauth token>" ./mn run examples/finance_slack_monitor_daemon
```

## ⚠️ Important Note on Recovery (Duplicate Messages)

MirrorNeuron is designed for highly-reliable, fault-tolerant workflows. The `manifest.json` for this bundle is set to `"recovery_mode": "cluster_recover"`. 

This means that if you start the monitor and then forcefully stop it (e.g., using `Ctrl+C`), MirrorNeuron will save the "interrupted" job state in its local Redis database. The next time you start the runtime, the supervisor will **automatically resume** the old jobs. If you've started and stopped the monitor multiple times, you might end up with multiple instances running simultaneously, which causes duplicate Slack replies.

### How to clean up "ghost" jobs

If you start seeing duplicate messages, stop the runtime and purge the old job states from your Redis container:

```bash
docker exec mirror-neuron-redis redis-cli keys "mirror_neuron:job:slack_money_monitor_*" | xargs -I {} docker exec mirror-neuron-redis redis-cli del {}
```

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

