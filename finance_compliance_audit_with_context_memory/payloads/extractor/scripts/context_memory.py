import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import grpc

import context_pb2
import context_pb2_grpc


ALL_ROLES = [
    "policy_interpreter",
    "evidence_extractor",
    "risk_classifier",
    "decision_agent",
    "critic_auditor",
]

TRACE_ROLES = ["decision_agent", "critic_auditor"]


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        event = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            event.update(structured)
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, sort_keys=True, default=str)


_CONTEXT_LOGGER = None


def context_logging_enabled():
    return os.environ.get("MN_CONTEXT_VIEW_LOG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_context_logger():
    global _CONTEXT_LOGGER
    if _CONTEXT_LOGGER is not None:
        return _CONTEXT_LOGGER

    logger = logging.getLogger("mn.context_view")
    logger.setLevel(os.environ.get("MN_CONTEXT_VIEW_LOG_LEVEL", "INFO").upper())
    logger.propagate = False

    if not logger.handlers:
        formatter = JsonLogFormatter()
        destination = os.environ.get("MN_CONTEXT_VIEW_LOG_DEST", "both").strip().lower()

        if destination in {"stdout", "both", "cloud"}:
            stream_handler = logging.StreamHandler(sys.stderr)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        if destination in {"file", "both"}:
            log_file = Path(os.environ.get("MN_CONTEXT_VIEW_LOG_FILE", "/tmp/mn-context-agent/context_views.jsonl"))
            log_file.parent.mkdir(parents=True, exist_ok=True)
            max_bytes = int(os.environ.get("MN_CONTEXT_VIEW_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
            backup_count = int(os.environ.get("MN_CONTEXT_VIEW_LOG_BACKUP_COUNT", "5"))
            file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    _CONTEXT_LOGGER = logger
    return logger


def content_for_log(content):
    return {key: value for key, value in content.items() if key != "acl"}


def log_context_view(job_id, role, focus_id, max_items, items):
    if not context_logging_enabled():
        return

    payload = {
        "event": "agent_context_view",
        "job_id": job_id,
        "agent_role": role,
        "focus_id": focus_id,
        "max_items": max_items,
        "returned_count": len(items),
        "items": [
            {
                "id": item["id"],
                "type": item["type"],
                "artifact_type": item["artifact_type"],
                "status": item["status"],
                "source": item["source"],
                "confidence": item["confidence"],
                "version": item["version"],
                "content": content_for_log(item["content"]),
            }
            for item in items
        ],
    }
    get_context_logger().info("agent received context", extra={"structured": payload})


def parse_json_payload(raw):
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    for line in reversed(str(raw).splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return json.loads(raw)


def load_input():
    input_file = os.environ.get("MIRROR_NEURON_INPUT_FILE")
    if not input_file:
        return {}

    data = json.loads(Path(input_file).read_text())
    if "sandbox" in data and "stdout" in data["sandbox"]:
        return parse_json_payload(data["sandbox"]["stdout"])
    return data.get("input", data)


def context_stub():
    endpoint = os.environ.get("CONTEXT_ENGINE_ADDR", "host.docker.internal:50052")
    channel = grpc.insecure_channel(endpoint)
    return context_pb2_grpc.ContextEngineStub(channel)


def acl(allow_roles, projection_fields=None):
    fields = projection_fields or [
        "goal_id",
        "artifact_type",
        "payload",
        "source_refs",
        "validation",
        "trace",
    ]
    return {
        "allow_roles": allow_roles,
        "projections": {role: fields for role in allow_roles},
    }


def make_content(
    goal_id,
    artifact_type,
    payload,
    allow_roles,
    source_refs=None,
    validation=None,
    trace=None,
    projection_fields=None,
):
    return {
        "goal_id": goal_id,
        "artifact_type": artifact_type,
        "payload": payload,
        "source_refs": source_refs or [],
        "validation": validation or {},
        "trace": trace or {},
        "acl": acl(allow_roles, projection_fields),
    }


def add_item(
    stub,
    job_id,
    item_id,
    item_type,
    status,
    source,
    content,
    confidence=1.0,
    embedding=None,
):
    item = context_pb2.MemoryItem(
        id=item_id,
        type=item_type,
        status=status,
        source=source,
        confidence=confidence,
        content_json=json.dumps(content, sort_keys=True),
        embedding=embedding or [],
        version=1,
    )
    response = stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=item))
    if hasattr(response, "success") and not response.success:
        raise RuntimeError(f"AddItem failed for {item_id}")
    return item_id


def get_item(stub, job_id, item_id):
    return stub.GetItem(context_pb2.GetItemRequest(job_id=job_id, item_id=item_id)).item


def transition_item(stub, job_id, item_id, status=None, content=None, confidence=None):
    current = get_item(stub, job_id, item_id)
    kwargs = {
        "job_id": job_id,
        "item_id": item_id,
        "expected_version": current.version,
    }
    if status is not None:
        kwargs["status"] = status
    if content is not None:
        kwargs["content_json"] = json.dumps(content, sort_keys=True)
    if confidence is not None:
        kwargs["confidence"] = confidence

    response = stub.UpdateItem(context_pb2.UpdateItemRequest(**kwargs))
    if not response.success:
        raise RuntimeError(f"UpdateItem failed for {item_id}: {response.error_message}")
    return response.new_version


def link_items(stub, job_id, source_id, target_id, relation):
    response = stub.LinkItems(
        context_pb2.LinkItemsRequest(
            job_id=job_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
        )
    )
    if hasattr(response, "success") and not response.success:
        raise RuntimeError(f"LinkItems failed: {source_id} -[{relation}]-> {target_id}")


def get_context(stub, job_id, role, focus_id, max_items=12):
    response = stub.GetContext(
        context_pb2.GetContextRequest(
            job_id=job_id,
            agent_role=role,
            focus_id=focus_id,
            max_items=max_items,
        )
    )
    items = []
    for item in response.items:
        content = parse_json_payload(item.content_json) if item.content_json else {}
        items.append(
            {
                "id": item.id,
                "type": item.type,
                "status": item.status,
                "source": item.source,
                "confidence": item.confidence,
                "version": item.version,
                "artifact_type": content.get("artifact_type"),
                "content": content,
            }
        )
    log_context_view(job_id, role, focus_id, max_items, items)
    return items


def require_artifact(items, artifact_type):
    matches = [item for item in items if item["artifact_type"] == artifact_type]
    if not matches:
        seen = [item["artifact_type"] or item["type"] for item in items]
        raise RuntimeError(f"Missing required artifact {artifact_type}; saw {seen}")
    return matches[0]


def context_summary(items):
    lines = []
    for item in items:
        visible_content = {
            key: value
            for key, value in item["content"].items()
            if key != "acl"
        }
        lines.append(
            f"[{item['id']} {item['type']}/{item['artifact_type']} "
            f"status={item['status']} confidence={item['confidence']:.2f}] "
            f"{json.dumps(visible_content, sort_keys=True)}"
        )
    return "\n".join(lines)


def call_llm(system_prompt, user_prompt, mock_response):
    quick_mode = os.environ.get("MN_BLUEPRINT_QUICK_TEST", "").strip().lower() in {"1", "true", "yes", "on"}
    if quick_mode:
        get_context_logger().info("quick test mode enabled; using mock LLM response")
        return mock_response if isinstance(mock_response, dict) else json.dumps(mock_response)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        get_context_logger().warning("OPENAI_API_KEY not set; falling back to mock response")
        return mock_response
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        return parse_json_payload(response.choices[0].message.content)
    except Exception as exc:
        get_context_logger().exception("LLM error; falling back to mock")
        return mock_response


def add_trace_event(stub, job_id, focus_id, role, event_name, input_refs, output_refs, note):
    event_id = f"trace_{role}_{event_name}"
    content = make_content(
        goal_id=focus_id,
        artifact_type="audit_trace",
        payload={
            "event": event_name,
            "role": role,
            "note": note,
            "input_refs": input_refs,
            "output_refs": output_refs,
        },
        allow_roles=TRACE_ROLES,
        source_refs=input_refs + output_refs,
        validation={"traceable": True},
    )
    add_item(stub, job_id, event_id, "Fact", "validated", role, content, confidence=1.0)
    link_items(stub, job_id, focus_id, event_id, "records_event")
    return event_id


def emit_state(source, **updates):
    state = dict(source)
    artifact_ids = dict(source.get("artifact_ids", {}))
    artifact_ids.update(updates.pop("artifact_ids", {}))
    state["artifact_ids"] = artifact_ids
    state.update(updates)
    print(json.dumps(state, sort_keys=True))


def snapshot_if_configured(stub, job_id, source):
    redis_url = source.get("redis_url") or os.environ.get("CONTEXT_REDIS_URL")
    if not redis_url:
        return None
    response = stub.Snapshot(context_pb2.SnapshotRequest(job_id=job_id, redis_url=redis_url))
    if hasattr(response, "success") and not response.success:
        raise RuntimeError("Snapshot failed")
    return redis_url
