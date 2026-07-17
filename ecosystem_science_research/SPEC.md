# Ecosystem Science Research Specification

## Purpose

Demonstrate that a large deterministic scientific simulation can run as
lightweight native BEAM actors while reserving an LLM for interpretation of the
finished result.

## Actor topology

The domain topology contains 19 actors: one world coordinator, 16 region
actors, one collector, and one explainer. Region actors are assigned
round-robin to the local node and all connected visible BEAM nodes. Temporary
node hosts supervise actors on each participating node and are explicitly
stopped after every successful or failed attempt.

Simulation messages use direct PIDs. Every message includes a run epoch.
Regions ignore stale epochs. Each migration batch is acknowledged by its
destination before the source reports the tick complete, and the world starts
the next tick only after all 16 regions pass the barrier.

## Scientific model

The initial population is allocated across deterministic regional profiles.
Per-tick behavior is ordered as migrant arrival, food regeneration, forage and
energy use, mortality, breeding and mutation, then migration. Incoming animals
are sorted by stable ID so cross-node mailbox scheduling cannot change results.

DNA traits and bounds:

| Trait | Bounds | Main effects |
|---|---:|---|
| metabolism | 0.65–1.45 | Energy upkeep and mortality pressure |
| forage | 0.55–1.60 | Feeding priority and energy gain |
| breed | 0.55–1.55 | Reproduction probability |
| aggression | 0.00–1.20 | Feeding priority and migration |
| move | 0.00–1.20 | Migration selection |
| longevity | 0.70–1.65 | Maximum age and mortality protection |

Offspring blend parental traits and may mutate by at most 0.08 before bounds
are applied.

## Explanation boundary

The collector first freezes the deterministic result. The explainer receives a
compact copy containing regional summaries, the global population trajectory,
and the top DNA lineages. It may describe patterns and caveats but cannot alter
measurements. Live mode performs at most one OpenAI-compatible request. Fake,
unavailable, or invalid model responses produce a clearly labelled deterministic
fallback without failing the scientific run.

## Success criteria

- Exactly 16 regions complete all configured ticks.
- `final_population = initial_population + births - deaths`.
- Global migration in equals migration out.
- Every DNA value remains within its declared bounds.
- Same seed and parameters yield the same simulation result independent of
  actor placement and mailbox timing.
- Multi-node runs report at least one cross-node migration when migration occurs.
- No simulation source invokes MirrorNeuron durable delivery or an OS worker.
