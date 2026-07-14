#!/usr/bin/env python3
"""Run the focused catalog through a live MirrorNeuron runtime.

Runtime operations use public ``mn`` commands. OpenShell preparation uses the
runtime container's CLI because native sandbox preparation is intentionally off
by default. The runner also understands the shared-submission run store, because
output-copy is asynchronous and authoritative artifacts can appear there before
``~/.mn/runs`` is merged.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path


REQUIRED_ARTIFACTS = (
    "run.json",
    "config.json",
    "inputs.json",
    "events.jsonl",
    "errors.jsonl",
    "timeline.jsonl",
    "observability_summary.json",
    "result.json",
    "final_artifact.json",
)

EVIDENCE = {
    "demo_native_beam_agent": ("beam_native", "native_signal_classified"),
    "demo_hostlocal_worker": ("hostlocal",),
    "demo_docker_worker": ("sha256",),
    "demo_openshell_worker": ("deny-all",),
    "demo_python_sdk_workflow": ("demo_python_sdk_workflow",),
    "demo_dag_linear": ("parse", "score", "report"),
    "demo_dag_fork_join": ("east", "west", "central", "join"),
    "demo_dag_scatter_gather": ("mapped_items", "collect"),
    "demo_dag_conditional_branch": ("high_risk", "join"),
    "demo_dag_failure_fallback": ("intentional primary outage", "fallback"),
    "demo_dag_quorum": ("sensor_a", "sensor_b", "approve"),
    "demo_llm_tool_call": ("local_forecast", "tool_trace"),
    "demo_context_memory_acl": ("private_hidden",),
    "demo_context_compression": ("source_refs",),
    "demo_stream_backpressure": ("queue_size", "drop_policy"),
    "demo_executor_pool": ("pool_slots",),
    "demo_resource_allocation": ("allocation",),
    "demo_retry_recovery": ("attempt",),
    "demo_checkpoint_replay": ("duplicates_ignored", "evt-5"),
    "demo_observability_trace": ("trace_id", "span_id"),
}


def run(command: list[str], *, timeout: float = 60, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NO_COLOR": "1", "MN_CLI_OUTPUT": "plain"}
    proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout, env=env)
    if check and proc.returncode:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(command)}\n{proc.stdout}\n{proc.stderr}"
        )
    return proc


def read_json_output(proc: subprocess.CompletedProcess[str]):
    text = (proc.stdout or "").strip()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            return json.loads(text[index:])
        except json.JSONDecodeError:
            pass
    raise RuntimeError(f"command did not return JSON:\n{text}\n{proc.stderr}")


def objects(value) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("data", "items", "schedules", "deployments", "events", "jobs"):
            if isinstance(value.get(key), list):
                return [item for item in value[key] if isinstance(item, dict)]
        return [value]
    return []


def identifier(item: dict, *names: str) -> str:
    for name in names:
        value = item.get(name)
        if value:
            return str(value)
    return ""


def wait_until(predicate, timeout: float, description: str):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except Exception as exc:  # a service may not exist yet
            last = exc
        time.sleep(0.25)
    raise TimeoutError(f"timed out waiting for {description}; last={last!r}")


def locate_run_dir(run_id: str) -> Path | None:
    canonical = Path(os.path.expanduser("~/.mn/runs")) / run_id
    if (canonical / "run.json").is_file():
        return canonical
    shared = Path(os.path.expanduser("~/.mn/shared/submissions"))
    candidates = list(shared.glob(f"{run_id}-*/outputs/runs/{run_id}")) if shared.is_dir() else []
    candidates = [path for path in candidates if path.is_dir()]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def wait_run(run_id: str, timeout: float) -> tuple[Path, dict]:
    def finished():
        run_dir = locate_run_dir(run_id)
        if not run_dir or not (run_dir / "run.json").exists():
            return None
        state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        return (run_dir, state) if state.get("status") in {"completed", "failed", "cancelled"} else None

    return wait_until(finished, timeout, f"run {run_id}")


def assert_run(blueprint_id: str, run_id: str, timeout: float) -> Path:
    run_dir, state = wait_run(run_id, timeout)
    if state.get("status") != "completed":
        raise RuntimeError(f"{blueprint_id} ended as {state.get('status')}")
    missing = [name for name in REQUIRED_ARTIFACTS if not (run_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"{blueprint_id}: missing artifacts {missing}")
    corpus = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in run_dir.iterdir()
        if path.is_file() and path.suffix in {".json", ".jsonl"}
    ).lower()
    runtime_events = Path(os.path.expanduser("~/.mn/runs")) / run_id / "events.jsonl"
    if runtime_events.is_file() and runtime_events.parent != run_dir:
        corpus += "\n" + runtime_events.read_text(encoding="utf-8", errors="replace").lower()
    absent = [token for token in EVIDENCE.get(blueprint_id, ()) if token.lower() not in corpus]
    if absent:
        raise RuntimeError(f"{blueprint_id}: missing feature evidence {absent}")
    if blueprint_id == "demo_context_memory_acl" and not any(
        token in corpus for token in ('"private_hidden": true', '\\"private_hidden\\": true')
    ):
        raise RuntimeError("demo_context_memory_acl: private memory was visible to the auditor")
    return run_dir


def launch(mn: str, folder: Path, run_id: str, timeout: float, *, follow: int = 2):
    return run(
        [mn, "blueprint", "run", "--folder", str(folder), "--offline", "--fake-llm", "--run-id", run_id,
         "--follow-seconds", str(follow)],
        timeout=timeout,
        check=False,
    )


def job_id_from_output(proc: subprocess.CompletedProcess[str]) -> str:
    match = re.search(r"Job ID\s+([A-Za-z0-9_-]+)", proc.stdout or "")
    return match.group(1) if match else ""


@contextmanager
def runtime_bundle(folder: Path, revision: str = ""):
    """Materialize the transport topology expected by direct operator RPCs.

    ``mn blueprint run`` performs this lowering during submission. Schedule and
    deployment commands intentionally accept already-materialized bundles, so
    the suite performs the same catalog-to-Core boundary conversion here.
    """
    with tempfile.TemporaryDirectory(prefix=f"mn-{folder.name}-runtime-") as temp:
        output = Path(temp) / "bundle"
        output.mkdir()
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        workflow = manifest.get("workflow") or {}
        agents = manifest.get("agents") or {}
        if folder.name == "demo_canary_deployment":
            # A deployment service stays active without a terminal sink. Keep
            # only the long-running executor at the operator-RPC boundary so
            # promotion observes a live source job, matching Core's deployment
            # controller contract.
            agents["nodes"] = agents.get("nodes", [])[:1]
            agents["edges"] = []
            agents["entrypoints"] = ["serve"]
            workflow["steps"] = workflow.get("steps", [])[:1]
            workflow["edges"] = []
            workflow["source"] = "serve"
            workflow["sink"] = "serve"
            manifest["runtime"]["bindings"] = {"serve": manifest["runtime"]["bindings"]["serve"]}
        workflow_id = workflow.get("workflow_id")
        if workflow_id:
            manifest["graph_id"] = workflow_id
        flow = {
            "nodes": agents.get("nodes", []),
            "edges": agents.get("edges", []),
            "steps": workflow.get("steps", []),
            "graph": {"edges": workflow.get("edges", [])},
        }
        for key in ("entrypoint", "source", "sink", "mode", "execution", "dynamic", "policy", "state"):
            if key in workflow:
                flow[key] = workflow[key]
        manifest["flow"] = flow
        manifest["entrypoints"] = agents.get("entrypoints", [])
        manifest["initial_inputs"] = (manifest.get("runtime") or {}).get("initial_inputs", {})
        (output / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if (folder / "payloads").is_dir():
            shutil.copytree(folder / "payloads", output / "payloads")
        if revision:
            manifest["metadata"]["demo_revision"] = revision
            for node in manifest.get("agents", {}).get("nodes", []):
                config = node.get("config") if isinstance(node.get("config"), dict) else None
                if config is not None:
                    config.setdefault("environment", {})["MN_DEMO_REVISION"] = revision
            manifest_path = output / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            worker = output / "payloads/worker/worker.py"
            if worker.is_file():
                with worker.open("a", encoding="utf-8") as handle:
                    handle.write(f"\n# materialized demo revision: {revision}\n")
        yield output


def generic_demo(mn: str, blueprint_id: str, folder: Path, timeout: float):
    run_id = f"demo-{blueprint_id.removeprefix('demo_')}-{uuid.uuid4().hex[:8]}"
    proc = launch(mn, folder, run_id, timeout)
    if proc.returncode and not locate_run_dir(run_id):
        raise RuntimeError(proc.stdout + proc.stderr)
    assert_run(blueprint_id, run_id, timeout)


def python_sdk_demo(mn: str, folder: Path, timeout: float):
    executable = Path(shutil.which(mn) or mn)
    python = sys.executable
    try:
        first_line = executable.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        if first_line.startswith("#!") and "python" in first_line:
            python = first_line[2:].strip().split()[0]
    except (OSError, IndexError):
        pass
    with tempfile.TemporaryDirectory(prefix="mn-python-sdk-demo-") as temp:
        bundle = Path(temp) / "bundle"
        run([python, str(folder / "compile_demo.py"), str(bundle)], timeout=timeout)
        run([mn, "blueprint", "validate", str(bundle), "--output", "json"], timeout=timeout)
        run_id = f"demo-python-sdk-{uuid.uuid4().hex[:8]}"
        proc = launch(mn, bundle, run_id, timeout)
        if proc.returncode and not locate_run_dir(run_id):
            raise RuntimeError(proc.stdout + proc.stderr)
        assert_run("demo_python_sdk_workflow", run_id, timeout)


def openshell_demo(mn: str, folder: Path, timeout: float):
    """Prepare one deny-network sandbox and let the runtime reuse it for the job."""
    sandbox_name = f"mn-demo-{uuid.uuid4().hex[:12]}"
    image = "mirror-neuron/demo-openshell-worker:local"
    container_policy = f"/tmp/{sandbox_name}-policy.yaml"
    policy = folder / "payloads/worker/openshell-policy.yaml"
    run(
        ["docker", "build", "--tag", image, str(folder / "payloads/openshell_image")],
        timeout=max(timeout, 300),
    )
    with tempfile.TemporaryDirectory(prefix="mn-openshell-demo-") as temp:
        bundle = Path(temp) / "bundle"
        shutil.copytree(folder, bundle)
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        node = next(node for node in manifest["agents"]["nodes"] if node["node_id"] == "run")
        node["config"].update(
            {
                "reuse_shared_sandbox": True,
                "sandbox_name": sandbox_name,
                "ssh_host": f"openshell-{sandbox_name}",
            }
        )
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        run(["docker", "cp", str(policy), f"mirror-neuron-core:{container_policy}"], timeout=timeout)
        try:
            run(
                [
                    "docker", "exec", "mirror-neuron-core", "openshell", "sandbox", "create",
                    "--name", sandbox_name, "--from", image,
                    "--policy", container_policy, "--no-tty",
                    "--no-auto-providers", "--", "bash", "-lc", "mkdir -p /sandbox/job && true",
                ],
                timeout=max(timeout, 120),
            )
            generic_demo(mn, "demo_openshell_worker", bundle, timeout)
        finally:
            run(
                ["docker", "exec", "mirror-neuron-core", "openshell", "sandbox", "delete", sandbox_name],
                timeout=timeout,
                check=False,
            )
            run(["docker", "exec", "mirror-neuron-core", "rm", "-f", container_policy], check=False)


def human_demo(mn: str, folder: Path, timeout: float):
    run_id = f"demo-human-{uuid.uuid4().hex[:8]}"
    env = {**os.environ, "NO_COLOR": "1", "MN_CLI_OUTPUT": "plain"}
    command = [mn, "blueprint", "run", "--folder", str(folder), "--offline", "--fake-llm",
               "--run-id", run_id, "--follow-seconds", "1"]
    process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    def pending():
        run_dir = locate_run_dir(run_id)
        path = run_dir / "human.jsonl" if run_dir else None
        if not path or not path.exists():
            return None
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("type") == "human_input_requested":
                return run_dir, event["payload"]["request_id"]
        return None

    try:
        run_dir, request_id = wait_until(pending, timeout, "human input request")
        run(
            [mn, "blueprint", "human", "respond", run_id, request_id, "--decision", "approve",
             "--reviewer", "demo-suite", "--runs-root", str(run_dir.parent)],
            timeout=timeout,
        )
        stdout, stderr = process.communicate(timeout=timeout)
        if process.returncode and not locate_run_dir(run_id):
            raise RuntimeError(stdout + stderr)
        final_dir = assert_run("demo_human_approval", run_id, timeout)
        human_text = (final_dir / "human.jsonl").read_text(encoding="utf-8")
        if "human_input_received" not in human_text:
            raise RuntimeError("human response was not recorded")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def schedule_rows(mn: str, kind: str | None = None) -> list[dict]:
    command = [mn, "schedule", "list"]
    if kind:
        command.extend(["--kind", kind])
    return objects(read_json_output(run(command)))


def periodic_demo(mn: str, folder: Path, timeout: float):
    name = f"demo-periodic-{uuid.uuid4().hex[:8]}"
    before = {identifier(row, "schedule_id", "id") for row in schedule_rows(mn)}
    schedule_id = ""
    try:
        with runtime_bundle(folder) as bundle:
            run([mn, "schedule", "create", str(bundle), "--cron", "0 0 * * *", "--name", name], timeout=timeout)
        rows = schedule_rows(mn)
        created = [row for row in rows if identifier(row, "schedule_id", "id") not in before]
        match = next((row for row in created if row.get("name") == name), created[0] if created else None)
        if not match:
            raise RuntimeError("periodic schedule was not registered")
        schedule_id = identifier(match, "schedule_id", "id")
        dispatched = run([mn, "schedule", "run-now", schedule_id], timeout=timeout)
        if "Job ID" not in dispatched.stdout:
            raise RuntimeError("periodic run-now did not create a child job")
    finally:
        if schedule_id:
            run([mn, "schedule", "delete", schedule_id, "--reason", "demo suite cleanup"], check=False)
            if any(identifier(row, "schedule_id", "id") == schedule_id for row in schedule_rows(mn)):
                raise RuntimeError("periodic schedule cleanup failed")


def event_demo(mn: str, folder: Path, timeout: float):
    name = f"demo-trigger-{uuid.uuid4().hex[:8]}"
    event_type = f"demo.match.{uuid.uuid4().hex[:8]}"
    before = {identifier(row, "schedule_id", "id") for row in schedule_rows(mn, "event")}
    schedule_id = ""
    try:
        with runtime_bundle(folder) as bundle:
            run([mn, "trigger", "create", str(bundle), "--event", event_type, "--name", name,
                 "--filter-json", '{"region":"east"}'], timeout=timeout)
        rows = schedule_rows(mn, "event")
        created = [row for row in rows if identifier(row, "schedule_id", "id") not in before]
        match = next((row for row in created if row.get("name") == name), created[0] if created else None)
        if not match:
            raise RuntimeError("event trigger was not registered")
        schedule_id = identifier(match, "schedule_id", "id")
        baseline = int((match.get("counters") or {}).get("dispatched", 0))
        run([mn, "event", "emit", event_type, "--payload-json", '{"region":"west"}'], timeout=timeout)
        time.sleep(0.5)
        after_nonmatch = read_json_output(run([mn, "schedule", "status", schedule_id]))
        if int((after_nonmatch.get("counters") or {}).get("dispatched", 0)) != baseline:
            raise RuntimeError("nonmatching event unexpectedly launched a child job")
        run([mn, "event", "emit", event_type, "--payload-json", '{"region":"east"}'], timeout=timeout)
        after_match = wait_until(
            lambda: (
                status
                if int((status := read_json_output(run([mn, "schedule", "status", schedule_id])))
                       .get("counters", {}).get("dispatched", 0)) == baseline + 1
                else None
            ),
            timeout,
            "matching event child job",
        )
        dispatches = after_match.get("dispatches") or []
        if not dispatches or not dispatches[-1].get("job_id"):
            raise RuntimeError("matching event counter advanced without a child job id")
    finally:
        if schedule_id:
            run([mn, "trigger", "delete", schedule_id, "--reason", "demo suite cleanup"], check=False)
            if any(identifier(row, "schedule_id", "id") == schedule_id for row in schedule_rows(mn, "event")):
                raise RuntimeError("event trigger cleanup failed")


def service_demo(mn: str, folder: Path, timeout: float):
    run_id = f"demo-service-{uuid.uuid4().hex[:8]}"
    proc = launch(mn, folder, run_id, timeout, follow=1)
    job_id = job_id_from_output(proc)
    if not job_id:
        raise RuntimeError(proc.stdout + proc.stderr)
    try:
        wait_until(
            lambda: (result := run([mn, "service", "resolve", "demo-health"], check=False)).returncode == 0
            and "demo-health" in result.stdout,
            timeout,
            "healthy demo service",
        )
    finally:
        run([mn, "job", "cancel", job_id], check=False)
    unresolved = run([mn, "service", "resolve", "demo-health"], check=False)
    if unresolved.returncode == 0 and "demo-health" in unresolved.stdout:
        raise RuntimeError("service remained resolvable after cancellation")


def canary_demo(mn: str, folder: Path, timeout: float):
    key = f"demo-canary-{uuid.uuid4().hex[:8]}"
    job_ids: list[str] = []
    try:
        with runtime_bundle(folder, "stable") as stable_bundle:
            stable = run([mn, "deployment", "deploy", str(stable_bundle), "--key", key,
                          "--strategy", "rolling", "--wait"], timeout=timeout, check=False)
        if stable.returncode:
            raise RuntimeError(stable.stdout + stable.stderr)
        if stable_job := job_id_from_output(stable):
            job_ids.append(stable_job)
        with runtime_bundle(folder, "candidate") as candidate_bundle:
            candidate = run([mn, "deployment", "deploy", str(candidate_bundle), "--key", key,
                              "--strategy", "canary", "--canary", "1", "--wait"],
                             timeout=timeout, check=False)
        if candidate.returncode:
            raise RuntimeError(candidate.stdout + candidate.stderr)
        if candidate_job := job_id_from_output(candidate):
            job_ids.append(candidate_job)
        before = read_json_output(run([mn, "deployment", "status", key]))
        if str(before.get("status", "")).lower() != "awaiting_promotion":
            raise RuntimeError(f"candidate did not remain behind canary gate: {before}")
        run([mn, "deployment", "promote", key], timeout=timeout)
        after = read_json_output(run([mn, "deployment", "status", key]))
        if str(after.get("status", "")).lower() != "successful":
            raise RuntimeError(f"canary was not promoted: {after}")
    finally:
        for job_id in dict.fromkeys(job_ids):
            run([mn, "job", "cancel", job_id], check=False)
        # The current public API has no delete-deployment command; mark the
        # stopped demo deployment failed so it cannot remain an active target.
        run([mn, "deployment", "fail", key, "--reason", "demo suite cleanup"], check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blueprint", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--twice", action="store_true", help="Run selected finite demos twice.")
    parser.add_argument("--mn", default=os.environ.get("MN_CLI", "mn"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root / "index.json").read_text(encoding="utf-8"))
    selected = set(args.blueprint)
    rows = [row for row in rows if not selected or row["id"] in selected]
    run([sys.executable, str(root / "scripts/verify_catalog.py"), "--validate"], timeout=180)
    if args.validate_only:
        print(f"validated {len(rows)} blueprints")
        return
    health = run([args.mn, "runtime", "health", "--json"], check=False)
    if health.returncode:
        raise SystemExit("MirrorNeuron runtime is not healthy; run `mn runtime start` first")
    run([args.mn, "runtime", "ensure-context-engine"], timeout=120, check=False)

    handlers = {
        "demo_openshell_worker": openshell_demo,
        "demo_python_sdk_workflow": python_sdk_demo,
        "demo_human_approval": human_demo,
        "demo_periodic_schedule": periodic_demo,
        "demo_event_trigger": event_demo,
        "demo_service_health": service_demo,
        "demo_canary_deployment": canary_demo,
    }
    for row in rows:
        blueprint_id = row["id"]
        folder = root / row["path"]
        print(f"RUN  {blueprint_id}", flush=True)
        handler = handlers.get(blueprint_id)
        if handler:
            handler(args.mn, folder, args.timeout)
        else:
            generic_demo(args.mn, blueprint_id, folder, args.timeout)
            if args.twice:
                generic_demo(args.mn, blueprint_id, folder, args.timeout)
        print(f"PASS {blueprint_id}", flush=True)


if __name__ == "__main__":
    main()
