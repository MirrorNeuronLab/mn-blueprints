#!/usr/bin/env python3
import argparse
import json
import math
import secrets
import shutil
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "mn-skills" / "blueprint_support_skill" / "src"),
)
from mn_blueprint_support import apply_quick_test, log_status, progress, write_manifest


def build_manifest(args: argparse.Namespace) -> dict:
    shared_config = {
        "total_animals": args.animals,
        "region_count": args.regions,
        "duration_seconds": args.duration_seconds,
        "tick_seconds": args.tick_seconds,
        "max_food": args.max_food,
        "food_regen_per_tick": args.food_regen_per_tick,
        "max_region_population": args.max_region_population,
        "migration_rate": args.migration_rate,
        "mutation_rate": args.mutation_rate,
        "tick_delay_ms": args.tick_delay_ms,
        "seed": args.seed,
        "local_top_k": args.local_top_k,
    }

    nodes = [
        {
            "node_id": "ingress",
            "agent_type": "router",
            "type": "map",
            "role": "root_coordinator",
            "config": {"emit_type": "simulation_start"},
        },
        {
            "node_id": "world",
            "agent_type": "module",
            "type": "reduce",
            "role": "world",
            "config": {
                **shared_config,
                "module": "MirrorNeuron.Examples.EcosystemSimulation.WorldAgent",
                "module_source": "beam_modules/world_agent.ex",
            },
        },
        {
            "node_id": "collector",
            "agent_type": "aggregator",
            "type": "reduce",
            "config": {
                "complete_after": args.regions,
                "output_message_type": "region_collection",
            },
        },
        {
            "node_id": "summarizer",
            "agent_type": "module",
            "type": "reduce",
            "config": {
                "module": "MirrorNeuron.Examples.EcosystemSimulation.LeaderboardAgent",
                "module_source": "beam_modules/leaderboard_agent.ex",
            },
        },
    ]

    edges = []

    for index in range(args.regions):
        region_id = f"region_{index:02d}"

        nodes.append(
            {
                "node_id": region_id,
                "agent_type": "module",
                "type": "reduce",
                "role": "region",
                "config": {
                    **shared_config,
                    "module": "MirrorNeuron.Examples.EcosystemSimulation.RegionAgent",
                    "module_source": "beam_modules/region_agent.ex",
                    "region_index": index,
                },
            }
        )

        edges.append(
            {
                "edge_id": f"world_to_{region_id}",
                "from_node": "world",
                "to_node": region_id,
                "message_type": "region_bootstrap",
            }
        )
        edges.append(
            {
                "edge_id": f"{region_id}_to_collector",
                "from_node": region_id,
                "to_node": "collector",
                "message_type": "region_summary",
            }
        )

    edges.append(
        {
            "edge_id": "ingress_to_world",
            "from_node": "ingress",
            "to_node": "world",
            "message_type": "simulation_start",
        }
    )

    edges.append(
        {
            "edge_id": "collector_to_summarizer",
            "from_node": "collector",
            "to_node": "summarizer",
            "message_type": "region_collection",
        }
    )

    return {
        "manifest_version": "1.0",
        "graph_id": "science_ecosystem_intervention_sandbox_v1",
        "job_name": "ecosystem-simulation",
        "entrypoints": ["ingress"],
        "initial_inputs": {
            "ingress": [
                {
                    "scenario": "ecosystem_competition",
                    "animals": args.animals,
                    "regions": args.regions,
                    "duration_seconds": args.duration_seconds,
                    "tick_seconds": args.tick_seconds,
                    "max_region_population": args.max_region_population,
                    "seed": args.seed,
                }
            ]
        },
        "nodes": nodes,
        "edges": edges,
        "policies": {"recovery_mode": "cluster_recover"},
    }


def bundle_name(args: argparse.Namespace) -> str:
    return (
        f"science_ecosystem_intervention_sandbox_{args.animals}_animals_"
        f"{args.regions}_regions_{args.duration_seconds}s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the ecosystem simulation bundle.")
    parser.add_argument("--animals", type=int, default=2000)
    parser.add_argument("--regions", type=int, default=16)
    parser.add_argument("--duration-seconds", type=int, default=300)
    parser.add_argument("--tick-seconds", type=int, default=5)
    parser.add_argument("--max-food", type=float, default=420.0)
    parser.add_argument("--food-regen-per-tick", type=float, default=72.0)
    parser.add_argument("--max-region-population", type=int, default=220)
    parser.add_argument("--migration-rate", type=float, default=0.035)
    parser.add_argument("--mutation-rate", type=float, default=0.05)
    parser.add_argument("--tick-delay-ms", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--local-top-k", type=int, default=20)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--retry-backoff-ms", type=int, default=200)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Generate a tiny deterministic simulation bundle for fast validation.",
    )
    args = parser.parse_args()

    quick_test = apply_quick_test(
        args,
        {
            "animals": 40,
            "regions": 2,
            "duration_seconds": 30,
            "tick_seconds": 5,
            "tick_delay_ms": 0,
            "local_top_k": 5,
            "max_attempts": 1,
            "retry_backoff_ms": 0,
            "seed": 42,
        },
    )
    log_status(
        "science_ecosystem_intervention_sandbox",
        "generating ecosystem simulation bundle",
        phase="generate",
        details={"quick_test": quick_test, "regions": args.regions, "animals": args.animals},
    )

    args.animals = max(args.animals, 10)
    args.regions = max(args.regions, 2)
    args.duration_seconds = max(args.duration_seconds, 30)
    args.tick_seconds = max(args.tick_seconds, 1)
    if args.seed is None:
        args.seed = secrets.randbelow(1_000_000_000)
    args.max_region_population = max(
        args.max_region_population, math.ceil(args.animals / args.regions) + 20
    )

    root = Path(__file__).resolve().parent
    bundle_dir = args.output_dir


    bundle_dir.mkdir(parents=True, exist_ok=True)
    payloads_dir = bundle_dir / "payloads"
    payloads_dir.mkdir(parents=True, exist_ok=True)
    beam_modules_src = root / "payloads" / "beam_modules"
    beam_modules_dest = payloads_dir / "beam_modules"
    if bundle_dir.resolve() != Path(__file__).resolve().parent:
        shutil.copytree(beam_modules_src, beam_modules_dest, dirs_exist_ok=True)

    manifest = build_manifest(args)
    write_manifest(
        bundle_dir / "manifest.json",
        manifest,
        blueprint_id="science_ecosystem_intervention_sandbox",
        quick_test=quick_test,
    )
    print(progress("bundle generated", 1, 1), file=sys.stderr)
    print(bundle_dir)


if __name__ == "__main__":
    main()
