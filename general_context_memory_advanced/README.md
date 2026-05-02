# Advanced Context Memory Compression

This blueprint demonstrates Membrane / MicroNeuron context memory under pressure: each LLM agent receives a precise compiled context packet, then writes a larger artifact into working memory so the next turn has more context to manage.

The point is to show context engineering as a runtime behavior, not a static prompt trick:

- typed memory items preserve tasks, evidence, constraints, hypotheses, decisions, traces, confidence, source refs, and lifecycle state
- role ACLs hide raw context from agents that do not need it
- `CompileContext` assembles a bounded packet for every LLM-facing turn
- automatic deterministic compression keeps pinned IDs, deadlines, constraints, validation metadata, and `do_not_lose` terms
- optional model compression can be requested with `MN_CONTEXT_USE_MODEL_COMPRESSION=true`

## Agent Relay

1. **Initializer** seeds a long source bundle, a compression policy, and pinned terms.
2. **Context Researcher** calls `CompileContext`, then uses `nemotron3:33b` to create a longer research digest.
3. **Context Expander** consumes the compressed packet and digest, then intentionally adds structured repetition and a larger handoff.
4. **Constraint Challenger** consumes the compressed context and tests what must survive compression.
5. **Context Compressor** consumes the growing graph and writes a short handoff for the final agent.
6. **Briefing Author** consumes the final compiled packet and produces a concise briefing with traceability.

## LLM Endpoint

The blueprint defaults to the Ollama-compatible endpoint you provided:

```bash
LITELLM_MODEL=ollama/nemotron3:33b
LITELLM_API_BASE=http://192.168.4.173:11434
```

Each agent calls `/api/chat` with `stream=false` and `format=json`.

## Context Engine

Start Membrane before running the blueprint. The current Membrane repo installs and runs the core memory engine with Docker:

```bash
cd /Users/homer/Projects/Membrane
MN_DOCKER_TARGET=cpu scripts/install-docker.sh run
```

For NVIDIA GPU-accelerated LLMLingua compression:

```bash
cd /Users/homer/Projects/Membrane
MN_DOCKER_TARGET=nvidia scripts/install-docker.sh run
```

The blueprint payload vendors the Membrane Python SDK model package and validates memory items with it before sending them to the Dockerized gRPC engine.

Useful compression knobs:

```bash
MN_CONTEXT_PACKET_TOKEN_BUDGET=1000
MN_CONTEXT_PACKET_TARGET_TOKENS=600
MN_CONTEXT_USE_MODEL_COMPRESSION=true
```

If Membrane is not started with external model compression enabled, it still performs deterministic packet compression and returns a warning in the compression trace.

## Run

Validate:

```bash
mn validate /Users/homer/Projects/mirror-neuron-set/mn-blueprints/general_context_memory_advanced
```

Run:

```bash
mn run /Users/homer/Projects/mirror-neuron-set/mn-blueprints/general_context_memory_advanced
```

Quick local logic test with mock LLM output:

```bash
MN_BLUEPRINT_QUICK_TEST=1 \
mn run /Users/homer/Projects/mirror-neuron-set/mn-blueprints/general_context_memory_advanced
```

## What To Inspect

The final output includes:

- `seen_by_*`: projected artifact types each agent received
- `context_compile`: token estimates, compression level, warnings, and compression status
- `final_briefing`: the final LLM-authored concise output
- source refs connecting the final briefing back to the compressed handoff, challenge, policy, and long source bundle
