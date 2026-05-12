# Business Context Memory Compression Code Analysis

`Blueprint ID:` `business_context_memory_compression_code_analsysis`  
`Category:` business - Business Runtime Pattern  
`Default LLM:` Ollama `nemotron3:33b` with deterministic fake LLM support for tests  
`Memory layer:` Membrane Python SDK from `/Users/homer/Projects/Membrane/mn-context-engine-python-sdk/src`

## One-line value proposition

Benchmark Membrane SDK working memory on large-repo code analysis with bounded context packets.

## What it is

This blueprint is an end-to-end Membrane memory-layer benchmark for a realistic code-analysis workload. It seeds a metadata-only fixture from the real `django/django` GitHub repository, expands it into hundreds of typed memory items, and asks a multi-agent workflow to produce a concise architecture briefing without losing source refs, commit identity, or private-memory boundaries.

It ships with mock inputs so it runs immediately against already-running Membrane containers, and it defines a path for replacing the Django fixture with another repository while keeping the same blueprint identity, configuration model, and output contract.

## Who this is for

Engineering leaders, platform teams, and agent builders evaluating whether a memory layer can support large-repo code analysis under tight prompt budgets.

## Why it matters

Large codebases produce more evidence than an LLM can safely carry in a single prompt. A static dashboard can list files, and a one-shot LLM prompt can summarize a small sample, but neither proves that a working-memory system can retrieve, project, compress, and preserve source evidence across several agent turns. This blueprint makes that pressure visible with a real repository fixture and strict source-ref invariants.

## Why this runtime is useful here

MirrorNeuron is useful here because it runs a sequence of agents over shared typed Membrane memory instead of handing one giant blob to a model. Each agent imports the updated `mn_context_engine_sdk`, calls `CompileContext` through the running Membrane context engine, sees only role-allowed memory, creates a new artifact, and leaves traceable evidence for the next agent. The result is a benchmark for whether memory quality improves speed, cost, and reviewability compared with unbounded context stuffing.

## How it works

1. Load the graph in `manifest.json` and start `initializer` with the bundled Django tree fixture.
2. Seed a task, repository fixture summary, analysis policy, private security note, hundreds of file facts, and generated context-pressure notes.
3. Route work through repo architect, dependency mapper, risk classifier, context compressor, and briefing author agents.
4. Call `CompileContext` before every LLM turn with shrinking token budgets.
5. Return a compressed code-analysis handoff, final architecture briefing, and benchmark report with source refs, compression metrics, quality gates, and speed telemetry.

## Example scenario

A metadata-only Django fixture has more than 3,600 available code and documentation paths. The default run selects 260 files and creates generated notes around them, then asks agents to identify request lifecycle, ORM/migration, auth/session, admin/forms, template, test, and documentation boundaries without replaying every file fact.

## Inputs

| Input | What it controls | Example | Can customize? |
|---|---|---|---|
| `manifest.json` initial inputs | Job, focus, fixture scale, and generated-note volume. | `fixture_max_files: 260` | Yes |
| `payloads/repo_fixture/django_tree_fixture.json` | Metadata-only real GitHub repository fixture. | `repo.commit_sha` | Yes |
| `config/default.json` | Standard identity, mock input, LLM, output, logging, and adapter settings. | `outputs.run_root` | Yes |
| Environment variables | Runtime, Membrane SDK, context engine, Qdrant, LLM, and benchmark scaling. | `MN_MEMBRANE_SDK_PATH`, `MN_CONTEXT_ADDR`, `MN_QDRANT_URL`, `MN_CODE_ANALYSIS_FIXTURE_MAX_FILES` | Yes |

## Outputs

| Output | What it means | Where to look |
|---|---|---|
| Runtime events | Typed messages and worker events emitted through the graph. | `repo_fixture_seeded`, `architecture_digest_done`, `code_analysis_briefing_done` |
| Final artifact | The user-facing architecture briefing and memory benchmark result. | `final_code_analysis_briefing` memory item |
| Benchmark report | Machine-readable metrics for compression, token use, speed, source coverage, quality, and privacy isolation. | `context_memory_benchmark_report` memory item |
| Operational logs | Status lines and worker logs for debugging and audit. | `events.jsonl`, runtime logs, worker stderr |
| Generated memory artifacts | Repo fixture, architecture digest, dependency map, risk register, and compressed handoff. | Context engine memory for the run job |

Key benchmark fields:

| Metric | What it tells you |
|---|---|
| `estimated_compile_input_tokens` | How much uncompressed working memory was considered across agents. |
| `estimated_compile_output_tokens` | How large the compiled packets sent to agents were. |
| `mean_compression_ratio` | Packet size divided by retrieved-memory size; lower means smaller context. |
| `estimated_total_tokens_processed` | Compile input, compile output, and generated artifact token estimates. |
| `compile_latency_seconds_p95` | End-to-end `CompileContext` speed under the fixture load. |
| `tokens_per_second_compile_input` | Throughput over uncompressed memory considered by compilation. |
| `quality_score` | Weighted result quality over pinned terms, source refs, subsystem coverage, hot paths, budget, and privacy. |
| `private_leak_count` | Whether private notes reached roles that should not see them. |

## How to run

This blueprint assumes your Membrane Docker containers are already running. It does not start Docker. Workers use the updated Python SDK from `/Users/homer/Projects/Membrane/mn-context-engine-python-sdk/src` by default; override `MN_MEMBRANE_SDK_PATH` if you want a different checkout or an installed wheel.

Run through a registered MirrorNeuron blueprint checkout:

```bash
cd /Users/homer/Projects/mirror-neuron-set
mn blueprint update
MN_MEMBRANE_SDK_PATH=/Users/homer/Projects/Membrane/mn-context-engine-python-sdk/src \
MN_CONTEXT_ADDR=localhost:50052 \
MN_QDRANT_URL=http://localhost:6333 \
MN_BLUEPRINT_QUICK_TEST=1 \
mn blueprint run business_context_memory_compression_code_analsysis
```

Run directly from the local folder before refreshing the cached catalog:

```bash
cd /Users/homer/Projects/mirror-neuron-set
MN_MEMBRANE_SDK_PATH=/Users/homer/Projects/Membrane/mn-context-engine-python-sdk/src \
MN_CONTEXT_ADDR=localhost:50052 \
MN_QDRANT_URL=http://localhost:6333 \
MN_BLUEPRINT_QUICK_TEST=1 \
mn blueprint run ./mn-blueprints/business_context_memory_compression_code_analsysis
```

Run a larger benchmark by increasing the fixture scale:

```bash
cd /Users/homer/Projects/mirror-neuron-set
MN_MEMBRANE_SDK_PATH=/Users/homer/Projects/Membrane/mn-context-engine-python-sdk/src \
MN_CONTEXT_ADDR=localhost:50052 \
MN_QDRANT_URL=http://localhost:6333 \
MN_CODE_ANALYSIS_FIXTURE_MAX_FILES=900 \
MN_CODE_ANALYSIS_NOTES_PER_FILE=2 \
mn blueprint run business_context_memory_compression_code_analsysis
```

Inspect registered blueprints and recent run artifacts through the unified CLI:

```bash
mn blueprint list
mn blueprint monitor
```

The blueprint runner submits to the MirrorNeuron core runtime through `MN_GRPC_TARGET`. Each worker imports `mn_context_engine_sdk` from `MN_MEMBRANE_SDK_PATH` and talks to the already-running Membrane context engine through `MN_CONTEXT_ADDR`. If your Membrane stack exposes Qdrant, the SDK external-memory helpers use `MN_QDRANT_URL`, `MN_QDRANT_COLLECTION`, and `MN_QDRANT_NAMESPACE`.

The SDK distribution name is `mirrorneuron-membrane-python-sdk`; the import package is `mn_context_engine_sdk`.

Run the shared repository tests:

```bash
cd /Users/homer/Projects/mirror-neuron-set/mn-blueprints
python3 -m pytest -q
```

## How to customize it

Replace the Django tree fixture with another repository while preserving the fixture schema: repo identity, file path, size, SHA, source URL, component, signals, and generated relevance notes. Then tune `fixture_max_files`, `notes_per_file`, agent token budgets, pinned invariants, and risk categories for the codebase you want to evaluate.

A practical customization path is:

1. Generate or hand-curate a metadata-only tree fixture from the target repository.
2. Replace `payloads/repo_fixture/django_tree_fixture.json`.
3. Adjust hot paths, benchmark questions, and pinned facts.
4. Update role prompts for the engineering review style your team uses.
5. Compare run metrics across fixture sizes and compression settings.

## What to look for in results

The strongest signal is whether the final briefing keeps repo identity, commit SHA, subsystem claims, source item IDs, source URLs, compression metrics, and private-memory isolation while staying far smaller than the seeded memory graph.

Also inspect whether the repo architect and dependency mapper avoid private notes, whether the risk classifier sees the private security note, and whether the context compressor only sees the summarized risk result.

For benchmark comparison, treat `context_memory_benchmark_report.payload.quality_gates.passed` as the headline pass/fail and compare `aggregate_metrics.mean_compression_ratio`, `aggregate_metrics.estimated_total_tokens_processed`, `aggregate_metrics.compile_latency_seconds_p95`, and `quality_score` across runs.

## Investor and evaluator narrative

Large-repo code analysis is a concrete enterprise workflow where memory quality directly affects latency, cost, confidence, and auditability. This benchmark shows that the product value is not a larger prompt; it is controlled working memory that keeps evidence available, reduces noise, and makes agent outputs reviewable.

## Runtime features demonstrated

- Large repository fixture
- CompileContext
- role ACLs
- source_refs
- private memory isolation
- multi-agent code analysis relay
- token, latency, quality, and privacy benchmark telemetry

## Test coverage

The shared test suite verifies manifest loading, standard config sections, catalog registration, README quality sections, fixture shape, metadata-only source policy, worker script syntax, graph contract, and benchmark-report contract. Full runtime execution is an end-to-end memory-layer benchmark and requires a running MirrorNeuron core runtime plus a context engine at `MN_CONTEXT_ADDR`.

## Limitations

- The bundled fixture stores derived GitHub tree metadata, not source code text.
- Outputs are code-review decision-support artifacts, not production advice.
- The full graph requires the MirrorNeuron runtime and already-running Membrane context-engine containers.
- Live LLM behavior may vary; use `MN_BLUEPRINT_QUICK_TEST=1` for deterministic smoke runs.

## Next steps

- Add a fixture generator for arbitrary GitHub repositories.
- Compare packet size and final quality across fixture scales.
- Add golden invariant checks over final memory items after a run.
- Connect benchmark metrics to CI performance dashboards.
- Move selected run artifacts into your team's normal architecture-review workflow.
