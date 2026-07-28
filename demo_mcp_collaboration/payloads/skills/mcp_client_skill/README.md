# MCP Client Skill

`Package:` `mirrorneuron-mcp-client-skill`

Client-only helpers for connecting to existing MCP servers from MirrorNeuron
agents. The skill supports stdio subprocess servers and Streamable HTTP MCP
endpoints, then exposes simple helpers for listing tools/resources/prompts,
calling tools, and reading resources.

It also understands MirrorNeuron job collaboration services. A caller can
discover healthy MCP endpoints through the runtime service registry, select
them by job or shared goal, and read status, knowledge, staged results, final
results, or an incremental update journal.

## Quick Start

Install this skill from source:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

Example stdio config:

```python
from mn_mcp_client_skill import mcp_stdio_server_config, list_mcp_tools

config = mcp_stdio_server_config(
    command=["python", "-m", "my_mcp_server"],
    name="local-tools",
)
tools = list_mcp_tools(config)
```

Example Streamable HTTP config:

```python
from mn_mcp_client_skill import mcp_http_server_config, call_mcp_tool

config = mcp_http_server_config(
    "http://127.0.0.1:8000/mcp",
    headers={"authorization": "${MCP_AUTHORIZATION}"},
    name="shared-tools",
)
result = call_mcp_tool(config, "search", {"query": "invoice policy"})
```

Example job collaboration discovery:

```python
from mn_sdk import Client
from mn_mcp_client_skill import (
    discover_mcp_job_servers,
    get_mcp_job_snapshot,
)

discovery = discover_mcp_job_servers(
    runtime_client=Client(),
    goal_id="shared-goal-9",
    exclude_job_id="this-job-id",
    bearer_token_env="MN_MCP_COLLABORATION_TOKEN",
)
for peer in discovery["servers"]:
    snapshot = get_mcp_job_snapshot(
        peer["config"],
        include_staged=True,
    )
```

## Notes

- This package does not create or host MCP servers. Use
  `mirrorneuron-mcp-server-skill` for that.
- Prefer stdio for local agent-owned subprocess servers.
- Prefer Streamable HTTP for shared long-running MCP endpoints.
- Keep secrets in environment variables where possible.
- Treat MCP tool calls as remote actions that may need user approval.
- Treat `publication_state: staged` collaboration records as provisional.
