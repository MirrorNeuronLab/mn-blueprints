# MCP Job Collaboration

Demonstrates one MirrorNeuron feature: **cross-job MCP collaboration**.

Every launched instance publishes its own status, knowledge, and staged or
final results to a job-scoped SQLite exchange, serves that exchange through a
read-only Streamable HTTP MCP server, discovers matching peer services through
the runtime registry, and reads peer snapshots plus revisioned updates.

## Validate

```bash
mn blueprint validate .
```

## Run a collaborating pair

Launch the two jobs close together. They must use one shared goal and different
ports on the same runtime node:

```bash
mn blueprint run --folder . --offline --fake-llm --detached \
  --run-id mcp-collab-a --follow-seconds 1 \
  --set collaboration.goal_id=demo-pair-1 \
  --set collaboration.role=research \
  --set collaboration.port=18121 \
  --set collaboration.require_peer=true

mn blueprint run --folder . --offline --fake-llm --detached \
  --run-id mcp-collab-b --follow-seconds 1 \
  --set collaboration.goal_id=demo-pair-1 \
  --set collaboration.role=synthesis \
  --set collaboration.port=18122 \
  --set collaboration.require_peer=true
```

The first job starts serving while the second launches. Both poll the runtime
service registry by `goal_id`, exclude their own `job_id`, and connect to each
other through `mirrorneuron-mcp-client-skill`.

For an authenticated server, set `MN_MCP_COLLABORATION_TOKEN` to the same
secret value in both job environments. The token is read from the environment
and must not be placed in blueprint inputs, service metadata, logs, or
artifacts.

## Single-job smoke test

The default `collaboration.require_peer=false` lets one job prove that its MCP
server and local exchange work without a peer:

```bash
mn blueprint run --folder . --offline --fake-llm
```

## Expected evidence

Each run writes `peer_exchange.json`, `mcp_exchange.sqlite3`, and the standard
run-store artifacts. In a paired run, `peer_exchange.json` contains at least
one peer job ID and its MCP snapshot/update journal. The journal contains a
`publication_state: staged` draft followed by a final collaboration result.

The demo is same-node by default and binds to loopback. For cross-node use,
configure a reachable bind/advertise host, provide bearer authentication, and
reserve a distinct port per job.
