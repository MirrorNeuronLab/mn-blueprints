#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mn-python-sdk"))
sys.path.insert(0, str(ROOT / "mn-skills" / "blueprint_support_skill" / "src"))

from mn_blueprint_support import apply_quick_test, log_status, progress
from workflow import GeneralPythonDefinedAdvancedDeamon
from mn_sdk import workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an advanced pure-Python daemon bundle.")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--quick-test", action="store_true")
    args = parser.parse_args()

    quick_test = apply_quick_test(args, {})
    log_status(
        "general_python_defined_advanced_deamon",
        "generating pure Python daemon bundle",
        phase="generate",
        details={"quick_test": quick_test},
    )

    bundle_dir = workflow.to_bundle(
        GeneralPythonDefinedAdvancedDeamon,
        args.output_dir,
        blueprint_id="general_python_defined_advanced_deamon",
        includes=["daemon_helpers.py"],
        metadata={"quick_test": {"enabled": quick_test}},
    )
    print(progress("bundle generated", 1, 1), file=sys.stderr)
    print(bundle_dir)


if __name__ == "__main__":
    main()
