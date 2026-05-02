import json
import logging
import os
import sys
import urllib.error
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

import grpc

import context_pb2
import context_pb2_grpc

try:
    from mn_context_engine_sdk import MNMemoryItem
except Exception:
    MNMemoryItem = None


ALL_ROLES = [
    "context_researcher",
    "context_expander",
    "constraint_challenger",
    "context_compressor",
    "briefing_author",
]

TRACE_ROLES = ALL_ROLES


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


def first_env(*names, default=""):
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def env_int(*names, default=0):
    value = first_env(*names)
    if not value:
        return default
    return int(value)


def env_bool(*names, default=False):
    value = first_env(*names)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


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


def ensure_json_object(value, fallback):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = parse_json_payload(value)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return fallback if isinstance(fallback, dict) else {"value": fallback}


def load_input():
    input_file = os.environ.get("MIRROR_NEURON_INPUT_FILE")
    if not input_file:
        return {}

    data = json.loads(Path(input_file).read_text())
    if "sandbox" in data and "stdout" in data["sandbox"]:
        return parse_json_payload(data["sandbox"]["stdout"])
    return data.get("input", data)


def context_stub():
    configured = first_env("MN_CONTEXT_ADDR", "CONTEXT_ENGINE_ADDR")
    ready_timeout = float(
        first_env(
            "MN_CONTEXT_READY_TIMEOUT_SECONDS",
            "CONTEXT_ENGINE_READY_TIMEOUT_SECONDS",
            default="0.5",
        )
    )
    candidates = [
        configured,
        "localhost:50052",
        "127.0.0.1:50052",
        "host.docker.internal:50052",
    ]
    endpoints = [
        endpoint
        for index, endpoint in enumerate(candidates)
        if endpoint and endpoint not in candidates[:index]
    ]
    errors = []

    for endpoint in endpoints:
        channel = grpc.insecure_channel(endpoint)
        try:
            grpc.channel_ready_future(channel).result(timeout=ready_timeout)
            return context_pb2_grpc.ContextEngineStub(channel)
        except Exception as exc:
            channel.close()
            reason = str(exc) or exc.__class__.__name__
            errors.append(f"{endpoint}: {reason}")

    raise RuntimeError(
        "Context Engine is unavailable. Start it on port 50052 or set MN_CONTEXT_ADDR. "
        f"Tried: {'; '.join(errors)}"
    )


def acl(allow_roles, projection_fields=None):
    fields = projection_fields or [
        "goal_id",
        "artifact_type",
        "payload",
        "source_refs",
        "validation",
        "trace",
        "do_not_lose",
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
    do_not_lose=None,
):
    content = {
        "goal_id": goal_id,
        "artifact_type": artifact_type,
        "payload": payload,
        "source_refs": source_refs or [],
        "validation": validation or {},
        "trace": trace or {},
        "acl": acl(allow_roles, projection_fields),
    }
    if do_not_lose:
        content["do_not_lose"] = do_not_lose
    return content


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
    if MNMemoryItem is not None:
        MNMemoryItem(
            id=item_id,
            type=item_type,
            content=content,
            status=status,
            confidence=confidence,
            source=source,
        )
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


def compile_context(
    stub,
    job_id,
    role,
    focus_id,
    max_items=20,
    token_budget=None,
    target_tokens=None,
    objective="",
    current_subtask="",
    use_model_compression=None,
):
    response = stub.CompileContext(
        context_pb2.CompileContextRequest(
            job_id=job_id,
            agent_role=role,
            focus_id=focus_id,
            max_items=max_items,
            token_budget=(
                token_budget
                if token_budget is not None
                else env_int("MN_CONTEXT_PACKET_TOKEN_BUDGET", default=0)
            ),
            target_tokens=(
                target_tokens
                if target_tokens is not None
                else env_int("MN_CONTEXT_PACKET_TARGET_TOKENS", default=0)
            ),
            use_model_compression=(
                use_model_compression
                if use_model_compression is not None
                else env_bool("MN_CONTEXT_USE_MODEL_COMPRESSION", default=True)
            ),
            objective=objective,
            current_subtask=current_subtask,
        )
    )
    packet = parse_json_payload(response.packet_json) if response.packet_json else {}
    trace = (
        parse_json_payload(response.compression_trace_json)
        if response.compression_trace_json
        else {}
    )
    return {
        "packet": packet,
        "trace": trace,
        "estimated_input_tokens": response.estimated_input_tokens,
        "estimated_output_tokens": response.estimated_output_tokens,
        "compressed": response.compressed,
        "warnings": list(response.warnings),
    }


def compiled_context_summary(compiled):
    return json.dumps(
        {
            "context_packet": compiled.get("packet", {}).get("context_packet"),
            "compression": {
                "estimated_input_tokens": compiled.get("estimated_input_tokens", 0),
                "estimated_output_tokens": compiled.get("estimated_output_tokens", 0),
                "compressed": compiled.get("compressed", False),
                "warnings": compiled.get("warnings", []),
                "trace": compiled.get("trace", {}),
            },
        },
        sort_keys=True,
    )


def compile_context_state(compiled):
    trace = compiled.get("trace", {})
    return {
        "estimated_input_tokens": compiled.get("estimated_input_tokens", 0),
        "estimated_output_tokens": compiled.get("estimated_output_tokens", 0),
        "compressed": compiled.get("compressed", False),
        "level": trace.get("level"),
        "warnings": compiled.get("warnings", []),
    }


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

    model = os.environ.get("LITELLM_MODEL", "ollama/nemotron3:33b").strip()
    api_base = os.environ.get("LITELLM_API_BASE", "").strip()
    api_key = os.environ.get("LITELLM_API_KEY", "").strip()
    timeout = float(os.environ.get("LITELLM_TIMEOUT_SECONDS", "60"))

    try:
        if model.startswith("ollama/"):
            api_base = (api_base or "http://192.168.4.173:11434").rstrip("/")
            payload = {
                "model": model.removeprefix("ollama/"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "format": "json",
            }
            request = urllib.request.Request(
                f"{api_base}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            return ensure_json_object(
                parse_json_payload(data.get("message", {}).get("content", "{}")),
                mock_response,
            )

        from openai import OpenAI

        base_url = api_base.rstrip("/") if api_base else None
        if base_url:
            for suffix in ("/v1/chat/completions", "/chat/completions"):
                if base_url.endswith(suffix):
                    base_url = base_url[: -len(suffix)]
        client = OpenAI(api_key=api_key or "unused", base_url=base_url)
        response = client.chat.completions.create(
            model=model.split("/", 1)[1] if model.startswith("openai/") else model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        return ensure_json_object(
            parse_json_payload(response.choices[0].message.content),
            mock_response,
        )
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
    redis_url = (
        source.get("redis_url")
        or first_env("MN_CONTEXT_REDIS_URL", "CONTEXT_REDIS_URL")
    )
    if not redis_url:
        return None
    response = stub.Snapshot(context_pb2.SnapshotRequest(job_id=job_id, redis_url=redis_url))
    if hasattr(response, "success") and not response.success:
        raise RuntimeError("Snapshot failed")
    return redis_url
