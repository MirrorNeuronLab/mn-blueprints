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
