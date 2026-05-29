#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path


def load_message() -> dict:
    path = os.environ.get("MN_MESSAGE_FILE") or os.environ.get("MN_INPUT_FILE")
    if not path:
        return {}
    payload = json.loads(Path(path).read_text())
    return payload.get("input", payload)


def main() -> None:
    message = load_message()
    state = message.get("agent_state") or {}
    count = int(state.get("count", 0)) + 1
    body = message.get("body", message)
    slow_ms = int(os.environ.get("SINK_SLOW_MS", "0"))
    started = time.time()
    time.sleep(max(slow_ms, 0) / 1000)
    elapsed_ms = int((time.time() - started) * 1000)

    print(
        json.dumps(
            {
                "next_state": {"count": count, "last_seq": body.get("seq")},
                "events": [
                    {
                        "type": "stream_metrics_updated",
                        "payload": {
                            "worker": "metrics_sink",
                            "processed_count": count,
                            "last_seq": body.get("seq"),
                            "processing_ms": elapsed_ms,
                            "manual_delay_ms": slow_ms,
                        },
                    }
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
