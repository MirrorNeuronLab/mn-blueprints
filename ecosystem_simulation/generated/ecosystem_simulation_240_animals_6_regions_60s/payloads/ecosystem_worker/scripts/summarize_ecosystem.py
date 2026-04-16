#!/usr/bin/env python3
import json
import os
from collections import defaultdict
from pathlib import Path


def load_input() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())


def summarize(messages: list[dict]) -> dict:
    lineages: dict[str, dict] = {}
    regions = []
    population = births = deaths = migrants_in = migrants_out = 0

    for region_summary in messages:
        regions.append(region_summary["region_id"])
        population += region_summary["population"]
        births += region_summary["births"]
        deaths += region_summary["deaths"]
        migrants_in += region_summary["migrants_in"]
        migrants_out += region_summary["migrants_out"]

        for lineage in region_summary.get("top_lineages", []):
            key = lineage["dna_key"]
            entry = lineages.setdefault(
                key,
                {
                    "dna_key": key,
                    "dna": lineage["dna"],
                    "alive": 0,
                    "generation_max": 0,
                    "avg_energy_weighted": 0.0,
                    "regions_present": set(),
                },
            )
            entry["alive"] += lineage["alive"]
            entry["generation_max"] = max(entry["generation_max"], lineage["generation_max"])
            entry["avg_energy_weighted"] += lineage["avg_energy"] * lineage["alive"]
            entry["regions_present"].add(region_summary["region_id"])

    ranked = []
    for entry in lineages.values():
        alive = max(entry["alive"], 1)
        avg_energy = round(entry["avg_energy_weighted"] / alive, 2)
        ranked.append(
            {
                "dna_key": entry["dna_key"],
                "dna": entry["dna"],
                "alive": entry["alive"],
                "generation_max": entry["generation_max"],
                "avg_energy": avg_energy,
                "regions_present": sorted(entry["regions_present"]),
                "fitness_score": round(entry["alive"] * 100 + entry["generation_max"] * 5 + avg_energy, 2),
            }
        )

    ranked.sort(
        key=lambda item: (item["alive"], item["generation_max"], item["avg_energy"]),
        reverse=True,
    )

    history_tail = {
        summary["region_id"]: summary.get("history_tail", [])[-3:]
        for summary in messages
    }

    return {
        "mode": "ecosystem_simulation",
        "regions": sorted(regions),
        "region_count": len(regions),
        "population_alive": population,
        "births": births,
        "deaths": deaths,
        "migrants_in": migrants_in,
        "migrants_out": migrants_out,
        "top_10_dna": ranked[:10],
        "region_history_tail": history_tail,
    }


def main() -> None:
    incoming = load_input()
    messages = incoming.get("messages", [])
    print(json.dumps({"complete_job": summarize(messages)}))


if __name__ == "__main__":
    main()
