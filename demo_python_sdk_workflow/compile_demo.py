#!/usr/bin/env python3
"""Compile the decorated workflow into a temporary runnable bundle."""
from __future__ import annotations

import argparse
from pathlib import Path

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

    print(output)


if __name__ == "__main__":
    main()
