#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


WORKDIR = Path(__file__).resolve().parents[1]
SHARED_SKILL = WORKDIR / "_shared_skills" / "litellm_communicate_skill" / "src"
if SHARED_SKILL.exists():
    sys.path.insert(0, str(SHARED_SKILL))

from mn_litellm_communicate_skill import LLMError, completion_json


MOCK_CLAIM = "Claim: this is based on mockup market data, not real market data or financial advice."


def load_json_env(name: str) -> dict[str, Any]:
    path = os.environ.get(name)
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def initial_state() -> dict[str, Any]:
    return {
        "events_seen": 0,
        "market_ticks": [],
        "latest_signals": {},
        "traders": {},
        "last_explained_at": 0,
        "last_explained_wall_ts": 0.0,
        "pending_explanations": [],
        "llm_backpressure": {
            "status": "healthy",
            "failure_count": 0,
            "last_error": None,
        },
    }


def update_market(state: dict[str, Any], market_data: dict[str, Any]) -> None:
    tick = {
        "tick": market_data.get("tick"),
        "last_price": market_data.get("last_price"),
        "bid_depth": market_data.get("bid_depth", 0),
        "ask_depth": market_data.get("ask_depth", 0),
        "trades": market_data.get("trades", []),
    }
    state["market_ticks"] = (state.get("market_ticks") or [])[-39:] + [tick]

    for trade in tick["trades"] or []:
        price = float(trade.get("price", 0) or 0)
        quantity = float(trade.get("quantity", 0) or 0)
        notional = price * quantity
        buyer = trade.get("buyer")
        seller = trade.get("seller")
        if buyer:
            update_trader(state, buyer, "buy", quantity, notional)
        if seller:
            update_trader(state, seller, "sell", quantity, notional)


def update_trader(state: dict[str, Any], agent_id: str, side: str, quantity: float, notional: float) -> None:
    traders = state.setdefault("traders", {})
    trader = traders.setdefault(
        agent_id,
        {"buy_orders": 0, "sell_orders": 0, "buys": 0, "sells": 0, "volume": 0.0, "notional": 0.0},
    )
    trader["buys" if side == "buy" else "sells"] += 1
    trader["volume"] = round(float(trader["volume"]) + quantity, 4)
    trader["notional"] = round(float(trader["notional"]) + notional, 4)


def update_order(state: dict[str, Any], order: dict[str, Any]) -> None:
    agent_id = order.get("agent_id")
    if not agent_id:
        return

    side = order.get("side", "unknown")
    price = float(order.get("price", 0) or 0)
    quantity = float(order.get("quantity", 0) or 0)
    traders = state.setdefault("traders", {})
    trader = traders.setdefault(
        agent_id,
        {"buy_orders": 0, "sell_orders": 0, "buys": 0, "sells": 0, "volume": 0.0, "notional": 0.0},
    )
    trader["strategy"] = order.get("strategy", trader.get("strategy", "unknown"))
    if side == "buy":
        trader["buy_orders"] += 1
    elif side == "sell":
        trader["sell_orders"] += 1
    trader["last_order_price"] = round(price, 4)
    trader["last_order_quantity"] = quantity


def update_signal(state: dict[str, Any], signal: dict[str, Any]) -> None:
    symbol = signal.get("symbol")
    if symbol:
        state.setdefault("latest_signals", {})[symbol] = signal


def should_explain(state: dict[str, Any]) -> bool:
    interval_seconds = float(os.environ.get("LLM_EXPLANATION_INTERVAL_SECONDS", "300"))
    now = time.time()
    if interval_seconds > 0 and now - float(state.get("last_explained_wall_ts", 0.0)) >= interval_seconds:
        return True

    interval = int(os.environ.get("LLM_EXPLANATION_INTERVAL_EVENTS", "25"))
    if interval > 0 and state["events_seen"] - state.get("last_explained_at", 0) >= interval:
        return True

    latest_signal = state.get("latest_signal") or {}
    confidence = float(latest_signal.get("confidence", 0) or 0)
    return latest_signal.get("action") in {"buy_watch", "sell_or_reduce_watch"} and confidence >= 0.72


def build_context(state: dict[str, Any]) -> dict[str, Any]:
    ticks = state.get("market_ticks") or []
    prices = [float(item.get("last_price", 0) or 0) for item in ticks]
    first_price = prices[0] if prices else 0.0
    last_price = prices[-1] if prices else 0.0
    move_pct = ((last_price / first_price - 1.0) * 100.0) if first_price else 0.0

    traders = state.get("traders") or {}
    top_traders = sorted(
        [
            {"agent_id": agent_id, **stats}
            for agent_id, stats in traders.items()
        ],
        key=lambda item: (
            float(item.get("notional", 0)),
            int(item.get("buy_orders", 0)) + int(item.get("sell_orders", 0)),
        ),
        reverse=True,
    )[:5]

    latest_signals = list((state.get("latest_signals") or {}).values())
    latest_signals = sorted(
        latest_signals,
        key=lambda item: float(item.get("confidence", 0) or 0),
        reverse=True,
    )[:7]

    return {
        "market": {
            "ticks_seen": len(ticks),
            "first_price": round(first_price, 4),
            "last_price": round(last_price, 4),
            "move_pct": round(move_pct, 3),
            "latest_bid_depth": ticks[-1].get("bid_depth", 0) if ticks else 0,
            "latest_ask_depth": ticks[-1].get("ask_depth", 0) if ticks else 0,
            "recent_trade_count": sum(len(item.get("trades") or []) for item in ticks[-10:]),
        },
        "top_traders": top_traders,
        "latest_stock_signals": latest_signals,
    }


def fallback_explanation(context: dict[str, Any]) -> dict[str, Any]:
    market = context["market"]
    signals = context["latest_stock_signals"]
    top_signal = signals[0] if signals else {}
    trader = context["top_traders"][0] if context["top_traders"] else {}
    symbol = top_signal.get("symbol", "the stock stream")
    action = top_signal.get("action", "hold_watch")
    trader_text = trader.get("agent_id", "no dominant trader yet")

    return {
        "headline": f"{symbol} is the cleanest current setup while exchange price moved {market['move_pct']}%.",
        "summary": (
            f"Current strongest stock signal is {symbol} {action}; "
            f"the busiest simulated trader is {trader_text}."
        ),
        "watch_next": "Watch whether high-confidence stock signals align with stronger exchange bid/ask depth.",
        "risk_note": "Signals are synthetic and should be treated as workflow validation, not trading advice.",
    }


def call_explainer(context: dict[str, Any]) -> dict[str, Any]:
    system_prompt = (
        "You explain synthetic market-agent simulations for humans. "
        "Be concise and practical. Return JSON with headline, summary, watch_next, risk_note. "
        "Never claim this is real market data."
    )
    user_prompt = (
        "Explain what matters in this MirrorNeuron financial market daemon state. "
        "Use both exchange/trader activity and stock technical signals.\n"
        f"{json.dumps(context, sort_keys=True)}"
    )
    result = completion_json(system_prompt, user_prompt)
    if not result:
        raise LLMError("LLM returned an empty explanation")
    return result


def enqueue_explanation(state: dict[str, Any], reason: str) -> None:
    queue = state.setdefault("pending_explanations", [])
    max_pending = int(os.environ.get("LLM_EXPLANATION_MAX_PENDING", "25"))
    context = build_context(state)
    request = {
        "request_id": f"explain-{state['events_seen']}",
        "reason": reason,
        "created_at_event": state["events_seen"],
        "attempts": 0,
        "context": context,
    }

    if len(queue) >= max_pending:
        state["llm_backpressure"] = {
            "status": "saturated",
            "failure_count": state.get("llm_backpressure", {}).get("failure_count", 0),
            "last_error": f"pending queue full at {max_pending}",
        }
        return

    queue.append(request)
    state["last_explained_at"] = state["events_seen"]
    state["last_explained_wall_ts"] = time.time()


def process_pending_explanation(state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queue = state.setdefault("pending_explanations", [])
    if not queue:
        return [], []

    backpressure = state.setdefault(
        "llm_backpressure",
        {"status": "healthy", "failure_count": 0, "last_error": None},
    )
    retry_delay = float(os.environ.get("LLM_EXPLANATION_RETRY_DELAY_SECONDS", "5"))
    if backpressure.get("status") == "retry_later" and retry_delay > 0:
        time.sleep(retry_delay)

    request = queue[0]
    request["attempts"] = int(request.get("attempts", 0)) + 1

    try:
        explanation = call_explainer(request["context"])
    except Exception as exc:
        backpressure["status"] = "retry_later"
        backpressure["failure_count"] = int(backpressure.get("failure_count", 0)) + 1
        backpressure["last_error"] = str(exc)[:500]
        return (
            [
                {
                    "type": "llm_market_explanation_deferred",
                    "payload": {
                        "request_id": request["request_id"],
                        "attempts": request["attempts"],
                        "pending_count": len(queue),
                        "reason": "llm_unavailable_or_slow",
                        "error": backpressure["last_error"],
                    },
                }
            ],
            [retry_message()],
        )

    queue.pop(0)
    backpressure["status"] = "healthy" if not queue else "draining"
    backpressure["last_error"] = None
    payload_out = explanation_payload(explanation, request["context"], request)
    events = [{"type": "llm_market_explanation_generated", "payload": payload_out}]
    emits = [
        {
            "to": "market_advisor",
            "type": "llm_market_explanation",
            "class": "event",
            "payload": payload_out,
            "headers": {
                "schema_ref": "com.mirrorneuron.finance.llm_market_explanation",
                "schema_version": "1.0.0",
            },
        }
    ]
    if queue:
        emits.append(retry_message())
    return events, emits


def retry_message() -> dict[str, Any]:
    return {
        "to": os.environ.get("MIRROR_NEURON_AGENT_ID", "llm_market_explainer"),
        "type": "retry_llm_explanation",
        "class": "control",
        "payload": {"reason": "pending_llm_explanation"},
    }


def explanation_payload(explanation: dict[str, Any], context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    message_text = format_message(explanation, context)
    return {
        "message": message_text,
        "headline": explanation.get("headline"),
        "summary": explanation.get("summary"),
        "watch_next": explanation.get("watch_next"),
        "risk_note": explanation.get("risk_note"),
        "context": context,
        "request_id": request.get("request_id"),
        "created_at_event": request.get("created_at_event"),
        "completed_after_attempts": request.get("attempts"),
        "mock_data_claim": MOCK_CLAIM,
    }


def format_message(explanation: dict[str, Any], context: dict[str, Any]) -> str:
    market = context["market"]
    return (
        f"{explanation.get('headline', 'Market explanation update')}\n"
        f"Summary: {explanation.get('summary', '')}\n"
        f"Market: price {market['last_price']}, move {market['move_pct']}%, recent trades {market['recent_trade_count']}.\n"
        f"Watch next: {explanation.get('watch_next', '')}\n"
        f"{MOCK_CLAIM}"
    )


def main() -> None:
    message = load_json_env("MIRROR_NEURON_MESSAGE_FILE")
    payload = load_json_env("MIRROR_NEURON_INPUT_FILE")
    context = load_json_env("MIRROR_NEURON_CONTEXT_FILE")
    state = context.get("agent_state") or initial_state()
    state["events_seen"] = int(state.get("events_seen", 0)) + 1

    message_type = message.get("type") or message.get("message_type")
    if message_type is None and "last_price" in payload:
        message_type = "market_data"
    if message_type is None and "action" in payload and "symbol" in payload:
        message_type = "market_signal"
    if message_type is None and "agent_id" in payload and "side" in payload:
        message_type = "trader_order"
    if message_type is None and payload.get("reason") == "pending_llm_explanation":
        message_type = "retry_llm_explanation"
    if message_type == "market_data":
        update_market(state, payload)
    elif message_type == "market_signal":
        state["latest_signal"] = payload
        update_signal(state, payload)
    elif message_type == "trader_order":
        update_order(state, payload)

    events = []
    emit_messages = []

    if should_explain(state):
        enqueue_explanation(state, "scheduled_or_actionable_signal")

    pending_events, pending_emits = process_pending_explanation(state)
    events.extend(pending_events)
    emit_messages.extend(pending_emits)

    print(json.dumps({"next_state": state, "events": events, "emit_messages": emit_messages}))


if __name__ == "__main__":
    main()
