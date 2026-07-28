# MCP Server Skill

`Package:` `mirrorneuron-mcp-server-skill`

This package gives a MirrorNeuron job a small collaboration exchange that
other jobs can read over MCP. It publishes three record kinds:

- job status;
- reusable knowledge; and
- staged or final results.

The durable SQLite journal supports concurrent local publishers, idempotent
retries, incremental update cursors, bounded payloads, and a read-only
Streamable HTTP MCP server.

## Quick Start

```python
from mn_mcp_server_skill import JobExchangeStore, run_job_mcp_server

store = JobExchangeStore(
    "/job/output/mcp_exchange.sqlite3",
    allowed_root="/job/output",
    job_id="job-123",
    blueprint_id="research",
    goal_id="goal-9",
)
store.publish_status(
    "working",
    stage="research",
    progress=0.4,
    summary="Collecting primary sources.",
    idempotency_key="research-started-v1",
)
store.publish_result(
    "candidate-report",
    {"findings": ["provisional finding"]},
    stage="draft",
    publication_state="staged",
    idempotency_key="candidate-report-draft-v1",
)

run_job_mcp_server(store, host="127.0.0.1", port=18121)
```

Declare that endpoint as a job or agent service in the blueprint, including
the `mcp`, `job-collaboration`, and goal-selection tags needed by clients.
Peers can then use `mirrorneuron-mcp-client-skill` to discover the service and
read its snapshot or update journal.

## Authentication

Loopback-only servers may run without authentication for same-node jobs. A
non-loopback bind is rejected unless a bearer token is supplied or the caller
explicitly opts into an unauthenticated bind. Prefer passing the token through
a secret environment variable:

```python
run_job_mcp_server(
    store,
    host="0.0.0.0",
    port=18121,
    bearer_token=os.environ["MN_MCP_COLLABORATION_TOKEN"],
)
```

Do not put bearer tokens in service metadata, blueprint inputs, logs, or
artifacts.

## Boundaries

This skill owns the exchange store and MCP adapter. The blueprint owns peer
selection, collaboration policy, runtime service declarations, workflow
routing, and completion. The server does not mutate another job, launch peers,
or supervise blueprint processes.
