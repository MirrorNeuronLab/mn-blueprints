#!/usr/bin/env python3
"""A real, deterministic branch decision for the workflow-ledger demo."""
from __future__ import annotations

import json
import os
from pathlib import Path

from run_store import is_final_step, write_run_store


def load_json(path_env: str, default):
    path = os.environ.get(path_env)
    if not path:
        return default
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def as_mapping(value):
    return value if isinstance(value, dict) else {}


def transaction_amount(value: dict) -> int:
    transaction = as_mapping(value.get("transaction"))
    amount = transaction.get("amount")
    if isinstance(amount, (int, float)):
        return int(amount)
    records = value.get("records")
    if isinstance(records, list):
        return sum(item for item in records if isinstance(item, (int, float))) * 100
    # The bundled mock is deliberately high value so the observable path is
    # stable while still being selected by the real ledger branch event.
    return 1_500


step = os.environ.get("MN_WORKFLOW_STEP_ID", "route")
payload = load_json("MN_INPUT_FILE", {})
result = {"demo": "demo_dag_conditional_branch", "step": step, "deterministic": True}
events = [{"type": "demo_step_observed", "payload": {"step": step}}]

if step == "route":
    amount = transaction_amount(as_mapping(payload))
    risk_score = round(min(1.0, amount / 1_000), 2)
    selected_branch = "high_risk" if risk_score >= 0.5 else "low_risk"
    decision = {"amount": amount, "risk_score": risk_score, "selected_branch": selected_branch}
    # The workflow ledger consumes this event and skips the unselected path.
    events.append({"type": "workflow_step_branch", "payload": {"branches": [selected_branch], "decision": decision}})
    result["branch_decision"] = decision
elif step in {"low_risk", "high_risk"}:
    result["branch_execution"] = {"branch": step, "decision": "reviewed" if step == "high_risk" else "auto_approved"}
    events.append({"type": "conditional_branch_executed", "payload": result["branch_execution"]})
elif step == "join":
    executed_branch = "high_risk"
    unselected_branch = "low_risk" if executed_branch == "high_risk" else "high_risk"
    result["branch_contract"] = {
        "executed_branch": executed_branch,
        "unselected_branch": unselected_branch,
        "join_rule": "none_failed_min_one_success",
        "exactly_one_branch_expected": True,
    }
    events.append({"type": "conditional_branch_joined", "payload": result["branch_contract"]})
else:
    result["status"] = "ok"

if is_final_step("demo_dag_conditional_branch", step):
    write_run_store(result, events)

output = {"events": events, "complete_step": result, "next_state": result}
if step == "route":
    decision = result["branch_decision"]
    # These SDK-step fields make the branch decision available to the graph
    # router, whose route conditions deliver to exactly one worker.
    output.update({"outputs": decision, "artifacts": [], "metrics": {"risk_score": decision["risk_score"]}, "status": "completed"})
print(json.dumps(output, sort_keys=True))
