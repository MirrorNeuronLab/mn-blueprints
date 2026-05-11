from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_events(path: str | Path) -> list[dict[str, Any]]:
    """Load events from a JSON array, JSON object with events, or JSONL file."""
    event_path = Path(path)
    if not event_path.exists():
        raise FileNotFoundError(f"event input file does not exist: {event_path}")

    if event_path.suffix.lower() == ".jsonl":
        events: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(event_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{event_path}:{line_number} must contain a JSON object")
            events.append(value)
        return events

    value = json.loads(event_path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ValueError(f"{event_path} must contain only JSON objects")
        return list(value)
    if isinstance(value, dict) and isinstance(value.get("events"), list):
        events = value["events"]
        if not all(isinstance(item, dict) for item in events):
            raise ValueError(f"{event_path} events must contain only JSON objects")
        return list(events)
    if isinstance(value, dict):
        return [value]
    raise ValueError(f"{event_path} must contain a JSON object, JSON array, or JSONL objects")

