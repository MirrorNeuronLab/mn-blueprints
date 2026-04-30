#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path


def load_message() -> dict:
    path = os.environ.get("MIRROR_NEURON_MESSAGE_FILE") or os.environ.get("MIRROR_NEURON_INPUT_FILE")
    if not path:
        return {}
    payload = json.loads(Path(path).read_text())
    return payload.get("input", payload)


def main() -> None:
    message = load_message()
    body = message.get("body", message)
    slow_ms = int(os.environ.get("SLOW_MS", "350"))
    started = time.time()
    time.sleep(max(slow_ms, 0) / 1000)
    elapsed_ms = int((time.time() - started) * 1000)

    seq = body.get("seq") or message.get("seq")
    enriched = {
        "seq": seq,
        "value": body.get("value"),
        "enriched": True,
        "slow_ms": elapsed_ms,
    }

    print(
        json.dumps(
            {
                "events": [
                    {
                        "type": "slow_event_processed",
                        "payload": {
                            "seq": seq,
                            "processing_ms": elapsed_ms,
                            "worker": "slow_enricher",
                            "manual_delay_ms": slow_ms,
                            "reason": "manual slowdown to trigger bounded-queue backpressure",
                        },
                    }
                ],
                "output": enriched,
            }
        )
    )


if __name__ == "__main__":
    main()
