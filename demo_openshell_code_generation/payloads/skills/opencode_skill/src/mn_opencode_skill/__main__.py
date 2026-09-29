from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .opencode import DEFAULT_MODEL, OpenCodeError, OpenCodeRequest, run_opencode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpenCode in an OpenShell worker folder.")
    parser.add_argument("--folder", required=True)
    prompt = parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt")
    prompt.add_argument("--prompt-file", type=Path)
    parser.add_argument("--mode", choices=("generate", "edit", "review"), default="generate")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sandbox-root", default="/sandbox/job")
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--max-output-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--binary", default="opencode")
    parser.add_argument("--result-file", type=Path)
    args = parser.parse_args()
    try:
        if args.prompt_file and args.prompt_file.stat().st_size > 128 * 1024:
            raise ValueError("prompt file exceeds 128 KiB")
        text = args.prompt_file.read_text(encoding="utf-8") if args.prompt_file else args.prompt
        result = run_opencode(OpenCodeRequest(
            folder=args.folder, prompt=text, mode=args.mode, model=args.model,
            sandbox_root=args.sandbox_root, timeout_seconds=args.timeout_seconds,
            max_output_bytes=args.max_output_bytes,
        ), binary=args.binary)
        serialized = json.dumps(result.as_dict(), ensure_ascii=False, indent=2) + "\n"
        if args.result_file:
            args.result_file.write_text(serialized, encoding="utf-8")
        print(serialized, end="")
        return 0
    except (OpenCodeError, ValueError, OSError) as exc:
        print(f"OpenCode failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
