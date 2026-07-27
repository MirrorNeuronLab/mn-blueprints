#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time

from mn_mcp_client_skill import (
    discover_mcp_job_servers,
    get_mcp_job_snapshot,
    get_mcp_job_updates,
)
from mn_sdk import Client

from common import config, exchange_store, output_root, write_json


collaboration = config()["collaboration"]
store = exchange_store()
deadline = time.monotonic() + float(collaboration["discover_seconds"])
poll_interval = max(float(collaboration["poll_interval_seconds"]), 0.05)
token_env = str(collaboration.get("bearer_token_env") or "")
bearer_token_env = token_env if token_env and os.environ.get(token_env) else None
peer_records: list[dict] = []
last_discovery: dict = {"status": "ok", "servers": [], "warnings": []}
runtime_client = Client(timeout=2)

while time.monotonic() < deadline and not peer_records:
    last_discovery = discover_mcp_job_servers(
        runtime_client=runtime_client,
        service_name=str(collaboration["service_name"]),
        tags=["mcp", "job-collaboration", "demo_mcp_collaboration"],
        goal_id=str(collaboration["goal_id"]),
        exclude_job_id=store.identity["job_id"],
        bearer_token_env=bearer_token_env,
        timeout_seconds=2,
        max_servers=8,
    )
    for peer in last_discovery.get("servers") or []:
        snapshot = get_mcp_job_snapshot(
            peer["config"],
            include_staged=True,
            limit=100,
        )
        updates = get_mcp_job_updates(
            peer["config"],
            after_revision=0,
            include_staged=True,
            limit=100,
        )
        if snapshot.get("status") == "ok" and updates.get("status") == "ok":
            peer_records.append(
                {
                    "job_id": peer["job_id"],
                    "goal_id": peer["goal_id"],
                    "snapshot": snapshot["snapshot"],
                    "updates": updates["updates"],
                }
            )
    if not peer_records:
        time.sleep(poll_interval)

if bool(collaboration.get("require_peer")) and not peer_records:
    store.publish_status(
        "failed",
        stage="collaboration",
        summary="No peer MCP service became available before the deadline.",
        publication_state="final",
        idempotency_key="peer-required-failed-v1",
    )
    raise RuntimeError(
        f"required peer was not found; discovery={last_discovery.get('error') or last_discovery.get('warnings')}"
    )

saw_staged = any(
    update.get("kind") == "result"
    and update.get("publication_state") == "staged"
    for peer in peer_records
    for update in peer["updates"].get("updates", [])
)
peer_job_ids = sorted({str(peer["job_id"]) for peer in peer_records})
exchange = {
    "schema_version": "mn.demo.mcp_peer_exchange.v1",
    "job_id": store.identity["job_id"],
    "goal_id": collaboration["goal_id"],
    "peer_count": len(peer_records),
    "peer_job_ids": peer_job_ids,
    "saw_staged_peer_result": saw_staged,
    "peers": peer_records,
    "discovery_warnings": last_discovery.get("warnings") or [],
}
write_json(output_root() / "peer_exchange.json", exchange)
store.publish_result(
    "collaboration-result",
    {
        "role": collaboration["role"],
        "state": "complete",
        "peer_job_ids": peer_job_ids,
        "saw_staged_peer_result": saw_staged,
    },
    stage="collaboration",
    summary="Final bounded collaboration result.",
    publication_state="final",
    idempotency_key=f"{collaboration['role']}-final-v1",
)
store.publish_status(
    "collaborated",
    stage="collaboration",
    progress=0.9,
    summary=f"Read {len(peer_records)} peer MCP exchange(s).",
    metadata={"peer_job_ids": peer_job_ids},
    publication_state="final",
    idempotency_key="collaboration-status-v1",
)

print(
    json.dumps(
        {
            "events": [
                {
                    "type": "mcp_peer_discovered",
                    "payload": {
                        "peer_count": len(peer_records),
                        "peer_job_ids": peer_job_ids,
                    },
                },
                {
                    "type": "mcp_peer_snapshot_read",
                    "payload": {"saw_staged_peer_result": saw_staged},
                },
            ],
            "complete_step": exchange,
            "next_state": exchange,
        },
        sort_keys=True,
    )
)
