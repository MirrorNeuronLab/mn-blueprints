#!/usr/bin/env python3
import json
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Optional


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def load_message() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_MESSAGE_FILE"]).read_text())


def load_context() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_CONTEXT_FILE"]).read_text())


def message_type(message: dict) -> str:
    envelope = message.get("envelope") or {}
    return envelope.get("type") or message.get("type") or ""


def body(message: dict):
    return message.get("body") or message.get("payload") or {}


def dna_key(dna: dict) -> str:
    return (
        f"m{dna['metabolism']:.2f}"
        f"-f{dna['forage']:.2f}"
        f"-b{dna['breed']:.2f}"
        f"-a{dna['aggression']:.2f}"
        f"-v{dna['move']:.2f}"
        f"-l{dna['longevity']:.2f}"
    )


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def steps() -> int:
    return max(1, env_int("DURATION_SECONDS", 300) // env_int("TICK_SECONDS", 5))


def region_index() -> int:
    return env_int("REGION_INDEX", 0)


def region_id() -> str:
    return os.environ.get("REGION_ID", f"region_{region_index():02d}")


def rng_for_tick(tick: int) -> random.Random:
    seed = env_int("SIMULATION_SEED", 42)
    return random.Random(seed + region_index() * 100_003 + tick * 97)


def allocated_animals() -> int:
    total = env_int("TOTAL_ANIMALS", 2000)
    regions = env_int("REGION_COUNT", 16)
    base = total // regions
    remainder = total % regions
    return base + (1 if region_index() < remainder else 0)


def initial_dna(rng: random.Random) -> dict:
    dna = {
        "metabolism": round(rng.uniform(0.75, 1.30), 2),
        "forage": round(rng.uniform(0.65, 1.45), 2),
        "breed": round(rng.uniform(0.60, 1.40), 2),
        "aggression": round(rng.uniform(0.00, 1.00), 2),
        "move": round(rng.uniform(0.00, 1.00), 2),
        "longevity": round(rng.uniform(0.80, 1.45), 2),
    }
    return dna


def create_animal(serial: int, rng: random.Random, dna: Optional[dict] = None, generation: int = 0) -> dict:
    dna = dna or initial_dna(rng)
    return {
        "id": f"{region_id()}-animal-{serial:05d}",
        "generation": generation,
        "energy": round(rng.uniform(72.0, 110.0), 2),
        "age": 0,
        "dna": dna,
        "dna_key": dna_key(dna),
    }


def initialize_state() -> dict:
    rng = rng_for_tick(0)
    animals = [create_animal(index, rng) for index in range(allocated_animals())]
    return {
        "region_id": region_id(),
        "tick": 0,
        "food": env_float("MAX_FOOD", 420.0) * 0.65,
        "animals": animals,
        "migration_inbox": {},
        "births": 0,
        "deaths": 0,
        "migrants_in": 0,
        "migrants_out": 0,
        "next_serial": len(animals),
        "history": [],
    }


def ingest_migrants(state: dict, tick: int) -> list[dict]:
    inbox = state.setdefault("migration_inbox", {})
    arrivals = inbox.pop(str(tick), [])
    if arrivals:
        state["animals"].extend(arrivals)
        state["migrants_in"] += len(arrivals)
    return arrivals


def stage_migrants(state: dict, incoming: dict) -> dict:
    arrival_tick = int(incoming.get("arrival_tick", state.get("tick", 0) + 2))
    migrants = incoming.get("animals", [])
    if not migrants:
        return state

    inbox = state.setdefault("migration_inbox", {})
    inbox.setdefault(str(arrival_tick), [])
    inbox[str(arrival_tick)].extend(migrants)
    return state


def forage_pass(animals: list[dict], food: float, tick: int) -> tuple[list[dict], float]:
    rng = rng_for_tick(tick)
    scarcity = len(animals) / max(1, env_int("MAX_REGION_POPULATION", 220))
    ranked = sorted(
        animals,
        key=lambda animal: animal["dna"]["forage"] * rng.uniform(0.85, 1.2)
        + animal["dna"]["aggression"] * scarcity * 0.45,
        reverse=True,
    )

    updated = []
    for animal in ranked:
        upkeep = env_int("TICK_SECONDS", 5) * (1.15 + animal["dna"]["metabolism"] * 1.45)
        appetite = 6.0 + animal["dna"]["forage"] * 3.0
        consumed = min(food, appetite)
        food -= consumed
        gain = consumed * (1.85 + animal["dna"]["forage"] * 0.55)
        animal = dict(animal)
        animal["energy"] = round(animal["energy"] + gain - upkeep, 2)
        animal["age"] += env_int("TICK_SECONDS", 5)
        updated.append(animal)

    return updated, max(food, 0.0)


def survivors_and_dead(animals: list[dict], tick: int) -> tuple[list[dict], int]:
    survivors = []
    dead = 0

    for animal in animals:
        max_age = 120 + animal["dna"]["longevity"] * 220
        if animal["energy"] <= 0 or animal["age"] >= max_age:
            dead += 1
            continue
        survivors.append(animal)

    return survivors, dead


def breed_animals(state: dict, tick: int) -> tuple[list[dict], int]:
    rng = rng_for_tick(tick + 1_000)
    animals = sorted(state["animals"], key=lambda item: item["energy"], reverse=True)
    newborns = []
    max_population = env_int("MAX_REGION_POPULATION", 220)

    eligible = [
        animal
        for animal in animals
        if animal["age"] >= 20 and animal["energy"] >= 95.0 and rng.random() <= animal["dna"]["breed"] * 0.24
    ]

    while len(eligible) >= 2 and len(state["animals"]) + len(newborns) < max_population:
        parent_a = eligible.pop(0)
        parent_b = eligible.pop(0)
        parent_a["energy"] = round(parent_a["energy"] - 16.0, 2)
        parent_b["energy"] = round(parent_b["energy"] - 16.0, 2)
        child_dna = mix_dna(parent_a["dna"], parent_b["dna"], rng)
        child = create_animal(state["next_serial"], rng, child_dna, generation=max(parent_a["generation"], parent_b["generation"]) + 1)
        state["next_serial"] += 1
        child["energy"] = round(52.0 + rng.uniform(-4.0, 6.0), 2)
        newborns.append(child)

    return newborns, len(newborns)


def mix_dna(left: dict, right: dict, rng: random.Random) -> dict:
    mutation_rate = env_float("MUTATION_RATE", 0.08)
    child = {}
    for trait in ["metabolism", "forage", "breed", "aggression", "move", "longevity"]:
        blended = (left[trait] + right[trait]) / 2.0
        if rng.random() <= mutation_rate:
            blended += rng.uniform(-0.12, 0.12)

        bounds = {
            "metabolism": (0.65, 1.45),
            "forage": (0.55, 1.55),
            "breed": (0.55, 1.55),
            "aggression": (0.0, 1.2),
            "move": (0.0, 1.2),
            "longevity": (0.70, 1.60),
        }
        low, high = bounds[trait]
        child[trait] = round(clamp(blended, low, high), 2)
    return child


def choose_migrants(state: dict, tick: int) -> tuple[list[dict], dict]:
    animals = state["animals"]
    if not animals:
        return [], {}

    rng = rng_for_tick(tick + 2_000)
    max_population = env_int("MAX_REGION_POPULATION", 220)
    pressure = max(0.0, (len(animals) - max_population * 0.72) / max_population)
    limit = min(4, int(len(animals) * env_float("MIGRATION_RATE", 0.035) + pressure * 5))

    if limit <= 0:
        return animals, {}

    ranked = sorted(
        animals,
        key=lambda item: item["dna"]["move"] * 1.4 + item["dna"]["aggression"] * 0.35 + rng.uniform(0.0, 0.25),
        reverse=True,
    )
    movers = ranked[:limit]
    survivors = [animal for animal in animals if animal["id"] not in {item["id"] for item in movers}]

    regions = env_int("REGION_COUNT", 16)
    migration_payloads: dict[str, list[dict]] = defaultdict(list)

    for offset, animal in enumerate(movers):
        direction = -1 if offset % 2 else 1
        destination = (region_index() + direction) % regions
        migration_payloads[f"region_{destination:02d}"].append(animal)

    return survivors, migration_payloads


def lineage_snapshot(animals: list[dict]) -> dict:
    lineages: dict[str, dict] = {}
    for animal in animals:
        key = animal["dna_key"]
        entry = lineages.setdefault(
            key,
            {
                "dna": animal["dna"],
                "dna_key": key,
                "alive": 0,
                "avg_energy_total": 0.0,
                "generation_max": 0,
            },
        )
        entry["alive"] += 1
        entry["avg_energy_total"] += animal["energy"]
        entry["generation_max"] = max(entry["generation_max"], animal["generation"])

    for entry in lineages.values():
        entry["avg_energy"] = round(entry["avg_energy_total"] / max(1, entry["alive"]), 2)
        del entry["avg_energy_total"]
    return lineages


def region_summary(state: dict) -> dict:
    local_top_k = env_int("LOCAL_TOP_K", 20)
    lineages = list(lineage_snapshot(state["animals"]).values())
    top = sorted(
        lineages,
        key=lambda item: (item["alive"], item["generation_max"], item["avg_energy"]),
        reverse=True,
    )[:local_top_k]

    return {
        "region_id": state["region_id"],
        "ticks_completed": state["tick"],
        "population": len(state["animals"]),
        "food_remaining": round(state["food"], 2),
        "births": state["births"],
        "deaths": state["deaths"],
        "migrants_in": state["migrants_in"],
        "migrants_out": state["migrants_out"],
        "history_tail": state["history"][-10:],
        "top_lineages": top,
    }


def tick_events(state: dict, births: int, deaths: int, arrivals: int, outgoing: int) -> list[dict]:
    return [
        {
            "type": "region_tick_processed",
            "payload": {
                "region_id": state["region_id"],
                "tick": state["tick"],
                "population": len(state["animals"]),
                "food": round(state["food"], 2),
                "births": births,
                "deaths": deaths,
                "arrivals": arrivals,
                "migrants_out": outgoing,
            },
        }
    ]


def process_tick(state: dict, tick: int) -> dict:
    arrivals = ingest_migrants(state, tick)
    state["food"] = min(env_float("MAX_FOOD", 420.0), state["food"] + env_float("FOOD_REGEN_PER_TICK", 72.0))

    animals, food = forage_pass(state["animals"], state["food"], tick)
    survivors, dead = survivors_and_dead(animals, tick)
    state["animals"] = survivors
    state["food"] = food
    state["deaths"] += dead

    newborns, birth_count = breed_animals(state, tick)
    state["animals"].extend(newborns)
    state["births"] += birth_count

    state["animals"], migration_payloads = choose_migrants(state, tick)
    outgoing = sum(len(items) for items in migration_payloads.values())
    state["migrants_out"] += outgoing
    state["tick"] = tick
    state["history"].append(
        {
            "tick": tick,
            "population": len(state["animals"]),
            "food": round(state["food"], 2),
            "births": birth_count,
            "deaths": dead,
        }
    )

    emit_messages = []
    arrival_tick = tick + 2

    for destination, migrants in migration_payloads.items():
        emit_messages.append(
            {
                "to": destination,
                "type": "migration_batch",
                "body": {
                    "from_region": state["region_id"],
                    "arrival_tick": arrival_tick,
                    "animals": migrants,
                },
                "class": "event",
                "headers": {"schema_ref": "com.mirrorneuron.ecosystem.migration"},
            }
        )

    if tick < steps():
        emit_messages.append(
            {
                "to": state["region_id"],
                "type": "region_tick",
                "body": {"tick": tick + 1},
                "class": "command",
                "headers": {"schema_ref": "com.mirrorneuron.ecosystem.tick"},
            }
        )
    else:
        emit_messages.append(
            {
                "type": "region_summary",
                "body": region_summary(state),
                "class": "event",
                "headers": {"schema_ref": "com.mirrorneuron.ecosystem.region_summary"},
            }
        )

    return {
        "next_state": state,
        "events": tick_events(state, birth_count, dead, len(arrivals), outgoing),
        "emit_messages": emit_messages,
    }


def main() -> None:
    message = load_message()
    context = load_context()
    state = context.get("agent_state") or {}
    kind = message_type(message)
    incoming = body(message)

    if kind == "simulation_start":
        state = initialize_state()
        result = {
            "next_state": state,
            "events": [
                {
                    "type": "region_initialized",
                    "payload": {
                        "region_id": state["region_id"],
                        "population": len(state["animals"]),
                        "food": round(state["food"], 2),
                    },
                }
            ],
            "emit_messages": [
                {
                    "to": state["region_id"],
                    "type": "region_tick",
                    "body": {"tick": 1},
                    "class": "command",
                    "headers": {"schema_ref": "com.mirrorneuron.ecosystem.tick"},
                }
            ],
        }
    elif kind == "migration_batch":
        if not state:
            state = initialize_state()
        state = stage_migrants(state, incoming)
        result = {
            "next_state": state,
            "events": [
                {
                    "type": "migration_staged",
                    "payload": {
                        "region_id": state["region_id"],
                        "arrival_tick": int(incoming.get("arrival_tick", state["tick"] + 2)),
                        "count": len(incoming.get("animals", [])),
                    },
                }
            ],
        }
    elif kind == "region_tick":
        if not state:
            state = initialize_state()
        result = process_tick(state, int(incoming.get("tick", state.get("tick", 0) + 1)))
    else:
        result = {
            "next_state": state or initialize_state(),
            "events": [{"type": "region_message_ignored", "payload": {"message_type": kind or "unknown"}}],
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
