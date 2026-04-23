import os
import sys

# Set up environment variables
os.environ["AGENTMAIL_API_KEY"] = "am_us_inbox_d7f3e9a38432ff1c0896e4d39f984d2396d4b54f97bdb225713a3804a9e45a15"
os.environ["AGENTMAIL_INBOX"] = "mn-demo@agentmail.to"

try:
    from agentmail import AgentMail
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "agentmail", "python-dotenv", "--quiet"])
    from agentmail import AgentMail

def run_test():
    client = AgentMail(api_key=os.environ["AGENTMAIL_API_KEY"])
    inbox_id = os.environ["AGENTMAIL_INBOX"]
    
    print(f"--- Testing AgentMail Integration for {inbox_id} ---")
    
    print("\n1. Fetching recent messages...")
    try:
        res = client.inboxes.messages.list(inbox_id, limit=3)
        for msg in res.messages:
            print(f"  - Subject: {msg.subject} | From: {msg.from_} | Labels: {msg.labels}")
    except Exception as e:
        print(f"  [ERROR] Failed to fetch messages: {e}")

    print("\n2. Fetching unread messages...")
    try:
        res = client.inboxes.messages.list(inbox_id, labels=["unread"])
        print(f"  Found {len(res.messages)} unread messages.")
        for msg in res.messages:
            print(f"  - Subject: {msg.subject} | From: {msg.from_}")
    except Exception as e:
        print(f"  [ERROR] Failed to fetch unread messages: {e}")

    print("\n3. Sending a test email...")
    try:
        sent = client.inboxes.messages.send(
            inbox_id=inbox_id,
            to="mn-demo@agentmail.to", # send to self to test receive
            subject="TEST MIRRORNEURON - Direct API Test",
            text="This is a test from the manual python script."
        )
        print(f"  [SUCCESS] Sent message ID: {sent.message_id}")
    except Exception as e:
        print(f"  [ERROR] Failed to send email: {e}")

if __name__ == '__main__':
    run_test()
