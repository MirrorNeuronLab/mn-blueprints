# Ecosystem Science Research

This standalone MirrorNeuron blueprint runs a deterministic ecosystem model as
native OTP actors. A world coordinator distributes exactly 16 region actors
round-robin over the connected BEAM cluster. Regions exchange migrants with
direct PID messages; Docker, OpenShell, HostLocal workers, and Redis delivery
are not used inside the simulation. Each completed run also includes a
self-contained static web replay of the frozen simulation.

The model tracks 2,000 animals by default. Each animal carries six inherited
traits—metabolism, forage, breed, aggression, move, and longevity—that affect
feeding, survival, reproduction, and migration. One LLM call is allowed only
after the deterministic collector has produced the final scientific result.

## Run

```bash
cd /Users/homer/Projects/mn-blueprints/ecosystem_science_research
mn blueprint validate . --output json
mn blueprint run --folder . --fake-llm --follow-seconds 5
```

The default config is fake so validation and the scientific demo require no
model download. For a live explanation, copy the `llm` object from
`config/live.example.json` into `config/overwrite.json`, then use the standard
model configuration and environment supported by `vc_assistant`. A missing or
invalid live model still finishes with an explicit deterministic fallback.

## Inputs

Override the mock payload with `json`, `file`, or `env_json`. The region count is
fixed at 16. The configurable model parameters are:

- `seed`
- `total_animals`
- `duration_seconds` and `tick_seconds`
- `max_food` and `food_regen_per_tick`
- `max_region_population`
- `migration_rate` and `mutation_rate`
- `tick_delay_ms`
- `require_multi_node`

Completed artifacts are written to `outputs.folder_path`. The default is
`~/Downloads/ecosystem_science_research`, and it can be changed in
`config/overwrite.json` or through the blueprint's standard output-folder
configuration.

When no peer node is connected, the exact same direct-message protocol runs on
one BEAM node and the final artifact records a distribution warning.

## Outputs

The result separates deterministic measurements from the model explanation and
publishes an offline replay UI:

- `simulation_result.json` — regional measurements and global lineage ranking
- `actor_topology.json` — actor placement and direct-message evidence
- `final_artifact.json` — immutable simulation result plus explanation, caveats, and UI metadata
- `web/index.html` — self-contained timeline replay with playback, region inspection, ecology metrics, and lineage summary
- `web_ui.json` — standard static HTML UI handle for the configured output folder

The JSON artifacts and replay UI are written directly to the configured output
folder; the MirrorNeuron run store remains available for run metadata and
execution logs.

The UI embeds the versioned `mn.ecosystem.visualization.v1` projection, so it
can be opened directly from the configured output folder without a running server or
network access. Playback is a replay of the completed deterministic run; it
does not rerun the simulation or change its measurements.

The blueprint is a research demonstration, not a calibrated ecological model or
an autonomous field-intervention system.

## Verify

```bash
bash tests/static_guard.sh
cd /Users/homer/Projects/mirror-neuron-set/MirrorNeuron
elixir --sname ecosystem_science_test -S mix run --no-start \
  /Users/homer/Projects/mn-blueprints/ecosystem_science_research/tests/ecosystem_actor_system_test.exs
elixir -S mix run --no-start \
  /Users/homer/Projects/mn-blueprints/ecosystem_science_research/tests/ecosystem_web_ui_test.exs
```

The actor test checks determinism, conservation, trait bounds, cleanup, and a
two-node direct-BEAM migration path when the local OTP installation supports
`:peer`.
