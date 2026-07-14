#!/usr/bin/env python3
"""Submit this complete DAG bundle to the running MirrorNeuron Core service."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from mn_cli.shared import client
from mn_sdk.bundle_io import read_bundle


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait", action="store_true", help="wait for the DAG job to finish")
    parser.add_argument("--timeout", type=float, default=90, help="maximum seconds to wait (default: 90)")
    args = parser.parse_args()

    bundle_dir = Path(__file__).resolve().parent
    manifest_json, payloads = read_bundle(bundle_dir)
    job_id = client.submit_job(manifest_json, payloads)
    print(json.dumps({"job_id": job_id, "payload_count": len(payloads), "status": "submitted"}))

    if not args.wait:
        return 0

    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        job = json.loads(client.get_job(job_id))
        summary = job.get("summary") if isinstance(job.get("summary"), dict) else {}
        status = str(job.get("status") or summary.get("status") or "unknown")
        if status in TERMINAL_STATUSES:
            print(json.dumps({"job_id": job_id, "status": status, "job": job}, sort_keys=True))
            return 0 if status == "completed" else 1
        time.sleep(1)

    print(json.dumps({"job_id": job_id, "status": "timeout"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
