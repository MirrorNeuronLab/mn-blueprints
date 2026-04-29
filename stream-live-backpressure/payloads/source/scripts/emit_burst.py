#!/usr/bin/env python3
import json
import os
from pathlib import Path


def load_input() -> dict:
    path = os.environ.get("MIRROR_NEURON_INPUT_FILE")
    if not path:
        return {}
    payload = json.loads(Path(path).read_text())
    return payload.get("input", payload)


def main() -> None:
    payload = load_input()
    count = int(os.environ.get("BURST_COUNT") or payload.get("burst_count") or 24)
    stream_id = os.environ.get("STREAM_ID", "bp-demo")

    messages = []
    for index in range(1, count + 1):
        messages.append(
            {
                "type": "telemetry_event",
                "class": "stream",
                "body": {"seq": index, "value": index * 10},
                "stream": {
                    "stream_id": stream_id,
                    "seq": index,
                    "open": index == 1,
                    "close": index == count,
                },
            }
        )

    print(
        json.dumps(
            {
                "events": [
                    {
                        "type": "source_burst_emitted",
                        "payload": {"count": count, "stream_id": stream_id},
                    }
                ],
                "emit_messages": messages,
            }
        )
    )


if __name__ == "__main__":
    main()
