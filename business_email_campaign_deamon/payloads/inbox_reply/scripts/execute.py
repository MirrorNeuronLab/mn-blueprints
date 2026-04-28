#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

import sqlite3
from datetime import datetime, timezone

try:
    from mn_email_receive_agentmail_skill import AgentMailReceiveConfig
    from mn_email_receive_agentmail_skill import get_message as skill_get_message
    from mn_email_receive_agentmail_skill import list_unread_messages as skill_list_unread_messages
    from mn_email_receive_agentmail_skill import mark_read as skill_mark_read
    from mn_email_receive_agentmail_skill import send_reply as skill_send_reply
except ImportError:
    AgentMailReceiveConfig = None
    skill_get_message = None
    skill_list_unread_messages = None
    skill_mark_read = None
    skill_send_reply = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def log_customer_reply(from_email: str, body: str):
    db_path = "/tmp/mn_business_email_campaign.db"
    if not os.path.exists(db_path):
        return
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_marketing_activity (
                activity_id TEXT PRIMARY KEY,
                customer_id TEXT,
                summary TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_drafts (
                draft_id TEXT PRIMARY KEY,
                customer_id TEXT,
                runtime_job_id TEXT,
                status TEXT,
                subject TEXT,
                preview_text TEXT,
                body_text TEXT,
                html_body TEXT,
                scheduled_send_at TEXT,
                prepared_at TEXT,
                provider_id TEXT,
                sent_at TEXT,
                from_email TEXT,
                thread_message_id TEXT,
                in_reply_to_message_id TEXT,
                references_message_ids_json TEXT,
                source_payload_json TEXT
            )
            """
        )
        
        # Determine the customer id loosely based on the email we received
        if "davis" in from_email.lower():
            customer_id = "cust_mr_davis_teacher"
        elif "ava" in from_email.lower() or "martinez" in from_email.lower():
            customer_id = "cust_ava_repeat_creator"
        else:
            # Fallback to the last customer we emailed if we're testing via override
            row = conn.execute("SELECT customer_id FROM email_drafts WHERE status = 'sent' ORDER BY sent_at DESC LIMIT 1").fetchone()
            customer_id = row["customer_id"] if row else "cust_maya_new_parent"
            
        activity_id = f"activity_{utc_now().replace('-', '').replace(':', '').replace('+00:00', 'z').lower()}"
        summary = f"Customer replied: {body[:200]}"
        conn.execute(
            """
            INSERT INTO customer_marketing_activity (
                activity_id,
                customer_id,
                summary,
                created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (activity_id, customer_id, summary, utc_now()),
        )
        conn.commit()
        print(f"Logged reply activity for customer: {customer_id}", file=sys.stderr)
        conn.close()
    except Exception as e:
        print(f"Error logging reply to db: {e}", file=sys.stderr)


def generate_reply_via_llm(body_content):
    api_base = os.environ.get("LITELLM_API_BASE", "http://192.168.4.173:11434").rstrip("/")
    model = os.environ.get("LITELLM_MODEL", "ollama/gemma4:latest")
    for suffix in ("/v1/chat/completions", "/v1"):
        if api_base.endswith(suffix):
            api_base = api_base[: -len(suffix)]
    
    if "ollama" in model:
        url = f"{api_base}/api/chat"
        actual_model = model.replace("ollama/", "")
        payload = {
            "model": actual_model,
            "messages": [
                {"role": "system", "content": "You are a warm, helpful customer support representative for Bibblio, a company that makes personalized children's SEL (social-emotional learning) picture books. Keep your response friendly but concise (1-3 sentences max)."},
                {"role": "user", "content": f"Customer email body:\n{body_content}"}
            ],
            "stream": False
        }
    else:
        url = f"{api_base}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a warm, helpful customer support representative for Bibblio, a company that makes personalized children's SEL (social-emotional learning) picture books. Keep your response friendly but concise (1-3 sentences max)."},
                {"role": "user", "content": f"Customer email body:\n{body_content}"}
            ]
        }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res = json.loads(response.read().decode('utf-8'))
            if "message" in res:
                return res["message"]["content"]
            elif "choices" in res:
                return res["choices"][0]["message"]["content"]
            else:
                return "Thank you for reaching out. Your message has been received."
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        return "Thank you for your message. We have received it."

def agentmail_request(method: str, path: str, body: dict | None = None, query: dict | None = None) -> dict:
    api_key = os.environ.get("AGENTMAIL_API_KEY")
    if not api_key:
        return {}
    url = "https://api.agentmail.to" + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def check_agentmail() -> list:
    api_key = os.environ.get("AGENTMAIL_API_KEY")
    inbox_id = os.environ.get("AGENTMAIL_INBOX")
    if not api_key or not inbox_id:
        return []

    if (
        AgentMailReceiveConfig is not None
        and skill_get_message is not None
        and skill_list_unread_messages is not None
        and skill_mark_read is not None
        and skill_send_reply is not None
    ):
        return check_agentmail_with_skill()

    processed = []
    inbox_path = urllib.parse.quote(inbox_id, safe="")
    try:
        res = agentmail_request(
            "GET",
            f"/v0/inboxes/{inbox_path}/messages",
            query={"labels": ["unread"]},
        )
        messages = res.get("messages") or res.get("data") or []
        
        for msg in messages:
            subject = msg.get("subject") or ""
            
            # Respond to ALL incoming emails now
            from_email = msg.get("from") or msg.get("from_") or ""
            if not from_email:
                continue
                
            if "<" in from_email and ">" in from_email:
                from_email = from_email.split("<")[1].split(">")[0]
                
            if inbox_id in from_email:
                # Skip processing our own emails to prevent loops
                agentmail_request(
                    "PATCH",
                    f"/v0/inboxes/{inbox_path}/messages/{urllib.parse.quote(str(msg.get('message_id') or msg.get('id')), safe='')}",
                    body={"add_labels": ["read"], "remove_labels": ["unread"]},
                )
                continue
                
            # Fetch the full message to get the actual body content
            message_id = str(msg.get("message_id") or msg.get("id"))
            full_msg = agentmail_request(
                "GET",
                f"/v0/inboxes/{inbox_path}/messages/{urllib.parse.quote(message_id, safe='')}",
            )
            body = (
                full_msg.get("extracted_text")
                or full_msg.get("text")
                or msg.get("extracted_text")
                or msg.get("text")
                or "No content provided."
            )
            print(f"Processing email from {from_email}...")
            
            log_customer_reply(from_email, body)
            reply_text = generate_reply_via_llm(body)
            
            agentmail_request(
                "POST",
                f"/v0/inboxes/{inbox_path}/messages/send",
                body={"to": from_email, "subject": f"Re: {subject}", "text": reply_text},
            )
            # Mark as read so we don't process it again
            agentmail_request(
                "PATCH",
                f"/v0/inboxes/{inbox_path}/messages/{urllib.parse.quote(message_id, safe='')}",
                body={"add_labels": ["read"], "remove_labels": ["unread"]},
            )
            processed.append({
                "type": "agent_inbox_email_received",
                "payload": {
                    "from": from_email,
                    "subject": subject,
                    "body": body[:500]
                }
            })
            processed.append({
                "type": "agent_inbox_reply_sent",
                "payload": {
                    "to": from_email,
                    "subject": f"Re: {subject}",
                    "reply_text": reply_text
                }
            })
            
    except Exception as e:
        print(f"AgentMail Fetch/Reply Error: {e}", file=sys.stderr)
    return processed


def check_agentmail_with_skill() -> list:
    config = AgentMailReceiveConfig.from_env()
    processed = []
    try:
        for msg in skill_list_unread_messages(config):
            subject = msg.subject or ""
            from_email = msg.from_email
            if not from_email:
                continue
            if "<" in from_email and ">" in from_email:
                from_email = from_email.split("<")[1].split(">")[0]
            if config.inbox_id in from_email:
                skill_mark_read(msg.message_id, config)
                continue

            full_msg = skill_get_message(msg.message_id, config)
            body = full_msg.extracted_text or full_msg.text or msg.extracted_text or msg.text or "No content provided."
            print(f"Processing email from {from_email}...")
            log_customer_reply(from_email, body)
            reply_text = generate_reply_via_llm(body)
            skill_send_reply(from_email, f"Re: {subject}", reply_text, config)
            skill_mark_read(msg.message_id, config)
            processed.append({
                "type": "agent_inbox_email_received",
                "payload": {
                    "from": from_email,
                    "subject": subject,
                    "body": body[:500]
                }
            })
            processed.append({
                "type": "agent_inbox_reply_sent",
                "payload": {
                    "to": from_email,
                    "subject": f"Re: {subject}",
                    "reply_text": reply_text
                }
            })
    except Exception as e:
        print(f"AgentMail Fetch/Reply Error: {e}", file=sys.stderr)
    return processed

def main():
    processed = check_agentmail()
    if processed:
        print(json.dumps({"events": processed}))
    else:
        print(json.dumps({"events": []}))

if __name__ == "__main__":
    main()
