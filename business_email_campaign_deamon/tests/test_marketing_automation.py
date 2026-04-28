import contextlib
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


BLUEPRINT_DIR = Path(__file__).resolve().parents[1]
EXECUTE_PATH = BLUEPRINT_DIR / "payloads" / "marketing_automation" / "scripts" / "execute.py"


def load_execute_module():
    spec = importlib.util.spec_from_file_location("marketing_automation_execute", EXECUTE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def init_runtime_db(path: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE email_drafts (
                draft_id TEXT PRIMARY KEY,
                customer_id TEXT,
                status TEXT,
                provider_id TEXT,
                sent_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE customer_marketing_activity (
                activity_id TEXT PRIMARY KEY,
                customer_id TEXT,
                summary TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE agent_logs (
                runtime_job_id TEXT,
                agent_id TEXT,
                level TEXT,
                message TEXT,
                details_json TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO email_drafts (draft_id, customer_id, status) VALUES (?, ?, 'ready')",
            ("draft_test", "cust_1"),
        )


class MarketingAutomationTests(unittest.TestCase):
    def setUp(self):
        self.previous_env = os.environ.copy()
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "runtime.db")
        self.input_path = os.path.join(self.tmp.name, "input.json")
        init_runtime_db(self.db_path)
        os.environ["SYNAPTIC_DB_PATH"] = self.db_path
        os.environ["SYNAPTIC_DB_CONNECTION"] = f"sqlite:///{self.db_path}"
        os.environ["MIRROR_NEURON_INPUT_FILE"] = self.input_path
        os.environ["SYNAPTIC_TEST_EMAIL_TO"] = ""
        os.environ["SYNAPTIC_EMAIL_DELIVERY_MODE"] = "agentmail"
        os.environ["SYNAPTIC_EMIT_CYCLE_TRIGGER"] = "false"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.previous_env)
        self.tmp.cleanup()

    def write_plan(self):
        plan = {
            "runtime_job_id": "job_1",
            "cycle": 2,
            "customer": {
                "customer_id": "cust_1",
                "name": "Avery",
                "email": "avery@example.com",
            },
            "control_decision": {"decision": "send_now"},
            "policy_decision": {"decision": "allow"},
            "saved_draft": {
                "draft_id": "draft_test",
                "subject": "A small story idea",
                "body_text": "Plain text body",
                "html_body": "<p>Plain text body</p>",
            },
        }
        Path(self.input_path).write_text(json.dumps(plan))

    def test_injected_email_sender_logs_sent_event(self):
        self.write_plan()
        module = load_execute_module()
        sent_requests = []

        def fake_email_sender(request):
            sent_requests.append(request)
            return {"status": "sent", "provider_id": "fake_provider", "http_status": 200}

        def fake_slack_sender(_text):
            return {"status": "sent", "channel": "#test"}

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.main(email_sender=fake_email_sender, slack_sender=fake_slack_sender)

        payload = json.loads(output.getvalue())
        self.assertEqual(sent_requests[0]["to"], ["homerquan@gmail.com"])
        self.assertEqual(payload["events"][0]["payload"]["status"], "sent")
        self.assertEqual(payload["events"][0]["payload"]["subject"], "A small story idea")

        with sqlite3.connect(self.db_path) as conn:
            log = conn.execute(
                "SELECT details_json FROM agent_logs WHERE message = 'Email sent event.'"
            ).fetchone()
        self.assertIsNotNone(log)
        self.assertEqual(
            json.loads(log[0]),
            {"to": "homerquan@gmail.com", "subject": "A small story idea"},
        )

    def test_quick_testing_mode_dry_runs_without_email_sender(self):
        self.write_plan()
        os.environ["SYNAPTIC_EMAIL_DELIVERY_MODE"] = "dry_run"
        module = load_execute_module()

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.main()

        payload = json.loads(output.getvalue())
        event = payload["events"][0]["payload"]
        self.assertEqual(event["status"], "sent")
        self.assertEqual(event["provider_id"], "dry_run")
        self.assertTrue(event["dry_run"])
        self.assertTrue(event["quick_testing"])


if __name__ == "__main__":
    unittest.main()
