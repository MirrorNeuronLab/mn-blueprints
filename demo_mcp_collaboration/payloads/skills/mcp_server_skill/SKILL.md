---
name: mirrorneuron.mcp.server
package: mirrorneuron-mcp-server-skill
folder: mcp_server_skill
import: mn_mcp_server_skill
description: Job-scoped MCP server helpers for publishing bounded status, knowledge, and staged or final results through a read-only Streamable HTTP MCP interface so separately launched MirrorNeuron jobs can collaborate.
---

# MCP Server Skill

Use `JobExchangeStore` to publish a job's own collaboration records and
`create_job_mcp_server` or `run_job_mcp_server` to expose them to peers.

## Workflow

1. Create one SQLite store under the job's writable output or data root.
2. Give the store immutable `job_id`, `blueprint_id`, `run_id`, and `goal_id`
   identity.
3. Publish status, knowledge, and result records with caller-owned
   idempotency keys. Mark provisional records `staged` and approved records
   `final`.
4. Run one Streamable HTTP MCP server for the job and declare its port as a
   MirrorNeuron service in the blueprint.
5. Let peer jobs discover and read the server with
   `mirrorneuron.mcp.client`; keep peer selection and workflow completion in
   the blueprint.

The MCP surface is intentionally read-only. A job writes its own store through
the local Python API; peers can call `get_job_snapshot`, `get_job_updates`, and
`get_job_record`, or read the fixed `mn-job://self/*` resources.

## Safety

- Keep the database inside an explicit allowed root.
- Do not publish credentials, private keys, authorization values, cookies, or
  customer data that peers are not authorized to receive. Sensitive field
  names are rejected by default.
- Bind unauthenticated servers only to loopback. Supply a bearer token when
  binding to a non-loopback interface, and distribute it outside manifests,
  logs, inputs, and artifacts.
- Bound payload bytes, history, query limits, and server lifetime.
- Treat peer-visible staged records as provisional, not approved facts.
- Use the runtime service registry for endpoint discovery; do not encode peer
  job routing or lifecycle supervision in this skill.

## Verification

Run:

```bash
PYTHONPATH=src python -m pytest tests -q
```
