#!/usr/bin/env python3
"""Execute the bundled worker in OpenShell and export its verified HTML to host."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "mirror-neuron/demo-openshell-code-generation:local"


def command(args, *, capture=False, timeout=900):
    result = subprocess.run(args, text=True, capture_output=capture, timeout=timeout)
    if result.returncode:
        if capture:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {args[0]}")
    return result.stdout if capture else ""


def export_result(envelope, output):
    result = envelope["complete_step"]
    if result.get("status") != "completed" or result.get("runner") != "openshell":
        raise ValueError("Worker did not complete inside OpenShell")
    content = base64.b64decode(result["artifact"]["content_base64"], validate=True)
    if len(content) > 250_000 or hashlib.sha256(content).hexdigest() != result["artifact"]["sha256"]:
        raise ValueError("Invalid or oversized exported artifact")
    output.mkdir(parents=True, exist_ok=True)
    page = output / "index.html"
    page.write_bytes(content)
    summary = {key: value for key, value in result.items() if key != "artifact"}
    summary["artifact"] = {key: value for key, value in result["artifact"].items() if key != "content_base64"}
    (output / "run.json").write_text(json.dumps(summary, indent=2) + "\n")
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Override the configured provider/model")
    parser.add_argument("--runtime-container", help="Use OpenShell installed in this local Docker container")
    parser.add_argument("--gateway-endpoint", help="Optional explicit OpenShell gateway URL")
    parser.add_argument("--openshell-bin", default="openshell")
    parser.add_argument("--provider", action="append", default=[], help="Attach an existing OpenShell provider")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--keep-sandbox", action="store_true")
    parser.add_argument("--output", type=Path, default=Path.home() / "Download/demo_openshell_code_generation")
    args = parser.parse_args()
    config = json.loads((ROOT / "config/default.json").read_text())
    if args.model:
        config["opencode"]["model"] = args.model
    timeout = config["opencode"]["timeout_seconds"] + 60
    sandbox = "pizza-codegen-" + uuid.uuid4().hex[:12]
    stage = "/tmp/" + sandbox
    client = (["docker", "exec", "-i", args.runtime_container, args.openshell_bin]
              if args.runtime_container else [args.openshell_bin])
    if not args.runtime_container and not shutil.which(args.openshell_bin):
        raise RuntimeError("OpenShell CLI is unavailable; supply --openshell-bin or --runtime-container")
    if args.gateway_endpoint:
        client += ["--gateway-endpoint", args.gateway_endpoint]
    created = False
    staged = False
    try:
        if not args.skip_build:
            command(["docker", "build", "--progress=plain", "-t", IMAGE,
                     str(ROOT / "payloads/openshell_image")])
        worker = str(ROOT / "payloads/worker")
        skills = str(ROOT / "payloads/skills")
        policy = str(ROOT / "payloads/worker/openshell-policy.yaml")
        if args.runtime_container:
            command(["docker", "exec", args.runtime_container, "mkdir", "-p", stage])
            staged = True
            command(["docker", "cp", worker, f"{args.runtime_container}:{stage}/worker"])
            command(["docker", "cp", skills, f"{args.runtime_container}:{stage}/skills"])
            worker, policy = stage + "/worker", stage + "/worker/openshell-policy.yaml"
            skills = stage + "/skills"
        create = client + ["sandbox", "create", "--name", sandbox, "--from", IMAGE,
                           "--policy", policy, "--no-auto-providers", "--no-tty"]
        for provider in args.provider:
            create += ["--provider", provider]
        command(create + ["--", "bash", "-lc", "mkdir -p /sandbox/job && true"])
        created = True
        command(client + ["sandbox", "upload", sandbox, worker, "/sandbox/job"])
        command(client + ["sandbox", "upload", sandbox, skills, "/sandbox/job"])
        print(f"Running OpenCode in OpenShell sandbox {sandbox}", flush=True)
        stdout = command(client + [
            "sandbox", "exec", "--name", sandbox, "--workdir", "/sandbox/job/worker",
            "--timeout", str(timeout), "--no-tty", "--", "env",
            "MN_DEMO_STANDALONE=1", "MN_BLUEPRINT_CONFIG_JSON=" + json.dumps(config), "python3", "worker.py",
        ], capture=True, timeout=timeout + 30)
        # Match the blueprint's second stage: independently read and verify the
        # persisted artifact in the same sandbox without another model call.
        stdout = command(client + [
            "sandbox", "exec", "--name", sandbox, "--workdir", "/sandbox/job/worker",
            "--timeout", "60", "--no-tty", "--", "env",
            "MN_DEMO_STANDALONE=1", "MN_BLUEPRINT_CONFIG_JSON=" + json.dumps(config), "python3", "worker.py", "--verify-only",
        ], capture=True, timeout=90)
        envelope = json.loads(stdout.strip())
        page = export_result(envelope, args.output.resolve())
        (args.output / "worker_response.json").write_text(stdout)
        print(f"Generated {page}\nModel: {envelope['complete_step']['model']}")
        if args.keep_sandbox:
            print(f"Sandbox retained: {sandbox}")
    finally:
        if created and not args.keep_sandbox:
            command(client + ["sandbox", "delete", sandbox], timeout=60)
        if staged:
            command(["docker", "exec", args.runtime_container, "rm", "-rf", stage], timeout=30)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
