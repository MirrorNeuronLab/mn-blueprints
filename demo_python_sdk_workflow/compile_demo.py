#!/usr/bin/env python3
"""Compile the decorated workflow into a temporary runnable bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from mn_sdk import workflow

from workflow import DemoPythonSdkWorkflow


def _write_runtime_compatible_worker(output: Path) -> None:
    """Adapt the SDK worker envelope to the current Core step contract."""
    worker = output / "payloads/mn_python_workflow/mn_worker.py"
    worker.write_text(
        '''#!/usr/bin/env python3.11
import importlib
import json
import os
import pathlib
import sys


def _load_input():
    path = pathlib.Path(os.environ["MN_INPUT_FILE"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    return payload.get("args", []), payload.get("kwargs", {})


def main():
    source_dir = pathlib.Path(__file__).resolve().parent / "source"
    sys.path.insert(0, str(source_dir))
    module = importlib.import_module(os.environ["MN_PY_SOURCE_MODULE"])
    owner = getattr(module, os.environ["MN_PY_OWNER_CLASS"])
    method = getattr(owner(), os.environ["MN_PY_METHOD"])
    args, kwargs = _load_input()
    result = method(*args, **kwargs)
    payload = result if isinstance(result, dict) else {"result": result}
    print(json.dumps({
        "complete_step": result,
        "events": [{"type": "python_workflow_result", "payload": payload}],
        "next_state": result,
    }))


if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = workflow.to_bundle(
        DemoPythonSdkWorkflow,
        args.output_dir,
        blueprint_id="demo_python_sdk_workflow",
        include_source_dir=False,
        includes=[root / "payloads/worker/run_store.py"],
        metadata={
            "category": "Execution",
            "runtime_features": ["Python SDK compilation"],
        },
    )

    # Execute the freshly compiled SDK workers through the catalog's current
    # two-step topology. This is the narrow compatibility boundary between the
    # SDK compiler and the Core submission contract.
    manifest_path = output / "manifest.json"
    compiled = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    compiled_nodes = {node["node_id"]: node for node in compiled["agents"]["nodes"]}
    for node, compiled_id, step_id, output_type in (
        (manifest["agents"]["nodes"][0], "normalize", "run", "run_done"),
        (manifest["agents"]["nodes"][1], "summarize", "publish", "final_result"),
    ):
        generated = compiled_nodes[compiled_id]["config"]
        node["config"]["command"] = generated["command"]
        node["config"]["upload_as"] = generated["upload_as"]
        node["config"]["upload_path"] = generated["upload_path"]
        node["config"]["workdir"] = generated["workdir"]
        node["config"]["environment"].update(generated["environment"])
        node["config"]["environment"]["MN_PY_OUTPUT_TYPE"] = output_type
        node["config"]["environment"]["MN_WORKFLOW_STEP_ID"] = step_id

    # Compiled SDK workers can sit briefly behind another local job before
    # Core starts their process. Give the workflow ledger enough time to see
    # the worker beacon and completion event on a busy dev runtime.
    for node in manifest["agents"]["nodes"]:
        config = node["config"]
        config["timeout_seconds"] = max(float(config.get("timeout_seconds") or 0), 60)
        config["beacon_interval_ms"] = max(int(config.get("beacon_interval_ms") or 0), 1000)
        config["beacon_timeout_ms"] = max(int(config.get("beacon_timeout_ms") or 0), 30000)
    for step in manifest["workflow"]["steps"]:
        step.setdefault("control", {})["timeout_seconds"] = 60
    liveness = manifest["runtime"]["workflow_control"]["liveness"]
    liveness["timeout_ms"] = 30000

    first_inputs = compiled["runtime"]["initial_inputs"]["normalize"]
    for item in first_inputs:
        if item.get("kwargs") == {}:
            item.pop("kwargs")
    manifest["runtime"]["initial_inputs"] = {"run": first_inputs}
    manifest["metadata"].update(compiled["metadata"])
    manifest["metadata"]["python_source_mode"] = False
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copytree(root / "config", output / "config", dirs_exist_ok=True)
    _write_runtime_compatible_worker(output)

    print(output)


if __name__ == "__main__":
    main()
