from __future__ import annotations

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping, Sequence
from urllib.parse import urlparse


logger = logging.getLogger("mn.skill.mcp_client")
SECRET_KEY_PARTS = ("authorization", "token", "api_key", "apikey", "password", "secret", "cookie")
VALID_TRANSPORTS = {"stdio", "streamable_http"}
ENV_PLACEHOLDER_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

AsyncSessionOperation = Callable[[Any], Awaitable[dict[str, Any]]]
AsyncSessionFactory = Callable[[Mapping[str, Any]], AsyncIterator[Any]]


def mcp_stdio_server_config(
    command: Sequence[str],
    args: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    name: str | None = None,
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    cmd = _string_list(command)
    extra_args = _string_list(args or [])
    config: dict[str, Any] = {
        "transport": "stdio",
        "command": cmd,
        "args": extra_args,
        "env": dict(env or {}),
        "timeout_seconds": float(timeout_seconds),
    }
    if cwd is not None:
        config["cwd"] = str(cwd)
    if name:
        config["name"] = str(name)
    return config


def mcp_http_server_config(
    url: str,
    headers: Mapping[str, str] | None = None,
    name: str | None = None,
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "transport": "streamable_http",
        "url": str(url),
        "headers": dict(headers or {}),
        "timeout_seconds": float(timeout_seconds),
    }
    if name:
        config["name"] = str(name)
    return config


def validate_mcp_server_config(config: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    transport = str(config.get("transport") or "")
    if transport not in VALID_TRANSPORTS:
        return [f"transport must be one of {', '.join(sorted(VALID_TRANSPORTS))}"]

    if transport == "stdio":
        command = config.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
            issues.append("stdio command must be a non-empty list of strings")
        elif _looks_shell_like(command):
            issues.append("stdio command must not use shell operators or shell wrappers")
        args = config.get("args", [])
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            issues.append("stdio args must be a list of strings")
        env = config.get("env", {})
        if not isinstance(env, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in env.items()):
            issues.append("stdio env must be a mapping of string keys to string values")

    if transport == "streamable_http":
        url = str(config.get("url") or "")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            issues.append("streamable_http url must be an absolute http(s) URL")
        headers = config.get("headers", {})
        if not isinstance(headers, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in headers.items()):
            issues.append("streamable_http headers must be a mapping of string keys to string values")

    timeout = config.get("timeout_seconds", 30.0)
    try:
        if float(timeout) <= 0:
            issues.append("timeout_seconds must be greater than 0")
    except (TypeError, ValueError):
        issues.append("timeout_seconds must be numeric")
    return issues


def list_mcp_tools(
    config: Mapping[str, Any],
    *,
    session_factory: AsyncSessionFactory | None = None,
) -> dict[str, Any]:
    return _run_operation(config, _list_tools, session_factory=session_factory)


def call_mcp_tool(
    config: Mapping[str, Any],
    tool_name: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    session_factory: AsyncSessionFactory | None = None,
) -> dict[str, Any]:
    async def operation(session: Any) -> dict[str, Any]:
        result = await session.call_tool(tool_name, dict(arguments or {}))
        return {"result": _normalize(result)}

    return _run_operation(config, operation, session_factory=session_factory)


def list_mcp_resources(
    config: Mapping[str, Any],
    *,
    session_factory: AsyncSessionFactory | None = None,
) -> dict[str, Any]:
    return _run_operation(config, _list_resources, session_factory=session_factory)


def read_mcp_resource(
    config: Mapping[str, Any],
    uri: str,
    *,
    session_factory: AsyncSessionFactory | None = None,
) -> dict[str, Any]:
    async def operation(session: Any) -> dict[str, Any]:
        result = await session.read_resource(uri)
        return {"result": _normalize(result)}

    return _run_operation(config, operation, session_factory=session_factory)


def list_mcp_prompts(
    config: Mapping[str, Any],
    *,
    session_factory: AsyncSessionFactory | None = None,
) -> dict[str, Any]:
    return _run_operation(config, _list_prompts, session_factory=session_factory)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(part in key_text.lower() for part in SECRET_KEY_PARTS):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value


async def _list_tools(session: Any) -> dict[str, Any]:
    result = await session.list_tools()
    normalized = _normalize(result)
    return {"tools": _extract_collection(normalized, "tools")}


async def _list_resources(session: Any) -> dict[str, Any]:
    result = await session.list_resources()
    normalized = _normalize(result)
    return {"resources": _extract_collection(normalized, "resources")}


async def _list_prompts(session: Any) -> dict[str, Any]:
    result = await session.list_prompts()
    normalized = _normalize(result)
    return {"prompts": _extract_collection(normalized, "prompts")}


def _run_operation(
    config: Mapping[str, Any],
    operation: AsyncSessionOperation,
    *,
    session_factory: AsyncSessionFactory | None,
) -> dict[str, Any]:
    safe_config = dict(config)
    issues = validate_mcp_server_config(safe_config)
    base = {
        "server": _server_summary(safe_config),
        "transport": safe_config.get("transport"),
        "warnings": [],
    }
    if issues:
        return {**base, "status": "failed", "error": "; ".join(issues)}
    try:
        return asyncio.run(_run_operation_async(safe_config, operation, session_factory=session_factory))
    except Exception as exc:
        logger.warning("MCP client operation failed for %s: %s", safe_config.get("name") or safe_config.get("transport"), exc)
        return {**base, "status": "failed", "error": _redact_error(exc)}


async def _run_operation_async(
    config: Mapping[str, Any],
    operation: AsyncSessionOperation,
    *,
    session_factory: AsyncSessionFactory | None,
) -> dict[str, Any]:
    timeout = float(config.get("timeout_seconds", 30.0))
    factory = session_factory or _mcp_session
    async with factory(config) as session:
        await asyncio.wait_for(session.initialize(), timeout=timeout)
        payload = await asyncio.wait_for(operation(session), timeout=timeout)
    return {
        "status": "ok",
        "server": _server_summary(config),
        "transport": config.get("transport"),
        "warnings": [],
        **payload,
    }


@asynccontextmanager
async def _mcp_session(config: Mapping[str, Any]) -> AsyncIterator[Any]:
    transport = config.get("transport")
    if transport == "stdio":
        async with _stdio_session(config) as session:
            yield session
        return
    if transport == "streamable_http":
        async with _streamable_http_session(config) as session:
            yield session
        return
    raise ValueError(f"unsupported transport: {transport}")


@asynccontextmanager
async def _stdio_session(config: Mapping[str, Any]) -> AsyncIterator[Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    command = list(config["command"])
    params = StdioServerParameters(
        command=command[0],
        args=[*command[1:], *list(config.get("args") or [])],
        env={**os.environ, **dict(config.get("env") or {})},
        cwd=config.get("cwd"),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            yield session


@asynccontextmanager
async def _streamable_http_session(config: Mapping[str, Any]) -> AsyncIterator[Any]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = _resolve_header_env(dict(config.get("headers") or {}))
    async with streamablehttp_client(str(config["url"]), headers=headers) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            yield session


def _resolve_header_env(headers: Mapping[str, str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for key, value in headers.items():
        text = str(value)
        missing: list[str] = []

        def replace(match: re.Match[str]) -> str:
            env_name = match.group(1)
            env_value = os.environ.get(env_name)
            if not env_value:
                missing.append(env_name)
                return ""
            return env_value

        rendered = ENV_PLACEHOLDER_PATTERN.sub(replace, text)
        if missing:
            raise ValueError(
                f"required MCP header environment variable is not set: {missing[0]}"
            )
        resolved[str(key)] = rendered
    return resolved


def _normalize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize(item) for item in value]
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {key: _normalize(item) for key, item in vars(value).items() if not key.startswith("_")}
    return value


def _extract_collection(normalized: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(normalized, Mapping):
        value = normalized.get(key)
        if isinstance(value, list):
            return [_as_dict(item) for item in value]
    if isinstance(normalized, list):
        return [_as_dict(item) for item in normalized]
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    normalized = _normalize(value)
    if isinstance(normalized, Mapping):
        return dict(normalized)
    return {"value": normalized}


def _server_summary(config: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("name", "transport", "command", "args", "cwd", "url", "headers")
    return redact_secrets({key: config[key] for key in keys if key in config})


def _redact_error(error: BaseException) -> str:
    return str(redact_secrets({"error": str(error)})["error"])


def _string_list(values: Sequence[str]) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise TypeError("expected a sequence of strings, not a single string")
    return [str(value) for value in values]


def _looks_shell_like(command: Sequence[str]) -> bool:
    if not command:
        return True
    executable = command[0].strip().lower()
    if executable in {"sh", "bash", "zsh", "fish", "cmd", "powershell", "pwsh"}:
        return True
    shell_tokens = {"|", "&&", "||", ";", ">", "<", "$(", "`"}
    return any(token in part for part in command for token in shell_tokens)
