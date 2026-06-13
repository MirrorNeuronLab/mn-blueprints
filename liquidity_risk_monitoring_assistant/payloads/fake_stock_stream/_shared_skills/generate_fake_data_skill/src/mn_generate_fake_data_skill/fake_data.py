from __future__ import annotations

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    from faker import Faker
except ImportError:  # pragma: no cover - exercised implicitly when Faker is absent
    Faker = None


class FakeDataError(ValueError):
    pass


def load_spec(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise FakeDataError(f"invalid JSON spec: {exc}") from exc
    if not isinstance(data, dict):
        raise FakeDataError("spec must be a JSON object")
    return data


def generate_batch(spec: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = _normalize_spec(spec)
    template = normalized.get("template")
    if template:
        return _generate_template_batch(normalized, template)
    count = int(normalized.get("count", 1))
    if count < 0:
        raise FakeDataError("count must be >= 0")
    context = _Context(normalized)
    return [_generate_record(normalized["schema"], context, index) for index in range(count)]


def generate_one(spec: dict[str, Any], index: int = 0) -> dict[str, Any]:
    if index < 0:
        raise FakeDataError("index must be >= 0")

    normalized = _normalize_spec(spec)
    context = _Context(normalized)
    template = normalized.get("template")
    if template:
        return _generate_template_record(normalized, template, context, index)
    return _generate_record(normalized["schema"], context, index)


def iter_stream(
    spec: dict[str, Any],
    *,
    max_events: int | None = None,
    sleep: bool = True,
) -> Iterator[dict[str, Any]]:
    normalized = _normalize_spec(spec)
    configured_max = normalized.get("max_events")
    if max_events is None and configured_max is not None:
        max_events = int(configured_max)
    if max_events is not None and max_events < 0:
        raise FakeDataError("max_events must be >= 0")

    context = _Context(normalized)
    index = 0
    while max_events is None or index < max_events:
        if sleep and index > 0:
            time.sleep(_interval_seconds(normalized, context.rng))
        template = normalized.get("template")
        if template:
            yield _generate_template_record(normalized, template, context, index)
        else:
            yield _generate_record(normalized["schema"], context, index)
        index += 1


def _normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    mode = spec.get("mode", "batch")
    if mode not in {"batch", "stream"}:
        raise FakeDataError("mode must be 'batch' or 'stream'")
    schema = spec.get("schema")
    template = spec.get("template")
    if template:
        if template not in {"stock_price_dynamic", "real_estate_trade"}:
            raise FakeDataError(f"unsupported template: {template}")
    elif not isinstance(schema, dict) or not schema:
        raise FakeDataError("schema must be a non-empty object")
    normalized = dict(spec)
    normalized["mode"] = mode
    if template and schema is None:
        normalized["schema"] = {}
    return normalized


class _Context:
    def __init__(self, spec: dict[str, Any]) -> None:
        self.seed = spec.get("seed")
        self.rng = random.Random(self.seed)
        self.fake = _build_faker(self.seed)


def _build_faker(seed: Any):
    if Faker is None:
        return None
    fake = Faker()
    if seed is not None:
        Faker.seed(seed)
        fake.seed_instance(seed)
    return fake


def _generate_record(schema: dict[str, Any], context: _Context, index: int) -> dict[str, Any]:
    return {
        field_name: _generate_value(field_spec, context, index)
        for field_name, field_spec in schema.items()
    }


def _generate_value(field_spec: Any, context: _Context, index: int) -> Any:
    if isinstance(field_spec, str):
        field_spec = {"type": field_spec}
    if not isinstance(field_spec, dict):
        raise FakeDataError(f"field spec must be a string or object, got {field_spec!r}")

    field_type = field_spec.get("type")
    if not isinstance(field_type, str) or not field_type:
        raise FakeDataError("field spec requires a string 'type'")

    if field_type == "constant":
        return field_spec.get("value")
    if field_type == "sequence":
        return int(field_spec.get("start", 1)) + index * int(field_spec.get("step", 1))
    if field_type == "integer":
        return context.rng.randint(int(field_spec.get("min", 0)), int(field_spec.get("max", 100)))
    if field_type == "float":
        value = context.rng.uniform(float(field_spec.get("min", 0.0)), float(field_spec.get("max", 1.0)))
        precision = field_spec.get("precision")
        return round(value, int(precision)) if precision is not None else value
    if field_type == "boolean":
        return context.rng.choice([True, False])
    if field_type == "choice":
        values = field_spec.get("values")
        if not isinstance(values, list) or not values:
            raise FakeDataError("choice field requires a non-empty 'values' array")
        return context.rng.choice(values)
    if field_type == "uuid4":
        return str(uuid.UUID(int=context.rng.getrandbits(128), version=4))
    if field_type in {"timestamp", "date_time_iso"}:
        return _fake_timestamp(context, index, field_spec)
    if field_type == "object":
        nested = field_spec.get("schema")
        if not isinstance(nested, dict):
            raise FakeDataError("object field requires a nested 'schema'")
        return _generate_record(nested, context, index)
    if field_type == "array":
        item_spec = field_spec.get("items", "word")
        count = int(field_spec.get("count", 1))
        return [_generate_value(item_spec, context, index + offset) for offset in range(count)]

    faker_value = _faker_value(field_type, context, field_spec)
    if faker_value is not None:
        return faker_value
    return _fallback_value(field_type, context, index)


def _fake_timestamp(context: _Context, index: int, field_spec: dict[str, Any]) -> str:
    start_raw = field_spec.get("start", "2026-01-01T00:00:00+00:00")
    step_seconds = int(field_spec.get("step_seconds", 1))
    try:
        start = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00"))
    except ValueError as exc:
        raise FakeDataError(f"invalid timestamp start: {start_raw}") from exc
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    jitter = int(field_spec.get("jitter_seconds", 0))
    offset = index * step_seconds + (context.rng.randint(0, jitter) if jitter > 0 else 0)
    return (start + timedelta(seconds=offset)).isoformat()


def _faker_value(field_type: str, context: _Context, field_spec: dict[str, Any]) -> Any:
    fake = context.fake
    if fake is None or not hasattr(fake, field_type):
        return None
    provider = getattr(fake, field_type)
    args = field_spec.get("args", [])
    kwargs = field_spec.get("kwargs", {})
    if not isinstance(args, list) or not isinstance(kwargs, dict):
        raise FakeDataError("faker args must be an array and kwargs must be an object")
    return provider(*args, **kwargs)


def _fallback_value(field_type: str, context: _Context, index: int) -> Any:
    if field_type == "name":
        return f"Alex Morgan {index + 1}"
    if field_type == "email":
        return f"user{index + 1}@example.com"
    if field_type == "company":
        return f"Example Co {index + 1}"
    if field_type == "word":
        return context.rng.choice(["alpha", "bravo", "charlie", "delta"])
    if field_type == "sentence":
        return f"Generated fake sentence {index + 1}."
    if field_type == "text":
        return f"Generated fake text block {index + 1}."
    if field_type == "phone_number":
        return f"+1-555-{1000 + index:04d}"
    if field_type == "url":
        return f"https://example.com/{index + 1}"
    if field_type == "ipv4":
        return f"192.0.2.{(index % 254) + 1}"
    raise FakeDataError(f"unsupported fake data type: {field_type}")


def _generate_template_batch(spec: dict[str, Any], template: str) -> list[dict[str, Any]]:
    count = int(spec.get("count", 1))
    if count < 0:
        raise FakeDataError("count must be >= 0")
    context = _Context(spec)
    return [_generate_template_record(spec, template, context, index) for index in range(count)]


def _generate_template_record(
    spec: dict[str, Any],
    template: str,
    context: _Context,
    index: int,
) -> dict[str, Any]:
    if template == "stock_price_dynamic":
        return _stock_price_record(spec, context, index)
    if template == "real_estate_trade":
        return _real_estate_trade_record(spec, context, index)
    raise FakeDataError(f"unsupported template: {template}")


def _stock_price_record(spec: dict[str, Any], context: _Context, index: int) -> dict[str, Any]:
    symbols = spec.get(
        "symbols",
        ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"],
    )
    base_prices = spec.get(
        "base_prices",
        {
            "AAPL": 195.0,
            "MSFT": 420.0,
            "NVDA": 880.0,
            "GOOGL": 155.0,
            "AMZN": 180.0,
            "META": 500.0,
            "TSLA": 175.0,
        },
    )
    trading_days = max(int(spec.get("trading_days", 5)), 1)
    day = index // len(symbols)
    symbol = symbols[index % len(symbols)]
    daily_volatility = float(spec.get("daily_volatility", 0.018))
    drift = float(spec.get("daily_drift", 0.001))
    max_daily_move = abs(float(spec.get("max_daily_move", 0.08)))
    base_price = float(base_prices.get(symbol, 100.0))

    price = base_price
    for step in range(day + 1):
        local = random.Random(f"{context.seed}:{symbol}:{step}")
        move = max(min(local.gauss(drift, daily_volatility), max_daily_move), -max_daily_move)
        price *= 1.0 + move

    previous_price = base_price if day == 0 else _stock_price_for_day(symbol, day - 1, base_price, spec, context)
    daily_return = price / previous_price - 1.0
    local_tick = random.Random(f"{context.seed}:{symbol}:{day}:ohlcv")
    intraday_range = abs(daily_return) + local_tick.uniform(0.002, 0.02)
    open_price = previous_price * (1.0 + daily_return * local_tick.uniform(0.1, 0.5))
    high = max(open_price, price) * (1.0 + intraday_range / 2)
    low = min(open_price, price) * (1.0 - intraday_range / 2)

    return {
        "trade_date": _date_for_index(spec, day),
        "symbol": symbol,
        "company": _ai_stock_company(symbol),
        "sector_theme": "large-cap AI infrastructure and platforms",
        "open": round(open_price, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "close": round(price, 2),
        "daily_return_pct": round(daily_return * 100, 3),
        "volume": int(local_tick.uniform(18_000_000, 95_000_000)),
        "market_note": _stock_note(daily_return),
        "day_index": min(day + 1, trading_days),
    }


def _stock_price_for_day(symbol: str, day: int, base_price: float, spec: dict[str, Any], context: _Context) -> float:
    price = base_price
    daily_volatility = float(spec.get("daily_volatility", 0.018))
    drift = float(spec.get("daily_drift", 0.001))
    max_daily_move = abs(float(spec.get("max_daily_move", 0.08)))
    for step in range(day + 1):
        local = random.Random(f"{context.seed}:{symbol}:{step}")
        move = max(min(local.gauss(drift, daily_volatility), max_daily_move), -max_daily_move)
        price *= 1.0 + move
    return price


def _ai_stock_company(symbol: str) -> str:
    return {
        "AAPL": "Apple",
        "MSFT": "Microsoft",
        "NVDA": "NVIDIA",
        "GOOGL": "Alphabet",
        "AMZN": "Amazon",
        "META": "Meta Platforms",
        "TSLA": "Tesla",
    }.get(symbol, symbol)


def _stock_note(daily_return: float) -> str:
    if daily_return >= 0.025:
        return "strong AI-led risk-on session"
    if daily_return <= -0.025:
        return "orderly pullback on profit taking"
    return "normal large-cap trading range"


def _date_for_index(spec: dict[str, Any], index: int) -> str:
    start_raw = spec.get("start_date", "2026-01-02")
    start = datetime.fromisoformat(start_raw).date()
    return (start + timedelta(days=index)).isoformat()


def _real_estate_trade_record(spec: dict[str, Any], context: _Context, index: int) -> dict[str, Any]:
    zip_code = str(spec.get("zip_code", "03755"))
    city = spec.get("city", "Hanover")
    state = spec.get("state", "NH")
    transaction_types = spec.get("transaction_types", ["buy", "sell", "rent"])
    transaction_type = context.rng.choice(transaction_types)
    beds = context.rng.randint(2, 5)
    baths = context.rng.choice([1.5, 2.0, 2.5, 3.0, 3.5])
    size_sqft = context.rng.randint(1_250, 4_200)
    lot_acres = round(context.rng.uniform(0.12, 3.5), 2)
    year_built = context.rng.randint(1880, 2022)
    features = context.rng.sample(
        [
            "hardwood floors",
            "mudroom",
            "energy-efficient windows",
            "attached garage",
            "finished basement",
            "screened porch",
            "near Dartmouth campus",
            "wooded lot",
            "updated kitchen",
        ],
        k=4,
    )
    price_per_sqft = context.rng.randint(310, 620)
    sale_price = size_sqft * price_per_sqft
    rent_price = max(2200, int(size_sqft * context.rng.uniform(1.65, 2.35)))

    return {
        "listing_id": f"RE-{zip_code}-{index + 1:05d}",
        "transaction_type": transaction_type,
        "property_type": "single_family_house",
        "address": _hanover_address(context, index),
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "bedrooms": beds,
        "bathrooms": baths,
        "size_sqft": size_sqft,
        "lot_acres": lot_acres,
        "year_built": year_built,
        "features": features,
        "description": _property_description(beds, baths, size_sqft, city, features),
        "list_price": sale_price if transaction_type in {"buy", "sell"} else rent_price,
        "price_unit": "total_sale_price" if transaction_type in {"buy", "sell"} else "monthly_rent",
        "status": context.rng.choice(["active", "pending", "recently_closed"]),
        "listed_at": _date_for_index(spec, index),
    }


def _hanover_address(context: _Context, index: int) -> str:
    streets = ["Lyme Road", "Etna Road", "Reservoir Road", "Rip Road", "Greensboro Road", "Main Street"]
    return f"{100 + index * 7 + context.rng.randint(0, 6)} {context.rng.choice(streets)}"


def _property_description(beds: int, baths: float, size_sqft: int, city: str, features: list[str]) -> str:
    return (
        f"{beds}-bed, {baths:g}-bath single-family home in {city} with "
        f"{size_sqft:,} sqft, {features[0]}, {features[1]}, and {features[2]}."
    )


def _interval_seconds(spec: dict[str, Any], rng: random.Random) -> float:
    interval = spec.get("interval", {})
    if not isinstance(interval, dict):
        raise FakeDataError("interval must be an object")
    if "ms" in interval:
        return max(float(interval["ms"]), 0.0) / 1000.0
    min_ms = float(interval.get("min_ms", spec.get("interval_ms", 1000)))
    max_ms = float(interval.get("max_ms", min_ms))
    if min_ms < 0 or max_ms < 0 or max_ms < min_ms:
        raise FakeDataError("interval min/max must be non-negative and max >= min")
    return rng.uniform(min_ms, max_ms) / 1000.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate fake data from a JSON spec.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--no-sleep", action="store_true", help="Do not sleep between stream records.")
    args = parser.parse_args(argv)

    try:
        spec = load_spec(args.spec)
        mode = spec.get("mode", "batch")
        if mode == "stream":
            rows = iter_stream(spec, max_events=args.max_events, sleep=not args.no_sleep)
            _write_jsonl(rows, args.output)
        else:
            rows = generate_batch(spec)
            _write_json(rows, args.output)
    except FakeDataError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _write_json(rows: list[dict[str, Any]], output: Path | None) -> None:
    text = json.dumps(rows, indent=2, sort_keys=True) + "\n"
    if output:
        output.write_text(text)
    else:
        print(text, end="")


def _write_jsonl(rows: Iterator[dict[str, Any]], output: Path | None) -> None:
    if output:
        with output.open("w") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
    else:
        for row in rows:
            print(json.dumps(row, sort_keys=True), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
