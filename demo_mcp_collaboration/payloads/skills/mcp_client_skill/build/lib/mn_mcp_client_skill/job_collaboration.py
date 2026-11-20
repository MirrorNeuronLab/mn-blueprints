from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from .mcp_client import call_mcp_tool, mcp_http_server_config, redact_secrets


DEFAULT_JOB_MCP_SERVICE_NAME = "mn-job-collaboration"
DEFAULT_JOB_MCP_TAGS = ("mcp", "job-collaboration")
MAX_DISCOVERED_JOB_SERVERS = 64
ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def mcp_job_server_config(
    service: Mapping[str, Any],
    *,
    headers: Mapping[str, str] | None = None,
    bearer_token_env: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Build a Streamable HTTP config from one runtime service record."""
    meta = service.get("meta") if isinstance(service.get("meta"), Mapping) else {}
    scheme = str(meta.get("mcp_scheme") or meta.get("scheme") or "http").strip().lower()
    if scheme not in {"http", "https"}:
        raise ValueError("MCP service scheme must be http or https")
    host = _service_host(service)
    port = _service_port(service)
    path = str(meta.get("mcp_path") or "/mcp").strip()
    if not path.startswith("/") or "?" in path or "#" in path:
        raise ValueError("MCP service path must be an absolute URL path")

    resolved_headers = dict(headers or {})
    if bearer_token_env:
        env_name = str(bearer_token_env).strip()
        if not ENV_NAME_PATTERN.fullmatch(env_name):
            raise ValueError("bearer_token_env must be an environment variable name")
        if any(str(key).lower() == "authorization" for key in resolved_headers):
            raise ValueError("authorization header and bearer_token_env are mutually exclusive")
        resolved_headers["authorization"] = f"Bearer ${{{env_name}}}"

    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    service_id = str(service.get("id") or service.get("name") or "job-mcp")
    return mcp_http_server_config(
        f"{scheme}://{display_host}:{port}{path}",
        headers=resolved_headers,
        name=service_id,
        timeout_seconds=timeout_seconds,
    )


def discover_mcp_job_servers(
    *,
    runtime_client: Any | None = None,
    service_name: str = DEFAULT_JOB_MCP_SERVICE_NAME,
    tags: Sequence[str] = DEFAULT_JOB_MCP_TAGS,
    job_id: str | None = None,
    goal_id: str | None = None,
    agent_id: str | None = None,
    exclude_job_id: str | None = None,
    bearer_token_env: str | None = None,
    headers: Mapping[str, str] | None = None,
    timeout_seconds: float = 30.0,
    passing_only: bool = True,
    max_servers: int = MAX_DISCOVERED_JOB_SERVERS,
) -> dict[str, Any]:
    """Discover bounded job MCP endpoints through the runtime service registry."""
    resolved_max = int(max_servers)
    if resolved_max <= 0 or resolved_max > MAX_DISCOVERED_JOB_SERVERS:
        raise ValueError(
            f"max_servers must be between 1 and {MAX_DISCOVERED_JOB_SERVERS}"
        )
    client = runtime_client or _default_runtime_client()
    query = {
        "name": str(service_name),
        "tags": [str(tag) for tag in tags],
        "job_id": str(job_id) if job_id else None,
        "agent_id": str(agent_id) if agent_id else None,
        "passing_only": bool(passing_only),
    }
    try:
        response = client.list_services(
            **{key: value for key, value in query.items() if value is not None}
        )
        services = _service_records(response)
    except Exception as exc:
        return {
            "status": "failed",
            "servers": [],
            "warnings": [],
            "error": f"{type(exc).__name__}: runtime service discovery failed",
        }

    servers: list[dict[str, Any]] = []
    warnings: list[str] = []
    for service in services:
        service_job_id = str(service.get("job_id") or "")
        if exclude_job_id and service_job_id == str(exclude_job_id):
            continue
        meta = service.get("meta") if isinstance(service.get("meta"), Mapping) else {}
        if goal_id is not None and str(meta.get("goal_id") or "") != str(goal_id):
            continue
        try:
            config = mcp_job_server_config(
                service,
                headers=headers,
                bearer_token_env=bearer_token_env,
                timeout_seconds=timeout_seconds,
            )
        except (TypeError, ValueError) as exc:
            warnings.append(
                f"ignored service {service.get('id') or service.get('name') or 'unknown'}: {exc}"
            )
            continue
        servers.append(
            {
                "job_id": service_job_id,
                "agent_id": str(service.get("agent_id") or ""),
                "goal_id": str(meta.get("goal_id") or ""),
                "service": redact_secrets(dict(service)),
                "config": config,
            }
        )
        if len(servers) >= resolved_max:
            if len(services) > len(servers):
                warnings.append(f"service discovery was limited to {resolved_max} servers")
            break
    return {
        "status": "ok",
        "servers": servers,
        "warnings": warnings,
    }


def resolve_mcp_job_server_config(
    job_id: str,
    *,
    runtime_client: Any | None = None,
    service_name: str = DEFAULT_JOB_MCP_SERVICE_NAME,
    tags: Sequence[str] = DEFAULT_JOB_MCP_TAGS,
    goal_id: str | None = None,
    agent_id: str | None = None,
    bearer_token_env: str | None = None,
    headers: Mapping[str, str] | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    discovery = discover_mcp_job_servers(
        runtime_client=runtime_client,
        service_name=service_name,
        tags=tags,
        job_id=job_id,
        goal_id=goal_id,
        agent_id=agent_id,
        bearer_token_env=bearer_token_env,
        headers=headers,
        timeout_seconds=timeout_seconds,
        max_servers=2,
    )
    if discovery["status"] != "ok":
        raise RuntimeError(discovery["error"])
    servers = discovery["servers"]
    if not servers:
        raise LookupError(f"no passing MCP service was found for job {job_id}")
    if len(servers) > 1:
        raise LookupError(
            f"multiple MCP services were found for job {job_id}; select an agent_id"
        )
    return dict(servers[0]["config"])


def get_mcp_job_snapshot(
    config: Mapping[str, Any],
    *,
    kinds: Sequence[str] | None = None,
    include_staged: bool = True,
    limit: int = 200,
    session_factory: Any | None = None,
) -> dict[str, Any]:
    return _call_job_exchange_tool(
        config,
        "get_job_snapshot",
        {
            "kinds": list(kinds) if kinds is not None else None,
            "include_staged": bool(include_staged),
            "limit": int(limit),
        },
        payload_key="snapshot",
        session_factory=session_factory,
    )


def get_mcp_job_updates(
    config: Mapping[str, Any],
    *,
    after_revision: int = 0,
    kinds: Sequence[str] | None = None,
    include_staged: bool = True,
    limit: int = 200,
    session_factory: Any | None = None,
) -> dict[str, Any]:
    return _call_job_exchange_tool(
        config,
        "get_job_updates",
        {
            "after_revision": int(after_revision),
            "kinds": list(kinds) if kinds is not None else None,
            "include_staged": bool(include_staged),
            "limit": int(limit),
        },
        payload_key="updates",
        session_factory=session_factory,
    )


def get_mcp_job_record(
    config: Mapping[str, Any],
    kind: str,
    record_id: str,
    *,
    include_staged: bool = True,
    session_factory: Any | None = None,
) -> dict[str, Any]:
    return _call_job_exchange_tool(
        config,
        "get_job_record",
        {
            "kind": str(kind),
            "record_id": str(record_id),
            "include_staged": bool(include_staged),
        },
        payload_key="record",
        session_factory=session_factory,
    )


def _call_job_exchange_tool(
    config: Mapping[str, Any],
    tool_name: str,
    arguments: Mapping[str, Any],
    *,
    payload_key: str,
    session_factory: Any | None,
) -> dict[str, Any]:
    cleaned_arguments = {
        key: value for key, value in arguments.items() if value is not None
    }
    response = call_mcp_tool(
        config,
        tool_name,
        cleaned_arguments,
        session_factory=session_factory,
    )
    if response.get("status") != "ok":
        return response
    payload = _structured_tool_payload(response.get("result"))
    if payload is None:
        return {
            **response,
            "status": "failed",
            "error": f"{tool_name} returned no structured JSON payload",
        }
    return {
        key: value for key, value in response.items() if key != "result"
    } | {payload_key: payload}


def _structured_tool_payload(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, Mapping):
        return None
    for key in ("structuredContent", "structured_content"):
        value = result.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    if "schema_version" in result:
        return dict(result)
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, Mapping) or item.get("type") != "text":
                continue
            try:
                decoded = json.loads(str(item.get("text") or ""))
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, Mapping):
                return dict(decoded)
    return None


def _service_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        decoded = json.loads(value)
    else:
        decoded = value
    if isinstance(decoded, Mapping):
        for key in ("services", "items", "data"):
            items = decoded.get(key)
            if isinstance(items, list):
                return [dict(item) for item in items if isinstance(item, Mapping)]
    if isinstance(decoded, list):
        return [dict(item) for item in decoded if isinstance(item, Mapping)]
    return []


def _service_host(service: Mapping[str, Any]) -> str:
    host = str(service.get("address") or "").strip()
    if not host:
        node = str(service.get("node") or "").strip()
        host = node.rsplit("@", 1)[-1] if "@" in node else node
    host = host.strip("[]")
    if not host:
        raise ValueError("MCP service has no address or resolvable node host")
    if host in {"0.0.0.0", "::"}:
        raise ValueError("MCP service advertises a wildcard address")
    if any(character in host for character in "/?#"):
        raise ValueError("MCP service address is invalid")
    return host


def _service_port(service: Mapping[str, Any]) -> int:
    try:
        port = int(service.get("port"))
    except (TypeError, ValueError) as exc:
        raise ValueError("MCP service port must be an integer") from exc
    if port < 1 or port > 65_535:
        raise ValueError("MCP service port must be between 1 and 65535")
    return port


def _default_runtime_client() -> Any:
    try:
        from mn_sdk import Client
    except ImportError as exc:
        raise RuntimeError(
            "runtime discovery requires mirrorneuron-python-sdk or an injected runtime_client"
        ) from exc
    return Client()
