#!/usr/bin/env python3
from __future__ import annotations

import json
import os

from common import config, exchange_store, load_json_file, output_root, write_json
from run_store import write_run_store


def start() -> dict:
    collaboration = config()["collaboration"]
    role = str(collaboration["role"])
    store = exchange_store()
    status = store.publish_status(
        "working",
        stage="bootstrap",
        progress=0.1,
        summary=f"{role} job opened its collaboration exchange.",
        metadata={"role": role},
        idempotency_key="bootstrap-status-v1",
    )
    knowledge = store.publish_knowledge(
        f"{role}-brief",
        {
            "role": role,
            "goal_id": collaboration["goal_id"],
            "claim": f"{role} is contributing deterministic evidence to the shared goal.",
        },
        stage="bootstrap",
        summary="Synthetic role brief for peer jobs.",
        idempotency_key=f"{role}-brief-v1",
    )
    staged = store.publish_result(
        "collaboration-result",
        {
            "role": role,
            "state": "draft",
            "finding": f"Provisional {role} contribution.",
        },
        stage="draft",
        summary="A deliberately staged result that peers may inspect.",
        publication_state="staged",
        idempotency_key=f"{role}-draft-v1",
    )
    return {
        "job_id": store.identity["job_id"],
        "goal_id": collaboration["goal_id"],
        "role": role,
        "revisions": [status["revision"], knowledge["revision"], staged["revision"]],
        "publication_state": staged["publication_state"],
    }


def join() -> dict:
    store = exchange_store()
    collaboration = config()["collaboration"]
    role = str(collaboration["role"])
    peer_path = output_root() / "peer_exchange.json"
    peer_exchange = load_json_file(peer_path, {"peers": [], "peer_count": 0})
    final_result = {
        "job_id": store.identity["job_id"],
        "goal_id": collaboration["goal_id"],
        "role": role,
        "peer_count": int(peer_exchange.get("peer_count") or 0),
        "peer_job_ids": peer_exchange.get("peer_job_ids") or [],
        "saw_staged_peer_result": bool(peer_exchange.get("saw_staged_peer_result")),
    }
    store.publish_status(
        "completed",
        stage="finalize",
        progress=1.0,
        summary="The bounded collaboration window completed.",
        metadata={"peer_count": final_result["peer_count"]},
        publication_state="final",
        idempotency_key="final-status-v1",
    )
    snapshot = store.snapshot()
    updates = store.updates()
    result = {
        "mcp_collaboration": final_result,
        "local_exchange": snapshot,
        "local_updates": updates,
        "peer_exchange": peer_exchange,
    }
    write_run_store(
        result,
        [
            {
                "type": "mcp_exchange_published",
                "payload": {
                    "job_id": store.identity["job_id"],
                    "revision": snapshot["revision"],
                },
            },
            {
                "type": "mcp_peer_snapshot_read",
                "payload": {
                    "peer_count": final_result["peer_count"],
                    "saw_staged_peer_result": final_result["saw_staged_peer_result"],
                },
            },
        ],
    )
    return result


step = os.environ.get("MN_WORKFLOW_STEP_ID", "start")
if step == "start":
    value = start()
elif step == "join":
    value = join()
else:
    raise RuntimeError(f"worker.py does not implement step {step}")

print(
    json.dumps(
        {
            "events": [
                {
                    "type": "mcp_demo_step_completed",
                    "payload": {"step": step, "job_id": os.environ.get("MN_JOB_ID", "")},
                }
            ],
            "complete_step": value,
            "next_state": value,
        },
        sort_keys=True,
    )
)
