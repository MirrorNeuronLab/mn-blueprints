#!/usr/bin/env python3.11
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone


FEATURE_MATRIX = {
    "placement": ["scheduler", "resources", "constraints", "services"],
    "service": ["restart", "reschedule", "cluster_recover", "idempotency"],
    "drain": ["batch_wait", "deadline", "migration", "maintenance"],
    "review": ["manual_recover", "unsafe_side_effects", "operator_gate"],
}


def build_report(phase: str) -> dict:
    features = [item for item in os.environ.get("MN_RELIABILITY_DEMO_FEATURES", "").split(",") if item]
    if not features:
        features = FEATURE_MATRIX.get(phase, [])
    return {
        "blueprint": "demo_cluster_reliability_service",
        "phase": phase,
        "status": "completed",
        "features": features,
        "job_types": ["service", "batch", "system", "sysbatch"],
        "scheduler_strategies": ["spread", "binpack"],
        "recovery_modes": ["cluster_recover", "local_restart", "manual_recover"],
        "operator_checks": [
            "mn nodes shows both runtime nodes",
            "mn status shows scheduler placements and reliability policy",
            "mn drain-node dry-run returns actions without consuming reschedule attempts",
            "mn maintenance-node disables and restores scheduling eligibility",
        ],
        "safe_to_retry": phase in {"placement", "service", "drain"},
        "idempotency_key": f"mn-reliability-demo-{phase}-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a deterministic cluster reliability demo report.")
    parser.add_argument("--phase", default=os.environ.get("MN_RELIABILITY_DEMO_PHASE", "placement"))
    parser.add_argument("--health-check", action="store_true")
    args = parser.parse_args()
    if args.health_check:
        print(json.dumps({"status": "passing", "service": "mn-reliability-planner"}, sort_keys=True))
        return
    print(json.dumps(build_report(args.phase), sort_keys=True))


if __name__ == "__main__":
    main()
