#!/usr/bin/env python3
import json
import os
import random
import sys
import time
from pathlib import Path


WORKDIR = Path(__file__).resolve().parents[1]
SHARED_SKILL = WORKDIR / "_shared_skills" / "generate_fake_data_skill" / "src"
if SHARED_SKILL.exists():
    sys.path.insert(0, str(SHARED_SKILL))

from mn_generate_fake_data_skill import generate_one


def load_json_env(name: str) -> dict:
    path = os.environ.get(name)
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def interval_seconds(spec: dict, index: int) -> float:
    interval = spec.get("interval", {})
    if "ms" in interval:
        return max(float(interval["ms"]), 0.0) / 1000.0

    min_ms = float(interval.get("min_ms", spec.get("interval_ms", 1000)))
    max_ms = float(interval.get("max_ms", min_ms))
    rng = random.Random(f"{spec.get('seed')}:{index}:interval")
    return rng.uniform(min_ms, max_ms) / 1000.0


def build_spec(payload: dict, config: dict) -> dict:
    return {
        "mode": "stream",
        "template": "stock_price_dynamic",
        "seed": payload.get("seed", config.get("seed", 729905862)),
        "start_date": config.get("start_date", "2026-04-30"),
        "symbols": config.get("symbols", ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]),
        "trading_days": config.get("trading_days", 252),
        "daily_volatility": config.get("daily_volatility", 0.018),
        "daily_drift": config.get("daily_drift", 0.001),
        "max_daily_move": config.get("max_daily_move", 0.06),
        "interval": {
            "min_ms": config.get("interval_min_ms", config.get("interval_ms", 1000)),
            "max_ms": config.get("interval_max_ms", config.get("interval_ms", 1000)),
        },
    }


def main() -> None:
    context = load_json_env("MN_CONTEXT_FILE")
    payload = load_json_env("MN_INPUT_FILE")
    config = {
        "seed": int(os.environ.get("STOCK_STREAM_SEED", payload.get("seed", 729905862))),
        "start_date": os.environ.get("STOCK_STREAM_START_DATE", "2026-04-30"),
        "symbols": [item.strip() for item in os.environ.get("STOCK_STREAM_SYMBOLS", "AAPL,MSFT,NVDA,GOOGL,AMZN,META,TSLA").split(",") if item.strip()],
        "trading_days": int(os.environ.get("STOCK_STREAM_TRADING_DAYS", "252")),
        "daily_volatility": float(os.environ.get("STOCK_STREAM_DAILY_VOLATILITY", "0.018")),
        "daily_drift": float(os.environ.get("STOCK_STREAM_DAILY_DRIFT", "0.001")),
        "max_daily_move": float(os.environ.get("STOCK_STREAM_MAX_DAILY_MOVE", "0.06")),
        "interval_min_ms": int(os.environ.get("STOCK_STREAM_INTERVAL_MIN_MS", "1000")),
        "interval_max_ms": int(os.environ.get("STOCK_STREAM_INTERVAL_MAX_MS", "1000")),
        "target_node": os.environ.get("STOCK_STREAM_TARGET_NODE", "stock_signal_analyzer"),
    }
    state = context.get("agent_state") or {}

    event_index = int(state.get("event_index", 0))
    agent_id = os.environ.get("MN_AGENT_ID", "fake_stock_stream")
    stream_id = state.get("stream_id") or payload.get("stream_id") or f"{context.get('job_id')}:{agent_id}:fake-stock-prices"
    spec = build_spec(payload, config)

    if event_index > 0:
        time.sleep(interval_seconds(spec, event_index))

    tick = generate_one(spec, event_index)
    tick["event_index"] = event_index
    tick["stream_id"] = stream_id

    next_state = {
        "event_index": event_index + 1,
        "stream_id": stream_id,
        "last_symbol": tick["symbol"],
        "last_price": tick["close"],
    }

    result = {
        "next_state": next_state,
        "events": [
            {
                "type": "fake_stock_tick_generated",
                "payload": {
                    "stream_id": stream_id,
                    "event_index": event_index,
                    "symbol": tick["symbol"],
                    "close": tick["close"],
                    "daily_return_pct": tick["daily_return_pct"],
                },
            }
        ],
        "emit_messages": [
            {
                "to": config.get("target_node", "stock_signal_analyzer"),
                "type": "stock_price_tick",
                "class": "stream",
                "payload": tick,
                "headers": {
                    "schema_ref": "com.mirrorneuron.finance.fake_stock_price_tick",
                    "schema_version": "1.0.0",
                    "source_skill": "generate_fake_data_skill",
                },
                "stream": {
                    "stream_id": stream_id,
                    "seq": event_index + 1,
                    "open": event_index == 0,
                },
            },
            {
                "to": agent_id,
                "type": "generate_next_stock_tick",
                "class": "control",
                "payload": {"stream_id": stream_id},
            },
        ],
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
