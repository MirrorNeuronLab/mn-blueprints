#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
from pathlib import Path


def load_json_env(name: str) -> dict:
    path = os.environ.get(name)
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def ema(previous: float | None, value: float, window: int) -> float:
    alpha = 2.0 / (window + 1.0)
    return value if previous is None else value * alpha + previous * (1.0 - alpha)


def rsi(values: list[float], window: int = 14) -> float | None:
    if len(values) <= window:
        return None

    gains = []
    losses = []
    recent = values[-(window + 1) :]
    for before, after in zip(recent, recent[1:]):
        delta = after - before
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    avg_gain = sum(gains) / window
    avg_loss = sum(losses) / window
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def volatility_pct(values: list[float], window: int = 10) -> float | None:
    if len(values) <= 2:
        return None
    recent = values[-window:]
    returns = [
        (after / before - 1.0) * 100.0
        for before, after in zip(recent, recent[1:])
        if before
    ]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    return math.sqrt(variance)


def decide_signal(price: float, indicators: dict, bid_depth: float = 0.0, ask_depth: float = 0.0) -> tuple[str, float, list[str]]:
    score = 0.0
    reasons = []

    sma_short = indicators.get("sma_5")
    sma_long = indicators.get("sma_20")
    macd = indicators.get("macd")
    rsi_value = indicators.get("rsi_14")
    momentum = indicators.get("momentum_5_pct")

    if sma_short is not None and sma_long is not None:
        if sma_short > sma_long and price > sma_short:
            score += 1.5
            reasons.append("price above rising short/long moving-average stack")
        elif sma_short < sma_long and price < sma_short:
            score -= 1.5
            reasons.append("price below falling short/long moving-average stack")

    if macd is not None:
        if macd > 0:
            score += 1.0
            reasons.append("MACD trend is positive")
        elif macd < 0:
            score -= 1.0
            reasons.append("MACD trend is negative")

    if rsi_value is not None:
        if rsi_value < 35:
            score += 1.0
            reasons.append("RSI indicates oversold conditions")
        elif rsi_value > 70:
            score -= 1.0
            reasons.append("RSI indicates overbought conditions")

    if momentum is not None:
        if momentum >= 2.0:
            score += 0.75
            reasons.append("5-tick momentum is constructive")
        elif momentum <= -2.0:
            score -= 0.75
            reasons.append("5-tick momentum is weakening")

    if bid_depth and ask_depth:
        if bid_depth > ask_depth * 1.4:
            score += 0.5
            reasons.append("order-book depth leans bid")
        elif ask_depth > bid_depth * 1.4:
            score -= 0.5
            reasons.append("order-book depth leans ask")

    if score >= 1.5:
        action = "buy_watch"
    elif score <= -1.5:
        action = "sell_or_reduce_watch"
    else:
        action = "hold_watch"

    confidence = min(0.95, 0.45 + abs(score) * 0.12)
    if not reasons:
        reasons.append("not enough confirmation across trend, momentum, and RSI")

    return action, round(confidence, 3), reasons


def analyze_tick(tick: dict, symbol_state: dict) -> tuple[dict, dict]:
    symbol = tick["symbol"]
    price = float(tick["close"])
    prices = [float(item) for item in symbol_state.get("prices", [])]
    prices.append(price)
    prices = prices[-80:]

    ema_12 = ema(symbol_state.get("ema_12"), price, 12)
    ema_26 = ema(symbol_state.get("ema_26"), price, 26)
    macd = ema_12 - ema_26
    sma_5 = sma(prices, 5)
    sma_20 = sma(prices, 20)
    rsi_14 = rsi(prices, 14)
    vol_10 = volatility_pct(prices, 10)
    momentum_5 = ((price / prices[-6] - 1.0) * 100.0) if len(prices) >= 6 and prices[-6] else None

    indicators = {
        "sma_5": round(sma_5, 4) if sma_5 is not None else None,
        "sma_20": round(sma_20, 4) if sma_20 is not None else None,
        "ema_12": round(ema_12, 4),
        "ema_26": round(ema_26, 4),
        "macd": round(macd, 4),
        "rsi_14": round(rsi_14, 3) if rsi_14 is not None else None,
        "volatility_10_pct": round(vol_10, 3) if vol_10 is not None else None,
        "momentum_5_pct": round(momentum_5, 3) if momentum_5 is not None else None,
    }

    action, confidence, reasons = decide_signal(
        price,
        indicators,
        float(tick.get("bid_depth", 0) or 0),
        float(tick.get("ask_depth", 0) or 0),
    )

    signal = {
        "stream_id": tick.get("stream_id"),
        "event_index": tick.get("event_index"),
        "trade_date": tick.get("trade_date"),
        "symbol": symbol,
        "company": tick.get("company", symbol),
        "price": round(price, 4),
        "daily_return_pct": tick.get("daily_return_pct"),
        "volume": tick.get("volume"),
        "action": action,
        "confidence": confidence,
        "indicators": indicators,
        "rationale": reasons,
        "message": format_message(symbol, price, action, confidence, indicators, reasons),
    }

    next_symbol_state = {
        "prices": prices,
        "ema_12": ema_12,
        "ema_26": ema_26,
        "last_action": action,
    }

    return signal, next_symbol_state


def format_message(symbol: str, price: float, action: str, confidence: float, indicators: dict, reasons: list[str]) -> str:
    rsi_value = indicators.get("rsi_14")
    macd = indicators.get("macd")
    rsi_text = "warming" if rsi_value is None else f"RSI {rsi_value}"
    return (
        f"{symbol} signal: {action} at {price:.2f} "
        f"(confidence {confidence:.0%}, MACD {macd}, {rsi_text}). "
        f"Reason: {reasons[0]}."
    )


def should_emit_to_llm(signal: dict, signals_seen: int) -> bool:
    every = int(os.environ.get("LLM_SIGNAL_EVERY_EVENTS", "30"))
    min_confidence = float(os.environ.get("LLM_SIGNAL_MIN_CONFIDENCE", "0.72"))
    action = signal.get("action")
    confidence = float(signal.get("confidence", 0.0) or 0.0)

    if action in {"buy_watch", "sell_or_reduce_watch"} and confidence >= min_confidence:
        return True

    return every > 0 and signals_seen % every == 0


def main() -> None:
    context = load_json_env("MN_CONTEXT_FILE")
    tick = load_json_env("MN_INPUT_FILE")
    state = context.get("agent_state") or {"symbols": {}, "signals_seen": 0}

    symbol = tick.get("symbol")
    if not symbol:
        print(json.dumps({"next_state": state, "events": []}))
        return

    symbol_state = (state.get("symbols") or {}).get(symbol, {})
    signal, next_symbol_state = analyze_tick(tick, symbol_state)

    symbols = dict(state.get("symbols") or {})
    symbols[symbol] = next_symbol_state
    next_state = {
        "symbols": symbols,
        "signals_seen": int(state.get("signals_seen", 0)) + 1,
        "last_signal": signal,
    }
    signals_seen = next_state["signals_seen"]

    emit_messages = [
        {
            "to": "market_advisor",
            "type": "market_signal",
            "class": "event",
            "payload": signal,
            "headers": {
                "schema_ref": "com.mirrorneuron.finance.stock_decision_signal",
                "schema_version": "1.0.0",
            },
        }
    ]

    if should_emit_to_llm(signal, signals_seen):
        emit_messages.append(
            {
                "to": "llm_market_explainer",
                "type": "market_signal",
                "class": "event",
                "payload": signal,
                "headers": {
                    "schema_ref": "com.mirrorneuron.finance.stock_decision_signal",
                    "schema_version": "1.0.0",
                },
            }
        )

    result = {
        "next_state": next_state,
        "events": [{"type": "stock_signal_generated", "payload": signal}],
        "emit_messages": emit_messages,
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
