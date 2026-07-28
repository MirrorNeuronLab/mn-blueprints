from __future__ import annotations

import argparse
import os
from pathlib import Path

from .server import run_job_mcp_server
from .store import JobExchangeStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve one MirrorNeuron job collaboration exchange over MCP."
    )
    parser.add_argument("--store", required=True, help="SQLite exchange path.")
    parser.add_argument(
        "--allowed-root",
        help="Writable root containing the store. Defaults to the store parent.",
    )
    parser.add_argument("--job-id", default=os.environ.get("MN_JOB_ID", ""))
    parser.add_argument(
        "--blueprint-id",
        default=os.environ.get("MN_BLUEPRINT_ID")
        or os.environ.get("MN_DEMO_ID", ""),
    )
    parser.add_argument("--run-id", default=os.environ.get("MN_RUN_ID", ""))
    parser.add_argument("--goal-id", default=os.environ.get("MN_MCP_GOAL_ID", ""))
    parser.add_argument("--host", default=os.environ.get("MN_MCP_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MN_MCP_PORT", "8000")),
    )
    parser.add_argument("--path", default=os.environ.get("MN_MCP_PATH", "/mcp"))
    parser.add_argument(
        "--transport",
        choices=("streamable-http", "stdio"),
        default="streamable-http",
    )
    parser.add_argument(
        "--bearer-token-env",
        default="MN_MCP_COLLABORATION_TOKEN",
        help="Environment variable containing the bearer token; the token is never accepted on the command line.",
    )
    parser.add_argument(
        "--allow-unauthenticated-non-loopback",
        action="store_true",
        help="Explicitly allow an unauthenticated non-loopback bind.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    store_path = Path(args.store).expanduser()
    allowed_root = (
        Path(args.allowed_root).expanduser()
        if args.allowed_root
        else store_path.parent
    )
    token = os.environ.get(args.bearer_token_env) if args.bearer_token_env else None
    store = JobExchangeStore(
        store_path,
        allowed_root=allowed_root,
        job_id=args.job_id,
        blueprint_id=args.blueprint_id or None,
        run_id=args.run_id or None,
        goal_id=args.goal_id or None,
    )
    run_job_mcp_server(
        store,
        transport=args.transport,
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        bearer_token=token,
        allow_unauthenticated_non_loopback=args.allow_unauthenticated_non_loopback,
    )


if __name__ == "__main__":
    main()
