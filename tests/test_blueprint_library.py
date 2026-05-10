from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL_SRC = ROOT.parent / "mn-skills" / "blueprint_support_skill" / "src"
if SKILL_SRC.exists() and str(SKILL_SRC) not in sys.path:
    sys.path.insert(0, str(SKILL_SRC))

from mn_blueprint_support import FakeLLMClient, LEGACY_ALIASES, PRODUCT_PROFILES, REQUIRED_BLUEPRINT_IDS, SCENARIOS, get_scenario, run_blueprint
from mn_blueprint_support.llm import DEFAULT_OLLAMA_BASE, OllamaLLMClient, ollama_model_available
from mn_blueprint_support.standard import OUTPUT_ADAPTERS, STANDARD_VERSION, RunStore


def test_index_entries_point_to_loadable_blueprint_folders() -> None:
    index = json.loads((ROOT / "index.json").read_text())
    assert index
    ids = [entry["id"] for entry in index]
    assert len(ids) == len(set(ids))
    assert not list(ROOT.glob("*/product.json"))
    required_product_fields = {
        "agent_role",
        "customizable_for",
        "customize",
        "example",
        "investor",
        "one_line",
        "output",
        "problem",
        "runtime_features",
        "simulation_type",
        "target_users",
    }

    for entry in index:
        blueprint_dir = ROOT / entry["path"]
        manifest_path = blueprint_dir / "manifest.json"
        payloads_dir = blueprint_dir / "payloads"
        product = entry.get("product")
        assert blueprint_dir.exists(), entry
        assert manifest_path.exists(), entry
        assert isinstance(product, dict), entry
        assert required_product_fields.issubset(product), entry
        assert "blueprint_id" not in product
        assert "title" not in product
        manifest = json.loads(manifest_path.read_text())
        if manifest["metadata"].get("python_source_mode") is True:
            assert "python_workflow" in manifest["metadata"], entry
        else:
            assert payloads_dir.exists(), entry
        assert manifest["manifest_version"] == "1.0"
        assert manifest["graph_id"] == entry["graph_id"]
        assert manifest["job_name"] == entry["job_name"]
        assert entry["id"].startswith(("general_", "business_", "finance_", "science_"))
        assert manifest["metadata"]["blueprint_id"] == entry["id"]
        assert manifest["metadata"]["name"] == entry["name"]
        assert manifest["metadata"]["description"] == entry["description"]
        assert manifest["description"] == entry["description"]


def test_business_code_analysis_memory_benchmark_fixture_and_graph_contract() -> None:
    blueprint_id = "business_context_memory_compression_code_analsysis"
    blueprint_dir = ROOT / blueprint_id
    manifest = json.loads((blueprint_dir / "manifest.json").read_text())
    fixture = json.loads((blueprint_dir / "payloads" / "repo_fixture" / "django_tree_fixture.json").read_text())

    assert manifest["metadata"]["blueprint_id"] == blueprint_id
    assert manifest["entrypoints"] == ["initializer"]
    executable_nodes = [node for node in manifest["nodes"] if node.get("node_id") != "sink"]
    assert [node["role"] for node in executable_nodes] == [
        "initializer",
        "repo_architect",
        "dependency_mapper",
        "risk_classifier",
        "context_compressor",
        "briefing_author",
    ]
    initializer_uploads = {item["source"] for item in manifest["nodes"][0]["config"]["upload_paths"]}
    assert {"initializer", "_vendor", "repo_fixture"}.issubset(initializer_uploads)

    assert fixture["schema_version"] == "mn.code_analysis_fixture.v1"
    assert fixture["repo"]["url"] == "https://github.com/django/django"
    assert fixture["repo"]["commit_sha"] == "4d455ae2d7689ce066dfffef9fc29a6f6d3ed33e"
    assert fixture["scale"]["available_files"] >= 3000
    assert len(fixture["files"]) >= 3000
    assert all("source_url" in entry for entry in fixture["files"][:50])
    assert all("content" not in entry and "source" not in entry for entry in fixture["files"][:50])
    assert "token, latency, quality, and privacy telemetry" in manifest["metadata"]["runtime_features"]

    for script in [
        "initializer/scripts/init.py",
        "interpreter/scripts/interpreter.py",
        "extractor/scripts/extractor.py",
        "classifier/scripts/classifier.py",
        "decision/scripts/decision.py",
        "critic/scripts/critic.py",
    ]:
        path = blueprint_dir / "payloads" / script
        ast.parse(path.read_text(), filename=str(path))

    context_helper = (blueprint_dir / "payloads" / "initializer" / "scripts" / "context_memory.py").read_text()
    critic_script = (blueprint_dir / "payloads" / "critic" / "scripts" / "critic.py").read_text()
    assert "aggregate_benchmark_events" in context_helper
    assert "estimated_total_tokens_processed" in context_helper
    assert "context_memory_benchmark_report" in critic_script
    assert "quality_score" in critic_script
    assert "compile_latency_seconds_p95" in critic_script


def test_finance_property_alpha_memory_benchmark_contract(tmp_path: Path) -> None:
    blueprint_id = "finance_zip_code_property_alpha_engine_with_memory"
    blueprint_dir = ROOT / blueprint_id
    manifest = json.loads((blueprint_dir / "manifest.json").read_text())
    config = json.loads((blueprint_dir / "config" / "default.json").read_text())
    runner_path = blueprint_dir / "payloads" / "simulation_loop" / "scripts" / "run_blueprint.py"

    assert manifest["metadata"]["blueprint_id"] == blueprint_id
    assert manifest["initial_inputs"]["simulation_loop"][0]["memory_mode"] == "compare"
    assert "working memory retrieval" in manifest["metadata"]["runtime_features"]
    assert config["benchmark"]["baseline"] == "all_context"
    assert config["benchmark"]["schema_version"] == "mn.finance.property_alpha.memory_benchmark.v2"
    assert config["memory"]["enabled"] is True
    ast.parse(runner_path.read_text(), filename=str(runner_path))

    spec = importlib.util.spec_from_file_location("finance_memory_runner_contract_test", runner_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    result = module.run_blueprint(
        inputs={"steps": 2, "seed": 7, "memory_limit": 36},
        llm_client=FakeLLMClient(),
        runs_root=tmp_path,
    )

    benchmark = result["benchmark"]
    first_step = result["timeline"][0]
    source_refs = set(first_step["memory_packet"]["source_refs"])

    assert result["blueprint"] == blueprint_id
    assert len(result["timeline"]) == 2
    assert result["llm"]["calls"] == 2
    assert benchmark["schema_version"] == "mn.finance.property_alpha.memory_benchmark.v2"
    assert benchmark["memory_metrics"]["max_dropped_facts"] >= 1000
    assert benchmark["all_context"]["strategy"] == "share_full_agent_history"
    assert benchmark["optimized_memory"]["strategy"] == "optimized_memory_packet"
    assert benchmark["optimized_memory"]["mean_quality_score"] >= benchmark["all_context"]["mean_quality_score"]
    assert benchmark["lift"]["estimated_token_reduction_ratio"] > 0.9
    assert benchmark["all_context"]["mean_estimated_input_tokens"] > benchmark["optimized_memory"]["mean_estimated_input_tokens"]
    assert benchmark["all_context"]["budget_violation_rate"] == 1.0
    assert first_step["memory_comparison"]["optimized_memory"]["parameters"]["memory_used"] is True
    assert first_step["memory_comparison"]["all_context"]["parameters"]["memory_used"] is False
    assert first_step["context_packets"]["all_context"]["strategy"] == "share_full_agent_history"
    assert first_step["context_packets"]["optimized_memory"]["source_refs"]
    assert {
        "mem:02139-rent-comp-upside",
        "mem:02139-dscr-exception",
        "mem:river-quad-seller-motivation",
        "mem:ivy-duplex-flood-insurance",
    }.issubset(source_refs)


@pytest.mark.parametrize(
    "blueprint_id",
    [
        "general_python_sdk_live_research_daemon",
        "general_python_sdk_research_pipeline",
    ],
)
def test_python_sdk_source_blueprints_run_directly_and_generate_bundle(
    blueprint_id: str,
    tmp_path: Path,
) -> None:
    blueprint_dir = ROOT / blueprint_id
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(ROOT.parent / "mn-python-sdk"),
            str(ROOT.parent / "mn-skills" / "blueprint_support_skill" / "src"),
            env.get("PYTHONPATH", ""),
        ]
    )

    direct_run = subprocess.run(
        [sys.executable, str(blueprint_dir / "workflow.py")],
        cwd=tmp_path,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    direct_output = json.loads(direct_run.stdout)
    assert direct_output

    bundle_dir = tmp_path / blueprint_id
    subprocess.run(
        [
            sys.executable,
            "-m",
            "mn_blueprint_support.python_workflow_bundle_cli",
            "--blueprint-dir",
            str(blueprint_dir),
            "--quick-test",
            "--output-dir",
            str(bundle_dir),
        ],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert (bundle_dir / "manifest.json").exists()
    assert (bundle_dir / "payloads" / "mn_python_workflow" / "mn_worker.py").exists()
    assert (bundle_dir / "requirements.txt").exists()
    assert (bundle_dir / "config" / "default.json").exists()
    assert not (bundle_dir / "product.json").exists()
    manifest = json.loads((blueprint_dir / "manifest.json").read_text())
    for include_path in manifest["metadata"]["python_workflow"].get("includes", []):
        assert (bundle_dir / "payloads" / "mn_python_workflow" / "source" / include_path).exists()


def test_every_blueprint_declares_standard_config_and_interfaces() -> None:
    required_sections = {
        "metadata",
        "identity",
        "inputs",
        "simulation",
        "llm",
        "outputs",
        "logging",
        "real_adapters",
        "interfaces",
        "execution_model",
    }
    required_run_artifacts = {
        "run.json",
        "config.json",
        "inputs.json",
        "events.jsonl",
        "result.json",
        "final_artifact.json",
    }
    index = json.loads((ROOT / "index.json").read_text())
    blueprint_ids = [entry["id"] for entry in index]
    assert set(PRODUCT_PROFILES) == set(blueprint_ids)

    for blueprint_id in blueprint_ids:
        config_path = ROOT / blueprint_id / "config" / "default.json"
        manifest_path = ROOT / blueprint_id / "manifest.json"
        assert config_path.exists(), f"{blueprint_id} missing config/default.json"

        config = json.loads(config_path.read_text())
        assert required_sections.issubset(config), blueprint_id
        assert config["standard_version"] == STANDARD_VERSION
        assert config["identity"]["blueprint_id"] == blueprint_id
        assert config["identity"]["name"] != blueprint_id
        assert config["inputs"]["adapter"] == "mock"
        assert config["outputs"]["adapter"] == "local_run_store"
        assert config["outputs"]["run_root"] == "~/.mn/runs"
        assert config["outputs"]["write_run_store"] is True
        assert config["llm"]["model"] == "ollama/nemotron3:33b"
        assert config["llm"]["api_base"] == "http://192.168.4.173:11434"
        assert set(config["interfaces"]["run_artifacts"]) == required_run_artifacts
        assert config["interfaces"]["input_adapters"] == ["mock", "json", "file", "env_json"]
        assert tuple(config["interfaces"]["output_adapters"]) == OUTPUT_ADAPTERS
        assert "call_llm_agent" in config["execution_model"]
        assert "apply_decision_to_simulation" in config["execution_model"]

        manifest = json.loads(manifest_path.read_text())
        standard = manifest["metadata"]["standard"]
        assert standard["version"] == STANDARD_VERSION
        assert standard["config_path"] == "config/default.json"
        assert standard["run_store"] == "~/.mn/runs/<run_id>/"
        assert standard["default_input_adapter"] == "mock"
        assert manifest["metadata"]["interfaces"]["identity"] == ["blueprint_id", "name", "run_id"]
        assert set(manifest["metadata"]["interfaces"]["outputs"]) == required_run_artifacts
        assert tuple(manifest["metadata"]["interfaces"]["output_adapters"]) == OUTPUT_ADAPTERS

    for blueprint_id in REQUIRED_BLUEPRINT_IDS:
        scenario_path = ROOT / blueprint_id / "scenario.json"
        assert scenario_path.exists(), f"{blueprint_id} missing scenario.json"
        scenario = json.loads(scenario_path.read_text())
        assert scenario["blueprint_id"] == blueprint_id
        assert scenario["metrics"]
        assert scenario["actions"]


def test_every_blueprint_has_product_quality_readme_sections() -> None:
    required_sections = [
        "## One-line value proposition",
        "## What it is",
        "## Who this is for",
        "## Why it matters",
        "## Why this runtime is useful here",
        "## How it works",
        "## Example scenario",
        "## Inputs",
        "## Outputs",
        "## How to run",
        "## How to customize it",
        "## What to look for in results",
        "## Investor and evaluator narrative",
        "## Runtime features demonstrated",
        "## Test coverage",
        "## Limitations",
        "## Next steps",
    ]
    for blueprint_id in PRODUCT_PROFILES:
        text = (ROOT / blueprint_id / "README.md").read_text()
        assert f"`Blueprint ID:` `{blueprint_id}`" in text
        for section in required_sections:
            assert section in text, f"{blueprint_id} missing {section}"
        assert "static dashboard" in text
        assert "one-shot LLM" in text
        assert "replace" in text.lower()


def test_portfolio_standard_document_explains_execution_contract() -> None:
    text = (ROOT / "BLUEPRINT_STANDARD.md").read_text()
    for phrase in [
        "metadata",
        "config/default.json",
        "mock",
        "file",
        "env_json",
        "~/.mn/runs/<run_id>/",
        "run.json",
        "events.jsonl",
        "interactive_first_run_setup",
        "list_runs",
        "observe",
        "Call the LLM agent",
        "final_artifact.json",
    ]:
        assert phrase in text


def test_blueprint_standard_imports_shared_mn_skill_implementation() -> None:
    assert RunStore.__module__ == "mn_blueprint_support.run_store"
    text = (ROOT / "BLUEPRINT_STANDARD.md").read_text()
    assert "mn-skills/blueprint_support_skill/src/mn_blueprint_support/" in text
    assert "mn_blueprint_support.solution_runner" in text
    scenarios_text = (SKILL_SRC / "mn_blueprint_support" / "scenarios.py").read_text()
    assert "load_blueprint_json_files(\"scenario.json\")" in scenarios_text
    assert "general_closed_loop_agent_runtime" not in scenarios_text


def test_blueprint_repo_does_not_carry_support_code() -> None:
    assert not (ROOT / "blueprints.py").exists()
    assert not (ROOT / "blueprint_runtime").exists()


def test_renamed_blueprint_aliases_resolve_to_new_scenarios() -> None:
    for old_id, new_id in LEGACY_ALIASES.items():
        if new_id in SCENARIOS:
            assert get_scenario(old_id).blueprint_id == new_id


@pytest.mark.parametrize("blueprint_id", REQUIRED_BLUEPRINT_IDS)
def test_blueprint_manifest_and_runner_are_loadable(blueprint_id: str) -> None:
    blueprint_dir = ROOT / blueprint_id
    manifest_path = blueprint_dir / "manifest.json"
    readme_path = blueprint_dir / "README.md"
    runner_path = blueprint_dir / "payloads" / "simulation_loop" / "scripts" / "run_blueprint.py"

    assert manifest_path.exists()
    assert readme_path.exists()
    assert runner_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["metadata"]["blueprint_id"] == blueprint_id
    assert manifest["metadata"]["category"] == SCENARIOS[blueprint_id].category
    assert manifest["metadata"]["llm"]["default_model"] == "ollama/nemotron3:33b"
    assert manifest["entrypoints"] == ["simulation_loop"]
    assert manifest["nodes"][0]["agent_type"] == "executor"
    assert manifest["nodes"][1]["agent_type"] == "aggregator"
    assert manifest["edges"][0]["message_type"] == "blueprint_report"


@pytest.mark.parametrize("blueprint_id", REQUIRED_BLUEPRINT_IDS)
def test_blueprint_runs_end_to_end_with_fake_llm(blueprint_id: str, tmp_path: Path) -> None:
    llm = FakeLLMClient()
    result = run_blueprint(
        blueprint_id,
        inputs={"steps": 4, "seed": 123, "custom_input_is_accepted": True},
        llm_client=llm,
        runs_root=tmp_path,
    )

    assert result["blueprint"] == blueprint_id
    assert result["identity"]["blueprint_id"] == blueprint_id
    assert result["identity"]["name"] != blueprint_id
    assert result["identity"]["run_id"]
    assert result["run"]["run_dir"].startswith(str(tmp_path))
    assert result["uses_llm"] is True
    assert result["uses_simulation"] is True
    assert result["inputs"]["custom_input_is_accepted"] is True
    assert len(result["timeline"]) == 4
    assert result["llm"]["provider"] == "fake"
    assert result["llm"]["calls"] == 4
    assert llm.calls == 4

    changed = [item for item in result["state_changes"] if item["delta"] != 0]
    assert changed, "simulation state should change over time"

    final = result["final_artifact"]
    assert final["type"]
    assert final["recommended_action"]
    assert final["key_metrics"]
    assert final["ranked_options"]
    assert final["next_steps"]

    first_step = result["timeline"][0]
    assert first_step["observation"]["metrics"]
    assert first_step["decision"]["action"]
    assert first_step["state_after"]
    assert result["architecture"]["interfaces"]["identity_fields"] == ["blueprint_id", "name", "run_id"]
    assert "call_llm_agent" in result["architecture"]["execution_model"]


@pytest.mark.parametrize("blueprint_id", REQUIRED_BLUEPRINT_IDS)
def test_blueprint_cli_runs_with_mock_llm(blueprint_id: str, tmp_path: Path) -> None:
    runner_path = ROOT / blueprint_id / "payloads" / "simulation_loop" / "scripts" / "run_blueprint.py"
    completed = subprocess.run(
        [sys.executable, str(runner_path), "--mock-llm", "--steps", "2", "--seed", "7", "--runs-root", str(tmp_path)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert result["blueprint"] == blueprint_id
    assert len(result["timeline"]) == 2
    assert result["llm"]["calls"] == 2
    assert result["final_artifact"]["recommended_action"]
    assert result["run"]["run_dir"].startswith(str(tmp_path))


def test_required_category_counts_and_prefixes() -> None:
    categories = {}
    for blueprint_id, spec in SCENARIOS.items():
        assert blueprint_id.startswith(("general_", "business_", "finance_", "science_"))
        assert not blueprint_id.startswith("financial_")
        categories.setdefault(spec.category, []).append(blueprint_id)

    assert len(categories["general"]) >= 8
    assert 3 <= len(categories["business"]) <= 5
    assert 3 <= len(categories["finance"]) <= 5
    assert 3 <= len(categories["science"]) <= 5
    assert "financial" not in categories


def test_human_gate_and_tool_observation_paths_are_exercised(tmp_path: Path) -> None:
    human_result = run_blueprint(
        "general_human_approval_decision_gate",
        inputs={"steps": 2, "human_approval": "approve_high_confidence"},
        llm_client=FakeLLMClient(),
        runs_root=tmp_path,
    )
    assert all(step["human_gate"]["required"] for step in human_result["timeline"])

    tool_result = run_blueprint(
        "general_llm_tool_orchestration_loop",
        inputs={"steps": 2},
        llm_client=FakeLLMClient(),
        runs_root=tmp_path,
    )
    assert all("tool_result" in step["observation"] for step in tool_result["timeline"])

    negotiation_result = run_blueprint(
        "general_multi_agent_contract_negotiation_loop",
        inputs={"steps": 2},
        llm_client=FakeLLMClient(),
        runs_root=tmp_path,
    )
    assert all("agent_messages" in step["observation"] for step in negotiation_result["timeline"])


def test_run_store_writes_global_execution_artifacts(tmp_path: Path) -> None:
    run_id = "test-run-store-contract"
    result = run_blueprint(
        "business_supply_chain_resilience_war_room",
        inputs={"steps": 2, "seed": 99},
        llm_client=FakeLLMClient(),
        run_id=run_id,
        runs_root=tmp_path,
    )

    run_dir = tmp_path / run_id
    assert result["run"]["run_dir"] == str(run_dir)
    expected = {
        "run.json",
        "config.json",
        "inputs.json",
        "events.jsonl",
        "result.json",
        "final_artifact.json",
    }
    assert {path.name for path in run_dir.iterdir()} >= expected

    run_summary = json.loads((run_dir / "run.json").read_text())
    saved_result = json.loads((run_dir / "result.json").read_text())
    saved_artifact = json.loads((run_dir / "final_artifact.json").read_text())
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    event_types = [event["type"] for event in events]

    assert run_summary["status"] == "completed"
    assert run_summary["run_id"] == run_id
    assert saved_result["identity"]["run_id"] == run_id
    assert saved_artifact == result["final_artifact"]
    assert event_types[:2] == ["run_started", "inputs_loaded"]
    assert event_types.count("simulation_step_started") == 2
    assert event_types.count("llm_decision") == 2
    assert event_types.count("simulation_state_updated") == 2
    assert event_types[-1] == "run_completed"


def test_file_input_adapter_can_replace_mock_payload(tmp_path: Path) -> None:
    input_path = tmp_path / "inputs.json"
    input_path.write_text(json.dumps({"steps": 3, "seed": 321, "initial_backlog": 41}) + "\n")

    result = run_blueprint(
        "general_closed_loop_agent_runtime",
        input_file=input_path,
        llm_client=FakeLLMClient(),
        runs_root=tmp_path,
    )

    assert result["input_source"]["adapter"] == "file"
    assert result["input_source"]["real_ready"] is True
    assert result["inputs"]["initial_backlog"] == 41.0
    assert len(result["timeline"]) == 3


def test_run_store_can_be_disabled(tmp_path: Path) -> None:
    result = run_blueprint(
        "general_closed_loop_agent_runtime",
        inputs={"steps": 1},
        llm_client=FakeLLMClient(),
        runs_root=tmp_path,
        write_run_store=False,
    )

    assert result["run"]["run_dir"] is None
    assert not any(tmp_path.iterdir())


def test_specialized_motion_worker_uses_shared_run_contract(tmp_path: Path, monkeypatch, capsys) -> None:
    worker_path = ROOT / "science_multi_agent_motion_planning_lab" / "payloads" / "world_worker" / "scripts" / "run_shared_world.py"
    spec = importlib.util.spec_from_file_location("motion_worker_contract_test", worker_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class FakeState:
        def __init__(self, x: float, y: float):
            self.p_pos = [x, y]
            self.p_vel = [0.0, 0.0]

    class FakeAgent:
        def __init__(self, name: str, adversary: bool, x: float):
            self.name = name
            self.adversary = adversary
            self.size = 0.05
            self.max_speed = 1.0
            self.state = FakeState(x, 0.0)

    class FakeLandmark:
        def __init__(self):
            self.name = "obstacle_0"
            self.size = 0.08
            self.state = FakeState(0.4, 0.0)

    class FakeWorld:
        def __init__(self, num_good: int, num_adversaries: int, num_obstacles: int):
            self.agents = [
                *(FakeAgent(f"agent_{index}", False, index * 0.2) for index in range(num_good)),
                *(FakeAgent(f"adversary_{index}", True, 0.8 + index * 0.2) for index in range(num_adversaries)),
            ]
            self.landmarks = [FakeLandmark() for _ in range(num_obstacles)]

    class FakeEnv:
        def __init__(self, num_good: int, num_adversaries: int, num_obstacles: int, max_cycles: int, render_mode=None):
            self.max_cycles = max_cycles
            self.cycle = 0
            self.world = FakeWorld(num_good, num_adversaries, num_obstacles)
            self.unwrapped = self
            self.agents = [agent.name for agent in self.world.agents]

        def reset(self, seed: int):
            self.seed = seed

        def action_space(self, _agent_name: str):
            class Space:
                def sample(self):
                    return 0

            return Space()

        def step(self, _actions: dict):
            self.cycle += 1
            for index, agent in enumerate(self.world.agents):
                agent.state.p_pos[0] += 0.01 * (index + 1)
                agent.state.p_vel = [0.01 * (index + 1), 0.0]
            rewards = {
                agent.name: 0.2 if not agent.adversary else -0.1
                for agent in self.world.agents
            }
            done = self.cycle >= self.max_cycles
            terminations = {name: False for name in self.agents}
            truncations = {name: done for name in self.agents}
            if done:
                self.agents = []
            return {}, rewards, terminations, truncations, {}

        def close(self):
            self.closed = True

    class FakeSimpleTag:
        @staticmethod
        def parallel_env(**kwargs):
            return FakeEnv(**kwargs)

    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps({"seed": 33, "max_cycles": 2, "good_agents": 2, "adversaries": 1, "obstacles": 1}))
    runs_root = tmp_path / "runs"
    monkeypatch.setattr(module, "import_simple_tag", lambda: (FakeSimpleTag, "fake.simple_tag_v3"))
    monkeypatch.setenv("MN_INPUT_FILE", str(input_file))
    monkeypatch.setenv("MN_RUN_ID", "motion-worker-contract-run")
    monkeypatch.setenv("MN_RUNS_ROOT", str(runs_root))
    for env_name in (
        "SIMULATION_SEED",
        "MAX_CYCLES",
        "NUM_GOOD",
        "NUM_ADVERSARIES",
        "NUM_OBSTACLES",
        "POLICY_MODE",
        "MN_NO_RUN_STORE",
        "MN_DISABLE_RUN_STORE",
        "MN_BLUEPRINT_CONFIG_PATH",
        "MN_BLUEPRINT_CONFIG_JSON",
    ):
        monkeypatch.delenv(env_name, raising=False)

    module.main()

    result = json.loads(capsys.readouterr().out)
    run_dir = runs_root / "motion-worker-contract-run"
    assert result["identity"]["blueprint_id"] == "science_multi_agent_motion_planning_lab"
    assert result["identity"]["run_id"] == "motion-worker-contract-run"
    assert result["seed"] == 33
    assert result["max_cycles"] == 2
    assert result["team_counts"] == {"good": 2, "adversary": 1}
    assert result["uses_simulation"] is True
    assert result["final_artifact"]["type"] == "motion_planning_run_report"
    assert result["shared_run_contract"]["available"] is True
    assert result["shared_run_contract"]["run_store_enabled"] is True
    assert result["shared_run_contract"]["run_dir"] == str(run_dir)

    assert {path.name for path in run_dir.iterdir()} >= {
        "run.json",
        "config.json",
        "inputs.json",
        "events.jsonl",
        "result.json",
        "final_artifact.json",
    }
    saved_inputs = json.loads((run_dir / "inputs.json").read_text())
    saved_result = json.loads((run_dir / "result.json").read_text())
    event_types = [json.loads(line)["type"] for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert saved_inputs["seed"] == 33
    assert saved_inputs["raw_input"]["good_agents"] == 2
    assert saved_result["final_artifact"] == result["final_artifact"]
    assert "simulation_started" in event_types
    assert "simulation_state_updated" in event_types
    assert "simulation_completed" in event_types
    assert event_types[-1] == "run_completed"


def test_invalid_step_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="steps"):
        run_blueprint("business_supply_chain_resilience_war_room", inputs={"steps": 0}, llm_client=FakeLLMClient())


@pytest.mark.ollama
def test_optional_ollama_integration_smoke(tmp_path: Path) -> None:
    if os.getenv("RUN_OLLAMA_INTEGRATION") != "1":
        pytest.skip("set RUN_OLLAMA_INTEGRATION=1 to run live Ollama tests")

    api_base = os.getenv("LITELLM_API_BASE", DEFAULT_OLLAMA_BASE)
    model = os.getenv("LITELLM_MODEL", "ollama/nemotron3:33b").removeprefix("ollama/")
    if not ollama_model_available(api_base=api_base, model=model, timeout=2.0):
        pytest.skip(f"Ollama model {model} is not available at {api_base}")

    client = OllamaLLMClient.from_env(strict=True, prefer_shared_skill=False)
    result = run_blueprint("general_closed_loop_agent_runtime", inputs={"steps": 1, "seed": 11}, llm_client=client, runs_root=tmp_path)

    assert result["llm"]["provider"] == "ollama"
    assert result["llm"]["calls"] == 1
    assert result["timeline"][0]["decision"]["action"]
