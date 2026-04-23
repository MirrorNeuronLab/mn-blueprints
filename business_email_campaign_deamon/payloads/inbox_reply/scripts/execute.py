#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
import urllib.error
import subprocess

try:
    import agentmail
except ImportError:
    print("Installing agentmail SDK inside sandbox...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "agentmail", "python-dotenv", "--quiet"])

from agentmail import AgentMail

import sqlite3
from datetime import datetime, timezone

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def log_customer_reply(from_email: str, body: str):
    db_path = "/tmp/mn_business_email_campaign.db"
    if not os.path.exists(db_path):
        return
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        
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
    api_base = os.environ.get("LITELLM_API_BASE", "http://192.168.4.173:11434")
    model = os.environ.get("LITELLM_MODEL", "ollama/gemma4:latest")
    
    if "ollama" in model and api_base.endswith("11434"):
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

def check_agentmail() -> list:
    api_key = os.environ.get("AGENTMAIL_API_KEY")
    inbox_id = os.environ.get("AGENTMAIL_INBOX")
    if not api_key or not inbox_id:
        return []

    client = AgentMail(api_key=api_key)
    processed = []
    try:
        res = client.inboxes.messages.list(inbox_id, labels=["unread"])
        
        for msg in res.messages:
            subject = msg.subject or ""
            
            # Respond to ALL incoming emails now
            from_email = msg.from_
            if not from_email:
                continue
                
            if "<" in from_email and ">" in from_email:
                from_email = from_email.split("<")[1].split(">")[0]
                
            if inbox_id in from_email:
                # Skip processing our own emails to prevent loops
                client.inboxes.messages.update(
                    inbox_id=inbox_id,
                    message_id=msg.message_id,
                    add_labels=["read"],
                    remove_labels=["unread"]
                )
                continue
                
            # Fetch the full message to get the actual body content
            full_msg = client.inboxes.messages.get(inbox_id, msg.message_id)
            body = full_msg.extracted_text or full_msg.text or "No content provided."
            print(f"Processing email from {from_email}...")
            
            log_customer_reply(from_email, body)
            reply_text = generate_reply_via_llm(body)
            
            # Reply using SDK
            client.inboxes.messages.send(
                inbox_id,
                to=from_email,
                subject=f"Re: {subject}",
                text=reply_text
            )
            # Mark as read so we don't process it again
            client.inboxes.messages.update(
                inbox_id=inbox_id,
                message_id=msg.message_id,
                add_labels=["read"],
                remove_labels=["unread"]
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

def main():
    processed = check_agentmail()
    if processed:
        print(json.dumps({"events": processed}))
    else:
        print(json.dumps({"events": []}))

if __name__ == "__main__":
    main()
