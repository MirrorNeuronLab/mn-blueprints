import importlib.util
from pathlib import Path


BLUEPRINT_DIR = Path(__file__).resolve().parents[1]
EXECUTE_PATH = BLUEPRINT_DIR / "payloads" / "inbox_reply" / "scripts" / "execute.py"


def load_execute_module():
    spec = importlib.util.spec_from_file_location("inbox_reply_execute", EXECUTE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_inbox_reply_renders_personal_reply_template():
    module = load_execute_module()

    html = module.render_reply_html(
        subject="Question about stories",
        reply_text="Thanks for reaching out. Bibblio can help with that.",
        inbound_body="Can you help?",
    )

    assert "Thanks for reaching out" in html
    assert "Manage preferences" not in html
    assert "Unsubscribe" not in html
    assert "data-slot=\"body_section\"" in html


def test_inbox_reply_slack_report_uses_delivery_status(monkeypatch):
    module = load_execute_module()
    sent_messages = []

    def fake_post_slack_message(text):
        sent_messages.append(text)
        return {"status": "sent", "channel": "#test"}

    monkeypatch.setattr(module, "post_slack_message", fake_post_slack_message)

    result = module.send_slack_reply_report(
        to_email="parent@example.com",
        subject="Question about stories",
        delivery={"status": "sent"},
    )

    assert result["status"] == "sent"
    assert "reply to <parent@example.com> was sent" in sent_messages[0]
