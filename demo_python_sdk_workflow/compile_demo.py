#!/usr/bin/env python3
"""Compile the decorated workflow into a temporary runnable bundle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from mn_sdk import workflow

from workflow import DemoPythonSdkWorkflow


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
    first_inputs = compiled["runtime"]["initial_inputs"]["normalize"]
    for item in first_inputs:
        if item.get("kwargs") == {}:
            item.pop("kwargs")
    manifest["runtime"]["initial_inputs"] = {"run": first_inputs}
    manifest["metadata"].update(compiled["metadata"])
    manifest["metadata"]["python_source_mode"] = False
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copytree(root / "config", output / "config", dirs_exist_ok=True)

    print(output)


if __name__ == "__main__":
    main()
