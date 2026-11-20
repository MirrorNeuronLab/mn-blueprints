from __future__ import annotations

import hmac
import ipaddress
import json
from typing import Any, Callable

from .store import DEFAULT_QUERY_LIMIT, JobExchangeStore


DEFAULT_MCP_PATH = "/mcp"
READ_SCOPE = "mn:job:read"


class _StaticBearerTokenVerifier:
    def __init__(self, expected_token: str, access_token_factory: Callable[..., Any]) -> None:
        self.expected_token = expected_token
        self.access_token_factory = access_token_factory

    async def verify_token(self, token: str) -> Any | None:
        if not hmac.compare_digest(str(token), self.expected_token):
            return None
        return self.access_token_factory(
            token=token,
            client_id="mirrorneuron-job-peer",
            scopes=[READ_SCOPE],
            subject="job-collaborator",
        )


def create_job_mcp_server(
    store: JobExchangeStore,
    *,
    name: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    streamable_http_path: str = DEFAULT_MCP_PATH,
    bearer_token: str | None = None,
    allow_unauthenticated_non_loopback: bool = False,
    stateless_http: bool = True,
    server_factory: Callable[..., Any] | None = None,
) -> Any:
    """Create a read-only FastMCP projection over one job exchange."""
    resolved_host = str(host).strip()
    resolved_port = _port(port)
    resolved_path = _mcp_path(streamable_http_path)
    resolved_token = str(bearer_token or "").strip() or None
    if (
        not resolved_token
        and not _is_loopback(resolved_host)
        and not allow_unauthenticated_non_loopback
    ):
        raise ValueError(
            "bearer_token is required when binding the job MCP server outside loopback"
        )

    auth_kwargs: dict[str, Any] = {}
    if resolved_token:
        from mcp.server.auth.provider import AccessToken
        from mcp.server.auth.settings import AuthSettings

        public_host = resolved_host if _is_loopback(resolved_host) else "127.0.0.1"
        resource_url = f"http://{public_host}:{resolved_port}"
        auth_kwargs = {
            "token_verifier": _StaticBearerTokenVerifier(
                resolved_token,
                AccessToken,
            ),
            "auth": AuthSettings(
                issuer_url=resource_url,
                resource_server_url=resource_url,
                required_scopes=[READ_SCOPE],
            ),
        }

    if server_factory is None:
        from mcp.server.fastmcp import FastMCP

        server_factory = FastMCP

    server = server_factory(
        name
        or f"MirrorNeuron job {store.identity['job_id']} collaboration exchange",
        instructions=(
            "Read-only job collaboration exchange. Staged records are provisional; "
            "use publication_state to distinguish them from final records."
        ),
        host=resolved_host,
        port=resolved_port,
        streamable_http_path=resolved_path,
        json_response=True,
        stateless_http=bool(stateless_http),
        **auth_kwargs,
    )

    @server.tool(
        name="get_job_snapshot",
        description="Read the latest status, knowledge, and results published by this job.",
        structured_output=True,
    )
    def get_job_snapshot(
        kinds: list[str] | None = None,
        include_staged: bool = True,
        limit: int = DEFAULT_QUERY_LIMIT,
    ) -> dict[str, Any]:
        return store.snapshot(
            kinds=kinds,
            include_staged=include_staged,
            limit=limit,
        )

    @server.tool(
        name="get_job_updates",
        description="Read ordered collaboration updates after a revision cursor.",
        structured_output=True,
    )
    def get_job_updates(
        after_revision: int = 0,
        kinds: list[str] | None = None,
        include_staged: bool = True,
        limit: int = DEFAULT_QUERY_LIMIT,
    ) -> dict[str, Any]:
        return store.updates(
            after_revision=after_revision,
            kinds=kinds,
            include_staged=include_staged,
            limit=limit,
        )

    @server.tool(
        name="get_job_record",
        description="Read the latest version of one status, knowledge, or result record.",
        structured_output=True,
    )
    def get_job_record(
        kind: str,
        record_id: str,
        include_staged: bool = True,
    ) -> dict[str, Any]:
        return {
            "schema_version": "mn.mcp.job_record.v1",
            "identity": dict(store.identity),
            "record": store.get_record(
                kind,
                record_id,
                include_staged=include_staged,
            ),
        }

    @server.resource(
        "mn-job://self/identity",
        name="job_identity",
        description="Identity of the job that owns this MCP server.",
        mime_type="application/json",
    )
    def identity_resource() -> str:
        return json.dumps(
            {
                "schema_version": "mn.mcp.job_identity.v1",
                "identity": store.identity,
            },
            sort_keys=True,
        )

    @server.resource(
        "mn-job://self/snapshot",
        name="job_snapshot",
        description="Latest status, knowledge, and staged or final results.",
        mime_type="application/json",
    )
    def snapshot_resource() -> str:
        return json.dumps(store.snapshot(), sort_keys=True)

    @server.resource(
        "mn-job://self/updates",
        name="job_updates",
        description="Bounded collaboration update journal from revision zero.",
        mime_type="application/json",
    )
    def updates_resource() -> str:
        return json.dumps(store.updates(), sort_keys=True)

    return server


def run_job_mcp_server(
    store: JobExchangeStore,
    *,
    transport: str = "streamable-http",
    **server_options: Any,
) -> None:
    if transport not in {"streamable-http", "stdio"}:
        raise ValueError("transport must be streamable-http or stdio")
    server = create_job_mcp_server(store, **server_options)
    server.run(transport=transport)


def _port(value: Any) -> int:
    resolved = int(value)
    if resolved < 1 or resolved > 65_535:
        raise ValueError("port must be between 1 and 65535")
    return resolved


def _mcp_path(value: str) -> str:
    path = str(value).strip()
    if not path.startswith("/") or "?" in path or "#" in path:
        raise ValueError("streamable_http_path must be an absolute URL path")
    return path


def _is_loopback(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False
