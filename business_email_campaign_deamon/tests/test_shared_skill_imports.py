import os
import json
import subprocess
import sys
from pathlib import Path


BLUEPRINT_DIR = Path(__file__).resolve().parents[1]
PAYLOADS_DIR = BLUEPRINT_DIR / "payloads"


def test_payload_sitecustomize_exposes_shared_marketing_skill():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PAYLOADS_DIR / "customer_research")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from _synaptic_skills.marketing_email import build_customer_brief; print(callable(build_customer_brief))",
        ],
        cwd=BLUEPRINT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


def test_host_local_uploads_shared_skills_with_each_executor():
    manifest = json.loads((BLUEPRINT_DIR / "manifest.json").read_text())
    executor_nodes = [
        node
        for node in manifest["nodes"]
        if node.get("agent_type") == "executor"
        and node.get("config", {}).get("runner_module") == "MirrorNeuron.Runner.HostLocal"
    ]

    assert executor_nodes
    for node in executor_nodes:
        upload_paths = node["config"].get("upload_paths", [])
        sources = {entry["source"] for entry in upload_paths}
        assert "_shared_skills/business_email_campaign_skill" in sources
        assert "_shared_skills/mn_email_delivery_skill" in sources


def test_customer_research_runs_with_blueprint_local_campaign_skill(tmp_path):
    planned_actions = json.loads((BLUEPRINT_DIR / "planned_actions.json").read_text())
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps({"input": planned_actions[0]["payload"]}))
    db_path = tmp_path / "runtime.db"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PAYLOADS_DIR / "customer_research")
    env["MIRROR_NEURON_INPUT_FILE"] = str(input_file)
    env["SYNAPTIC_DB_PATH"] = str(db_path)
    for key in (
        "SECONDARY_LITELLM_API_KEY",
        "SECONDARY_LLM_API_KEY",
        "PRIMARY_LITELLM_API_KEY",
        "PRIMARY_LLM_API_KEY",
        "LITELLM_API_KEY",
        "LLM_API_KEY",
        "GEMINI_API_KEY",
    ):
        env.pop(key, None)

    result = subprocess.run(
        [
            sys.executable,
            str(PAYLOADS_DIR / "customer_research" / "scripts" / "execute.py"),
        ],
        cwd=BLUEPRINT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["customer_brief"]["recommended_template"]
    assert payload["audience_segment"]
