#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time

from common import config, exchange_store, output_root


collaboration = config()["collaboration"]
store = exchange_store()
port = int(collaboration["port"])
host = str(collaboration["host"])
serve_seconds = float(collaboration["serve_seconds"])
command = [
    sys.executable,
    "-m",
    "mn_mcp_server_skill",
    "--store",
    str(store.path),
    "--allowed-root",
    str(output_root()),
    "--job-id",
    store.identity["job_id"],
    "--blueprint-id",
    store.identity.get("blueprint_id", ""),
    "--run-id",
    store.identity.get("run_id", ""),
    "--goal-id",
    store.identity.get("goal_id", ""),
    "--host",
    host,
    "--port",
    str(port),
    "--path",
    str(collaboration["mcp_path"]),
]
process = subprocess.Popen(
    command,
    env=dict(os.environ),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
ready = False
started_at = time.monotonic()
deadline = started_at + min(5.0, serve_seconds)
while time.monotonic() < deadline and process.poll() is None:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            ready = True
            break
    except OSError:
        time.sleep(0.1)

if not ready:
    process.terminate()
    process.wait(timeout=5)
    raise RuntimeError("job MCP server did not become ready")

remaining = max(0.0, started_at + serve_seconds - time.monotonic())
time.sleep(remaining)
process.terminate()
try:
    process.wait(timeout=5)
except subprocess.TimeoutExpired:
    process.kill()
    process.wait(timeout=5)

result = {
    "job_id": store.identity["job_id"],
    "goal_id": store.identity.get("goal_id"),
    "mcp_url": f"http://{collaboration['advertise_host']}:{port}{collaboration['mcp_path']}",
    "ready": ready,
    "served_seconds": serve_seconds,
}
print(
    json.dumps(
        {
            "events": [{"type": "mcp_job_server_stopped", "payload": result}],
            "complete_step": result,
            "next_state": result,
        },
        sort_keys=True,
    )
)
