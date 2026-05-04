#!/usr/bin/env python3
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "mn-skills" / "blueprint_support_skill" / "src"),
)
from mn_blueprint_support import apply_quick_test, log_status, progress, write_manifest


def default_task() -> dict:
    return {
        "task_id": "inventory-report-cli",
        "title": "Inventory report CLI",
        "description": (
            "Create a Python 3 script named inventory_report.py. The script must read a JSON array "
            "of inventory records from a file passed with --input or from stdin when --input is omitted. "
            "Each record has sku, category, quantity, and price. The CLI must support --format text|json "
            "and --low-stock-threshold (default 5)."
        ),
        "requirements": [
            "Use only the Python standard library.",
            "Include a pure function build_report(records, low_stock_threshold=5).",
            "The JSON output must include total_quantity, total_value, category_totals, and low_stock_skus.",
            "Category totals must be sorted alphabetically by category name.",
            "low_stock_skus must be sorted alphabetically.",
            "Round total_value to two decimal places.",
            "Expose a main() entrypoint and guard it with if __name__ == '__main__'.",
        ],
        "sample_records": [
            {"sku": "A-100", "category": "books", "quantity": 3, "price": 12.5},
            {"sku": "B-200", "category": "books", "quantity": 7, "price": 8.0},
            {"sku": "C-300", "category": "games", "quantity": 2, "price": 59.99},
        ],
        "validation": {
            "low_stock_threshold": 4,
            "expected": {
                "total_quantity": 12,
                "total_value": 213.48,
                "category_totals": [
                    {"category": "books", "quantity": 10},
                    {"category": "games", "quantity": 2},
                ],
                "low_stock_skus": ["A-100", "C-300"],
            },
        },
    }


def build_manifest(model: str, api_base: str, api_key: str, max_attempts: int, retry_backoff_ms: int, task: dict) -> dict:
    upload_config = {
        "from": "base",
        "upload_path": "llm_worker",
        "upload_as": "llm_worker",
        "workdir": "/sandbox/job/llm_worker",
        "pool": "default",
        "pool_slots": 1,
        "no_keep": True,
        "no_auto_providers": True,
        "tty": False,
        "pass_env": ["LITELLM_MODEL", "LITELLM_API_BASE", "LITELLM_API_KEY"],
        "environment": {
            "LITELLM_MODEL": model,
            "LITELLM_API_BASE": api_base,
            "LITELLM_API_KEY": api_key,
        },
        "max_attempts": max_attempts,
        "retry_backoff_ms": retry_backoff_ms,
    }

    llm_runner_config = {
        **upload_config,
        "runner_module": "MirrorNeuron.Runner.HostLocal",
    }

    nodes = [
        {
            "node_id": "codegen_round_1",
            "agent_type": "executor",
            "type": "generic",
            "role": "root_coordinator",
            "config": {
                **llm_runner_config,
                "name_prefix": "codegen-r1",
                "command": ["python3", "scripts/run_llm_step.py", "codegen", "1"],
                "output_message_type": "codegen_round_1_result",
            },
        },
        {
            "node_id": "review_round_1",
            "agent_type": "executor",
            "type": "generic",
            "config": {
                **llm_runner_config,
                "name_prefix": "review-r1",
                "command": ["python3", "scripts/run_llm_step.py", "review", "1"],
                "output_message_type": "review_round_1_result",
            },
        },
        {
            "node_id": "codegen_round_2",
            "agent_type": "executor",
            "type": "generic",
            "config": {
                **llm_runner_config,
                "name_prefix": "codegen-r2",
                "command": ["python3", "scripts/run_llm_step.py", "codegen", "2"],
                "output_message_type": "codegen_round_2_result",
            },
        },
        {
            "node_id": "review_round_2",
            "agent_type": "executor",
            "type": "generic",
            "config": {
                **llm_runner_config,
                "name_prefix": "review-r2",
                "command": ["python3", "scripts/run_llm_step.py", "review", "2"],
                "output_message_type": "review_round_2_result",
            },
        },
        {
            "node_id": "codegen_round_3",
            "agent_type": "executor",
            "type": "generic",
            "config": {
                **llm_runner_config,
                "name_prefix": "codegen-r3",
                "command": ["python3", "scripts/run_llm_step.py", "codegen", "3"],
                "output_message_type": "codegen_round_3_result",
            },
        },
        {
            "node_id": "validator",
            "agent_type": "executor",
            "type": "generic",
            "config": {
                **upload_config,
                "name_prefix": "validator",
                "command": ["python3", "scripts/validate_candidate.py"],
                "output_message_type": "validation_result",
                "complete_job": True,
            },
        },
    ]

    edges = [
        {
            "edge_id": "codegen_r1_to_review_r1",
            "from_node": "codegen_round_1",
            "to_node": "review_round_1",
            "message_type": "codegen_round_1_result",
        },
        {
            "edge_id": "review_r1_to_codegen_r2",
            "from_node": "review_round_1",
            "to_node": "codegen_round_2",
            "message_type": "review_round_1_result",
        },
        {
            "edge_id": "codegen_r2_to_review_r2",
            "from_node": "codegen_round_2",
            "to_node": "review_round_2",
            "message_type": "codegen_round_2_result",
        },
        {
            "edge_id": "review_r2_to_codegen_r3",
            "from_node": "review_round_2",
            "to_node": "codegen_round_3",
            "message_type": "review_round_2_result",
        },
        {
            "edge_id": "codegen_r3_to_validator",
            "from_node": "codegen_round_3",
            "to_node": "validator",
            "message_type": "codegen_round_3_result",
        },
    ]

    return {
        "manifest_version": "1.0",
        "graph_id": "general_sandboxed_llm_codegen_review_loop_3_rounds",
        "job_name": "llm-codegen-review-3-rounds",
        "entrypoints": ["codegen_round_1"],
        "initial_inputs": {"codegen_round_1": [task]},
        "nodes": nodes,
        "edges": edges,
        "policies": {"recovery_mode": "cluster_recover"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the LLM codegen/review loop bundle.")
    parser.add_argument(
        "--model",
        default="ollama/nemotron3:33b",
        help="LiteLLM model to expose to worker payloads, defaults to ollama/nemotron3:33b",
    )
    parser.add_argument(
        "--api-base",
        default="http://192.168.4.173:11434",
        help="LiteLLM API base URL, defaults to local Ollama",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional LiteLLM API key",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=2,
        help="Maximum OpenShell attempts per worker for transient failures",
    )
    parser.add_argument(
        "--retry-backoff-ms",
        type=int,
        default=500,
        help="Base retry backoff in milliseconds",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory to write generated bundles into",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Use local mock LLM responses and one attempt for cheap logic validation.",
    )
    args = parser.parse_args()
    quick_test = apply_quick_test(
        args,
        {"model": "mock/local-codegen", "max_attempts": 1, "retry_backoff_ms": 0},
    )
    log_status(
        "general_sandboxed_llm_codegen_review_loop",
        "generating LLM codegen bundle",
        phase="generate",
        details={"quick_test": quick_test, "model": args.model},
    )

    script_dir = Path(__file__).resolve().parent
    template_payloads = script_dir / "payloads"
    bundle_dir = args.output_dir
    payloads_dir = bundle_dir / "payloads"


    payloads_dir.mkdir(parents=True, exist_ok=True)
    if bundle_dir.resolve() != Path(__file__).resolve().parent:
        shutil.copytree(template_payloads, payloads_dir, dirs_exist_ok=True)

    manifest = build_manifest(
        model=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
        max_attempts=max(args.max_attempts, 1),
        retry_backoff_ms=max(args.retry_backoff_ms, 0),
        task=default_task(),
    )
    if quick_test:
        for node in manifest["nodes"]:
            config = node.get("config", {})
            env = dict(config.get("environment") or {})
            env["MN_BLUEPRINT_QUICK_TEST"] = "1"
            env["LLM_MOCK_MODE"] = "1"
            config["environment"] = env

    write_manifest(
        bundle_dir / "manifest.json",
        manifest,
        blueprint_id="general_sandboxed_llm_codegen_review_loop",
        quick_test=quick_test,
    )
    print(progress("bundle generated", 1, 1), file=sys.stderr)
    print(bundle_dir)


if __name__ == "__main__":
    main()
