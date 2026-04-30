import json
from pathlib import Path

from mn_generate_fake_data_skill import generate_batch, generate_one, iter_stream, load_spec


def test_generate_batch_with_common_types():
    rows = generate_batch(
        {
            "mode": "batch",
            "seed": 42,
            "count": 3,
            "schema": {
                "id": {"type": "sequence", "start": 10},
                "email": "email",
                "score": {"type": "integer", "min": 1, "max": 1},
                "plan": {"type": "choice", "values": ["free"]},
            },
        }
    )

    assert [row["id"] for row in rows] == [10, 11, 12]
    assert rows[0]["score"] == 1
    assert rows[0]["plan"] == "free"
    assert "@" in rows[0]["email"]


def test_iter_stream_without_sleep_uses_max_events_and_sequence():
    rows = list(
        iter_stream(
            {
                "mode": "stream",
                "seed": 1,
                "max_events": 2,
                "interval": {"min_ms": 1, "max_ms": 1},
                "schema": {
                    "seq": {"type": "sequence"},
                    "value": {"type": "float", "min": 0, "max": 1, "precision": 3},
                },
            },
            sleep=False,
        )
    )

    assert len(rows) == 2
    assert rows[0]["seq"] == 1
    assert isinstance(rows[0]["value"], float)


def test_load_spec_reads_json_file(tmp_path: Path):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({"schema": {"name": "name"}}))

    assert load_spec(path)["schema"]["name"] == "name"


def test_example_generates_realistic_ai_stock_price_dynamics():
    rows = generate_batch(
        {
            "mode": "batch",
            "template": "stock_price_dynamic",
            "seed": 2026,
            "count": 35,
            "start_date": "2026-04-01",
            "symbols": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"],
            "trading_days": 5,
            "daily_volatility": 0.018,
            "daily_drift": 0.001,
            "max_daily_move": 0.08,
        }
    )

    assert len(rows) == 35
    assert {row["symbol"] for row in rows} == {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"}
    assert all(row["sector_theme"] == "large-cap AI infrastructure and platforms" for row in rows)
    assert all(-8.0 <= row["daily_return_pct"] <= 8.0 for row in rows)
    assert all(row["low"] <= row["open"] <= row["high"] for row in rows)
    assert all(row["low"] <= row["close"] <= row["high"] for row in rows)
    assert all(row["volume"] > 1_000_000 for row in rows)


def test_example_streams_realistic_ai_stock_price_ticks_without_sleep():
    rows = list(
        iter_stream(
            {
                "mode": "stream",
                "template": "stock_price_dynamic",
                "seed": 7,
                "max_events": 7,
                "interval": {"min_ms": 250, "max_ms": 750},
                "max_daily_move": 0.06,
            },
            sleep=False,
        )
    )

    assert len(rows) == 7
    assert [row["symbol"] for row in rows] == ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
    assert all(abs(row["daily_return_pct"]) <= 6.0 for row in rows)


def test_generate_one_matches_stream_index_for_stock_template():
    spec = {
        "mode": "stream",
        "template": "stock_price_dynamic",
        "seed": 7,
        "symbols": ["AAPL", "MSFT", "NVDA"],
        "max_daily_move": 0.06,
    }

    rows = list(iter_stream({**spec, "max_events": 5}, sleep=False))

    assert generate_one(spec, 4) == rows[4]


def test_example_generates_real_estate_trades_for_zip_03755():
    rows = generate_batch(
        {
            "mode": "batch",
            "template": "real_estate_trade",
            "seed": 37755,
            "count": 12,
            "zip_code": "03755",
            "city": "Hanover",
            "state": "NH",
            "transaction_types": ["buy", "sell", "rent"],
            "start_date": "2026-04-01",
        }
    )

    assert len(rows) == 12
    assert all(row["zip_code"] == "03755" for row in rows)
    assert all(row["property_type"] == "single_family_house" for row in rows)
    assert {row["transaction_type"] for row in rows}.issubset({"buy", "sell", "rent"})
    assert all(2 <= row["bedrooms"] <= 5 for row in rows)
    assert all(1.5 <= row["bathrooms"] <= 3.5 for row in rows)
    assert all(1_250 <= row["size_sqft"] <= 4_200 for row in rows)
    assert all(len(row["features"]) == 4 for row in rows)
    assert all("single-family home" in row["description"] for row in rows)
    assert all(row["list_price"] >= 2_200 for row in rows)
