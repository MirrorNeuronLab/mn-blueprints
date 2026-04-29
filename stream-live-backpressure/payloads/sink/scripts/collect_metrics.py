#!/usr/bin/env python3
import json
import os
from pathlib import Path


def load_message() -> dict:
    path = os.environ.get("MIRROR_NEURON_MESSAGE_FILE") or os.environ.get("MIRROR_NEURON_INPUT_FILE")
    if not path:
        return {}
    payload = json.loads(Path(path).read_text())
    return payload.get("input", payload)


def main() -> None:
    message = load_message()
    state = message.get("agent_state") or {}
    count = int(state.get("count", 0)) + 1
    body = message.get("body", message)

    print(
        json.dumps(
            {
                "next_state": {"count": count, "last_seq": body.get("seq")},
                "events": [
                    {
                        "type": "stream_metrics_updated",
                        "payload": {
                            "processed_count": count,
                            "last_seq": body.get("seq"),
                        },
                    }
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
