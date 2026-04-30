# Generate Fake Data Skill

Generate deterministic fake data from a JSON spec in batch or stream mode.

The skill uses `Faker` when it is installed and falls back to built-in deterministic generators when it is not.

## Spec

```json
{
  "mode": "batch",
  "seed": 42,
  "count": 3,
  "schema": {
    "id": {"type": "sequence", "start": 1000},
    "name": "name",
    "email": "email",
    "plan": {"type": "choice", "values": ["free", "pro"]},
    "score": {"type": "integer", "min": 0, "max": 100}
  }
}
```

For streaming, use `mode: "stream"` and an interval:

```json
{
  "mode": "stream",
  "seed": 7,
  "max_events": 10,
  "interval": {"min_ms": 250, "max_ms": 1000},
  "schema": {
    "event_id": "uuid4",
    "ts": "date_time_iso",
    "value": {"type": "float", "min": 0, "max": 1, "precision": 4}
  }
}
```

## CLI

```bash
python3 -m mn_generate_fake_data_skill spec.json --output out.json
python3 -m mn_generate_fake_data_skill stream-spec.json --max-events 5
```

Batch mode writes a JSON array by default. Stream mode writes JSON Lines to stdout or the output file.
