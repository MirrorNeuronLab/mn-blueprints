# Business Email Campaign Daemon

This is a long-lived, continuous MirrorNeuron workflow that acts as a personalized email marketing engine. It dynamically monitors customer data and orchestrates a series of specialized AI agents to plan, write, design, review, and send personalized emails using AgentMail and Ollama.

This is a demonstration  that sends newsletters every 5 minutes and reponse customers' replies asap. You can adapt it to run your own email campaigns.

This blueprint needs to run ollama locally, and an API key of agentmail. Please get one free at [https://www.agentmail.to](https://www.agentmail.to)

## What it does

This blueprint runs continuously in the background (`long_lived: true`) and processes two types of workflows:

1. **Scheduled Personalized Marketing**
   - Automatically polls the customer list (`input/manifest.json`) every 5 minutes (for fast demonstration).
   - Generates customized outreach emails using multiple specialized LLM agents (Research, Copywriting, Design, and Deliverability Review).
   - Supports 2 specific customer archetypes: a parent and a teacher.
   - Saves drafts and evaluates email quality before dispatching via your configured AgentMail account.

2. **Instant AI Email Replier**
   - Incorporates a continuous `inbox_reply_agent`.
   - Polls the configured AgentMail Inbox every 10 seconds.
   - Listens for **any** incoming emails regardless of the subject line.
   - If found, it reads the email body, generates an instant AI response using the local Ollama LLM, and emails the user back automatically.

## Requirements

- **AgentMail** API key (to send and receive emails via an AgentMail inbox).
- **Ollama** running locally or remotely, equipped with a compatible LLM (e.g., `gemma2` or `llama3`).

## How to Run

1. **Trigger the Run**
   From the project root:
   ```bash
   mn run mn-blueprints/business_email_campaign_deamon
   ```

2. **Auto-Configuration Wizard**
   Because this blueprint specifies `"require_config": true`, the CLI will automatically launch a configuration wizard the first time you run it. You will be prompted to enter:
   - Your Ollama API Base URL and Model
   - Your AgentMail Inbox address and API Key
   - Test mode override (if you want all emails to go to your test inbox)

3. **Monitor the Daemon**
   The job will detach into the background. You can stream the events and watch the agents interact by typing:
   ```bash
   mn monitor <job_id>
   ```

## Testing the Instant AI Reply

Once the daemon is running:
1. Send an email to the AgentMail address you configured during setup.
2. Provide any subject and body (e.g., "What are your opening hours?" or "Can you help me with my account?").
3. Wait roughly 10 seconds. You should receive a fully coherent AI-generated response from the daemon!

## Operations

### Status logging

Blueprint helper scripts and payloads report important running status as JSON lines on stderr. Each line includes `ts`, `level`, `blueprint`, `phase`, and `message`, with optional `details`. This keeps stdout reserved for bundle paths or machine-readable result JSON.

### Quick test mode

Use quick test mode for cheap logic validation before calling paid or slow external systems:

```bash
MN_BLUEPRINT_QUICK_TEST=1 python3 generate_bundle.py --quick-test
```

Generated blueprints shrink worker counts, durations, retries, and delays. LLM/email/API-facing paths use mock or dry-run providers where supported.

### Runtime DB seed

Fresh SQLite databases are bootstrapped from `input/data/bootstrap_seed.json`. The seed includes mock customer history, recent activities, ready drafts, and sent draft history so agents have enough context after deleting and recreating the DB. Ready seed drafts are rendered through the same `input/designs` templates used by `quick_preview_emails.py`, so runtime sends should match the colorful preview design instead of stale inline HTML. The runtime only loads this file when both `email_drafts` and `customer_marketing_activity` are empty.

### Test recipient mode

When `SYNAPTIC_TEST_EMAIL_TO` is set, all outbound emails are redirected to that address. To avoid one test inbox receiving the exact same job action twice, the marketing automation agent reserves each runtime job, cycle, customer, and campaign action for that test recipient. Duplicate test-mode actions emit `email_delivery_skipped` with `reason: duplicate_test_action` and do not continue that duplicate branch. Successful non-duplicate actions can emit `cycle_trigger` so the campaign sequence can advance through the planned funnel; failed, blocked, or waiting deliveries stop the loop. Test-recipient mode also stops after `SYNAPTIC_MAX_TEST_CYCLES` cycles, defaulting to 3, to avoid repeated sends to one inbox during debugging.

### Slack round reports

Set `SLACK_BOT_TOKEN` or `MIRROR_NEURON_SLACK_BOT_TOKEN` before running the blueprint to post delivery summaries to Slack. The non-secret channel env var `SLACK_DEFAULT_CHANNEL` is set to `#claw` in `manifest.json`; `MIRROR_NEURON_SLACK_DEFAULT_CHANNEL` can override it at runtime. Bot tokens are read from the runtime environment and are not stored in `manifest.json`. After every email delivery attempt, the marketing automation agent reports the current round totals: succeeded, failed, and attempted.

External calls made through the shared email and LLM skills are throttled by `mn_external_rate_limit_skill`. Override intervals with `MN_EXTERNAL_RATE_LIMIT_<KEY>_SECONDS`, set the shared state directory with `MN_EXTERNAL_RATE_LIMIT_STATE_DIR`, or disable throttling locally with `MN_EXTERNAL_RATE_LIMIT_DISABLED=1`.

### Output contract

CLI output is intentionally uniform:

- stderr: JSON status lines and ASCII progress bars such as `[########--------] 50% phase`.
- stdout: one bundle path, one JSON object, or MirrorNeuron event envelopes.
- events: typed objects with a `type` and `payload` field.

### Shared skills

Reusable helpers live in `mn-skills` instead of being reimplemented inside blueprints:

- `blueprint_support_skill`: logging, progress, quick-test, and manifest helpers.
- `marketing_email_skill`: generic draft normalization, CTA/footer, template rendering, and quality-check helpers.
- `email_delivery_skill`: dry-run/live email and Slack delivery wrappers.
- `litellm_communicate_skill`: shared LiteLLM-compatible text and JSON generation with local Ollama fallback.

Task-specific campaign strategy lives in this blueprint under `payloads/_shared_skills/business_email_campaign_skill`. That package contains the business audience segmentation, customer brief, offer selection, and template mapping used only by this campaign. Host-local agents upload that shared folder with their own payload so the blueprint works even when the system `python3` running the sandbox does not have any workspace packages installed.
