#!/usr/bin/env python3
import json
import os
import sys

def main():
    print("Welcome to the Business Email Campaign Settings Setup!")
    print("This will configure your blueprint to use Ollama and AgentMail.")
    print("-" * 50)

    # Defaults
    default_llm_base = "http://localhost:11434"
    default_llm_model = "ollama/gemma4:latest"
    default_test_email = "test@example.com"
    default_agentmail_inbox = "mn-demo@agentmail.to"
    default_agentmail_api = ""
    default_resend_from = ""

    # Prompts
    llm_base = input(f"Ollama API Base URL [{default_llm_base}]: ").strip() or default_llm_base
    llm_base = llm_base.rstrip("/")
    for suffix in ("/v1/chat/completions", "/v1"):
        if llm_base.endswith(suffix):
            llm_base = llm_base[: -len(suffix)]
    llm_model = input(f"Ollama Model [{default_llm_model}]: ").strip() or default_llm_model
    
    agentmail_inbox = input(f"AgentMail Inbox [{default_agentmail_inbox}]: ").strip() or default_agentmail_inbox
    agentmail_key = input(f"AgentMail API Key [{default_agentmail_api}]: ").strip() or default_agentmail_api
    resend_key = input("Resend API Key (optional, used by email_send_resend_skill) []: ").strip()
    resend_from = input(f"Resend From Email (optional) [{default_resend_from}]: ").strip() or default_resend_from

    test_mode = input("Enable Quick Test Mode? (Dry-runs email delivery every 1 minute) [Y/n]: ").strip().lower()
    is_test_mode = test_mode in ["", "y", "yes", "true"]
    
    test_email = ""
    if is_test_mode:
        test_email = input(f"Test Email Address [{default_test_email}]: ").strip() or default_test_email

    print("-" * 50)
    print("Updating manifest.json...")

    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Update nodes
    for node in manifest.get("nodes", []):
        if "config" in node and "environment" in node["config"]:
            env = node["config"]["environment"]
            
            # Update LLM Settings
            env["LITELLM_API_BASE"] = llm_base
            env["LITELLM_MODEL"] = llm_model
            env["PRIMARY_LITELLM_API_BASE"] = llm_base
            env["PRIMARY_LITELLM_MODEL"] = llm_model
            env["SECONDARY_LITELLM_API_BASE"] = llm_base
            env["SECONDARY_LITELLM_MODEL"] = llm_model
            env["TERTIARY_LITELLM_API_BASE"] = llm_base
            env["TERTIARY_LITELLM_MODEL"] = llm_model
            
            # Update AgentMail Settings
            env["AGENTMAIL_API_KEY"] = agentmail_key
            env["AGENTMAIL_INBOX"] = agentmail_inbox
            env["RESEND_API_KEY"] = resend_key
            env["RESEND_FROM_EMAIL"] = resend_from
            
            if "GMAIL_ADDRESS" in env:
                del env["GMAIL_ADDRESS"]
            if "GMAIL_APP_PASSWORD" in env:
                del env["GMAIL_APP_PASSWORD"]
            if "GMAIL_SENDER_NAME" in env:
                del env["GMAIL_SENDER_NAME"]
            
            # Update Test Mode
            if is_test_mode:
                env["SYNAPTIC_TEST_EMAIL_TO"] = test_email
                env["SYNAPTIC_EMAIL_DELIVERY_MODE"] = "dry_run"
            else:
                env["SYNAPTIC_TEST_EMAIL_TO"] = ""
                env["SYNAPTIC_EMAIL_DELIVERY_MODE"] = "agentmail"

    for node in manifest.get("nodes", []):
        if node.get("node_id") == "monitor_scheduler_agent":
            node.setdefault("config", {})["interval_ms"] = 60000 if is_test_mode else 300000

    # Mark as configured
    if "require_config" in manifest:
        manifest["require_config"] = False

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("Success! The blueprint is now configured.")
    print("You can run it using: mn run mn-blueprints/business_email_campaign_deamon")

if __name__ == "__main__":
    main()
