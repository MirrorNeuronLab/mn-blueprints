from __future__ import annotations

import json
import os
import uuid

import grpc

import context_pb2
import context_pb2_grpc


def _target():
    return os.environ.get("MN_CONTEXT_ADDR") or os.environ.get("CONTEXT_ENGINE_ADDR") or "mirror-neuron-context-engine:50052"


def _stub():
    channel = grpc.insecure_channel(_target())
    grpc.channel_ready_future(channel).result(timeout=5)
    return context_pb2_grpc.ContextEngineStub(channel)


def _add(stub, job_id, item_id, payload, roles):
    content = {"goal_id": "goal-1", "artifact_type": "demo_fact", "payload": payload, "source_refs": [f"source:{item_id}"], "acl": {"allow_roles": roles}}
    response = stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=context_pb2.MemoryItem(id=item_id, type="Fact", content_json=json.dumps(content, sort_keys=True), status="validated", confidence=1.0, source="mn-blueprints", version=1)))
    if not response.success:
        raise RuntimeError(f"AddItem failed: {item_id}")


def run_acl_demo(context):
    stub = _stub()
    job_id = f"acl-{context.get('job_id') or uuid.uuid4().hex}"
    _add(stub, job_id, "shared", {"value": "shared"}, ["operator", "auditor"])
    _add(stub, job_id, "private", {"value": "private"}, ["operator"])
    response = stub.GetContext(context_pb2.GetContextRequest(job_id=job_id, agent_role="auditor", focus_id="shared", max_items=10))
    visible = [item.id for item in response.items]
    return {"job_id": job_id, "auditor_visible_ids": visible, "private_hidden": "private" not in visible, "context_engine": _target()}


def run_compression_demo(context):
    stub = _stub()
    job_id = f"compress-{context.get('job_id') or uuid.uuid4().hex}"
    for index in range(8):
        _add(stub, job_id, f"fact-{index}", {"value": "runtime evidence " * 30, "index": index}, ["operator"])
    response = stub.CompileContext(context_pb2.CompileContextRequest(job_id=job_id, agent_role="operator", focus_id="fact-0", max_items=8, token_budget=512, target_tokens=160, use_model_compression=False, objective="Preserve the goal and source references.", current_subtask="Summarize runtime evidence."))
    packet = json.loads(response.packet_json or "{}")
    rendered = json.dumps(packet, sort_keys=True)
    return {"job_id": job_id, "compressed": response.compressed, "estimated_input_tokens": response.estimated_input_tokens, "estimated_output_tokens": response.estimated_output_tokens, "goal_preserved": "goal-1" in rendered, "source_refs_preserved": "source:" in rendered, "context_engine": _target()}
