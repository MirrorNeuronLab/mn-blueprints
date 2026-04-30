#!/usr/bin/env python3
import argparse
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "mn-skills" / "blueprint_support_skill" / "src"),
)
from mn_blueprint_support import apply_quick_test, log_status, progress, write_manifest


def build_manifest(args: argparse.Namespace) -> dict:
    shared_config = {
        "duration_seconds": args.duration_seconds,
        "tick_seconds": args.tick_seconds,
        "initial_price": args.initial_price,
        "tick_delay_ms": args.tick_delay_ms,
        "live_mode": True,
    }

    nodes = [
        {
            "node_id": "ingress",
            "agent_type": "router",
            "type": "map",
            "role": "root_coordinator",
            "config": {"emit_type": "simulation_start"},
        },
        {
            "node_id": "exchange",
            "agent_type": "module",
            "type": "reduce",
            "role": "exchange",
            "config": {
                **shared_config,
                "module": "MirrorNeuron.Examples.FinancialMarket.ExchangeAgent",
                "module_source": "beam_modules/exchange_agent.ex",
                "llm_market_data_every_ticks": args.llm_market_data_every_ticks,
            },
        },
        {
            "node_id": "fake_stock_stream",
            "agent_type": "executor",
            "type": "stream",
            "role": "fake_data_stream_agent",
            "config": {
                "runner_module": "MirrorNeuron.Runner.HostLocal",
                "upload_path": "fake_stock_stream",
                "upload_as": "fake_stock_stream",
                "workdir": "/sandbox/job/fake_stock_stream",
                "command": ["python3", "scripts/generate_stock_stream.py"],
                "output_message_type": None,
                "seed": args.seed,
                "start_date": args.start_date,
                "symbols": args.symbols.split(","),
                "trading_days": args.trading_days,
                "daily_volatility": args.daily_volatility,
                "daily_drift": args.daily_drift,
                "max_daily_move": args.max_daily_move,
                "interval_min_ms": args.stock_interval_min_ms,
                "interval_max_ms": args.stock_interval_max_ms,
                "target_node": "stock_signal_analyzer",
                "environment": {
                    "STOCK_STREAM_SEED": str(args.seed),
                    "STOCK_STREAM_START_DATE": args.start_date,
                    "STOCK_STREAM_SYMBOLS": args.symbols,
                    "STOCK_STREAM_TRADING_DAYS": str(args.trading_days),
                    "STOCK_STREAM_DAILY_VOLATILITY": str(args.daily_volatility),
                    "STOCK_STREAM_DAILY_DRIFT": str(args.daily_drift),
                    "STOCK_STREAM_MAX_DAILY_MOVE": str(args.max_daily_move),
                    "STOCK_STREAM_INTERVAL_MIN_MS": str(args.stock_interval_min_ms),
                    "STOCK_STREAM_INTERVAL_MAX_MS": str(args.stock_interval_max_ms),
                    "STOCK_STREAM_TARGET_NODE": "stock_signal_analyzer",
                },
            },
        },
        {
            "node_id": "stock_signal_analyzer",
            "agent_type": "executor",
            "type": "stream",
            "role": "technical_signal_analyzer",
            "config": {
                "runner_module": "MirrorNeuron.Runner.HostLocal",
                "upload_path": "stock_signal_analyzer",
                "upload_as": "stock_signal_analyzer",
                "workdir": "/sandbox/job/stock_signal_analyzer",
                "command": ["python3", "scripts/analyze_stock_signal.py"],
                "output_message_type": None,
                "environment": {
                    "LLM_SIGNAL_EVERY_EVENTS": str(args.llm_signal_every_events),
                    "LLM_SIGNAL_MIN_CONFIDENCE": str(args.llm_signal_min_confidence),
                },
            },
        },
        {
            "node_id": "llm_market_explainer",
            "agent_type": "executor",
            "type": "stream",
            "role": "market_explanation_agent",
            "config": {
                "runner_module": "MirrorNeuron.Runner.HostLocal",
                "upload_path": "llm_market_explainer",
                "upload_as": "llm_market_explainer",
                "workdir": "/sandbox/job/llm_market_explainer",
                "command": ["python3", "scripts/explain_market.py"],
                "output_message_type": None,
                "environment": {
                    "LITELLM_MODEL": args.litellm_model,
                    "LITELLM_API_BASE": args.litellm_api_base,
                    "LITELLM_API_KEY": args.litellm_api_key,
                    "LITELLM_TIMEOUT_SECONDS": str(args.litellm_timeout_seconds),
                    "LITELLM_MAX_TOKENS": str(args.litellm_max_tokens),
                    "LITELLM_NUM_RETRIES": str(args.litellm_num_retries),
                    "LITELLM_RETRY_BACKOFF_SECONDS": str(args.litellm_retry_backoff_seconds),
                    "LLM_EXPLANATION_INTERVAL_EVENTS": str(args.llm_explanation_interval_events),
                    "LLM_EXPLANATION_INTERVAL_SECONDS": str(args.llm_explanation_interval_seconds),
                    "LLM_EXPLANATION_MAX_PENDING": str(args.llm_explanation_max_pending),
                    "LLM_EXPLANATION_RETRY_DELAY_SECONDS": str(args.llm_explanation_retry_delay_seconds),
                },
            },
        },
        {
            "node_id": "market_advisor",
            "agent_type": "module",
            "type": "map",
            "role": "advisor",
            "config": {
                "module": "MirrorNeuron.Examples.FinancialMarket.MarketAdvisorAgent",
                "module_source": "beam_modules/market_advisor_agent.ex",
                "advice_interval_ticks": args.advice_interval_ticks,
                "important_move_pct": args.important_move_pct,
                "slack_enabled": args.slack_enabled,
                "slack_channel": args.slack_channel,
                "slack_policy": {
                    "mode": args.slack_policy_mode,
                    "min_confidence": args.slack_min_confidence,
                    "cooldown_ticks_per_symbol": args.slack_cooldown_ticks_per_symbol,
                    "alert_on_action_change": True,
                    "digest_every_ticks": args.slack_digest_every_ticks,
                },
            },
        },
    ]

    edges = [
        {
            "edge_id": "ingress_to_exchange",
            "from_node": "ingress",
            "to_node": "exchange",
            "message_type": "simulation_start",
        },
        {
            "edge_id": "ingress_to_fake_stock_stream",
            "from_node": "ingress",
            "to_node": "fake_stock_stream",
            "message_type": "simulation_start",
        },
        {
            "edge_id": "fake_stock_stream_self_tick",
            "from_node": "fake_stock_stream",
            "to_node": "fake_stock_stream",
            "message_type": "generate_next_stock_tick",
        },
        {
            "edge_id": "fake_stock_stream_to_signal_analyzer",
            "from_node": "fake_stock_stream",
            "to_node": "stock_signal_analyzer",
            "message_type": "stock_price_tick",
        },
        {
            "edge_id": "signal_analyzer_to_advisor",
            "from_node": "stock_signal_analyzer",
            "to_node": "market_advisor",
            "message_type": "market_signal",
        },
        {
            "edge_id": "llm_explainer_to_advisor",
            "from_node": "llm_market_explainer",
            "to_node": "market_advisor",
            "message_type": "llm_market_explanation",
        },
        {
            "edge_id": "llm_explainer_self_retry",
            "from_node": "llm_market_explainer",
            "to_node": "llm_market_explainer",
            "message_type": "retry_llm_explanation",
        },
        {
            "edge_id": "exchange_to_advisor",
            "from_node": "exchange",
            "to_node": "market_advisor",
            "message_type": "market_data",
        },
    ]

    rand = random.Random(args.seed)
    strategies = ["momentum", "mean_reversion", "noise", "market_maker"]
    weights = [0.15, 0.15, 0.6, 0.1]

    for index in range(args.traders):
        agent_id = f"trader_{index:03d}"
        strategy = rand.choices(strategies, weights=weights)[0]

        nodes.append(
            {
                "node_id": agent_id,
                "agent_type": "module",
                "type": "reduce",
                "role": strategy,
                "config": {
                    **shared_config,
                    "strategy": strategy,
                    "llm_order_sample_rate": args.llm_order_sample_rate,
                    "module": "MirrorNeuron.Examples.FinancialMarket.TraderAgent",
                    "module_source": "beam_modules/trader_agent.ex",
                },
            }
        )

        edges.extend(
            [
                {
                    "edge_id": f"exchange_to_{agent_id}_data",
                    "from_node": "exchange",
                    "to_node": agent_id,
                    "message_type": "market_data",
                },
                {
                    "edge_id": f"{agent_id}_to_exchange",
                    "from_node": agent_id,
                    "to_node": "exchange",
                    "message_type": "place_order",
                },
            ]
        )

    return {
        "manifest_version": "1.0",
        "graph_id": "financial_market_realtime_advisor_deamon_v1",
        "job_name": "financial_market_realtime_advisor_deamon",
        "requiredContextEngine": False,
        "daemon": True,
        "entrypoints": ["ingress"],
        "initial_inputs": {
            "ingress": [
                {
                    "scenario": "financial_market_realtime_advisor",
                    "tick_seconds": args.tick_seconds,
                    "seed": args.seed,
                    "slack_optional": True,
                }
            ]
        },
        "nodes": nodes,
        "edges": edges,
        "policies": {"recovery_mode": "cluster_recover", "stream_mode": "live"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the realtime financial market advisor daemon bundle."
    )
    parser.add_argument("--traders", type=int, default=25)
    parser.add_argument("--duration-seconds", type=int, default=86_400)
    parser.add_argument("--tick-seconds", type=int, default=1)
    parser.add_argument("--initial-price", type=float, default=100.0)
    parser.add_argument("--tick-delay-ms", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=729905862)
    parser.add_argument("--start-date", default="2026-04-30")
    parser.add_argument("--symbols", default="AAPL,MSFT,NVDA,GOOGL,AMZN,META,TSLA")
    parser.add_argument("--trading-days", type=int, default=252)
    parser.add_argument("--daily-volatility", type=float, default=0.018)
    parser.add_argument("--daily-drift", type=float, default=0.001)
    parser.add_argument("--max-daily-move", type=float, default=0.06)
    parser.add_argument("--stock-interval-min-ms", type=int, default=1000)
    parser.add_argument("--stock-interval-max-ms", type=int, default=1000)
    parser.add_argument("--litellm-model", default="ollama/gemma4:latest")
    parser.add_argument("--litellm-api-base", default="http://192.168.4.173:11434")
    parser.add_argument("--litellm-api-key", default="")
    parser.add_argument("--litellm-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--litellm-max-tokens", type=int, default=800)
    parser.add_argument("--litellm-num-retries", type=int, default=2)
    parser.add_argument("--litellm-retry-backoff-seconds", type=float, default=1.0)
    parser.add_argument("--llm-market-data-every-ticks", type=int, default=30)
    parser.add_argument("--llm-order-sample-rate", type=int, default=20)
    parser.add_argument("--llm-signal-every-events", type=int, default=30)
    parser.add_argument("--llm-signal-min-confidence", type=float, default=0.72)
    parser.add_argument("--llm-explanation-interval-events", type=int, default=0)
    parser.add_argument("--llm-explanation-interval-seconds", type=float, default=300.0)
    parser.add_argument("--llm-explanation-max-pending", type=int, default=25)
    parser.add_argument("--llm-explanation-retry-delay-seconds", type=float, default=5.0)
    parser.add_argument("--advice-interval-ticks", type=int, default=5)
    parser.add_argument("--important-move-pct", type=float, default=1.5)
    parser.add_argument("--slack-enabled", action="store_true", default=True)
    parser.add_argument("--slack-disabled", action="store_false", dest="slack_enabled")
    parser.add_argument("--slack-channel", default="#claw")
    parser.add_argument("--slack-policy-mode", default="important_only")
    parser.add_argument("--slack-min-confidence", type=float, default=0.65)
    parser.add_argument("--slack-cooldown-ticks-per-symbol", type=int, default=20)
    parser.add_argument("--slack-digest-every-ticks", type=int, default=100)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Generate a small deterministic daemon bundle for fast validation.",
    )
    args = parser.parse_args()

    quick_test = apply_quick_test(
        args,
        {
            "traders": 5,
            "tick_delay_ms": 100,
            "stock_interval_min_ms": 50,
            "stock_interval_max_ms": 50,
            "llm_explanation_interval_events": 12,
            "llm_explanation_interval_seconds": 0,
            "llm_explanation_retry_delay_seconds": 0.05,
            "llm_market_data_every_ticks": 12,
            "llm_order_sample_rate": 10,
            "llm_signal_every_events": 12,
            "litellm_timeout_seconds": 1.0,
            "litellm_num_retries": 0,
            "advice_interval_ticks": 2,
            "slack_cooldown_ticks_per_symbol": 5,
            "slack_digest_every_ticks": 20,
            "seed": 42,
        },
    )

    args.traders = max(args.traders, 1)
    args.tick_delay_ms = max(args.tick_delay_ms, 0)
    args.stock_interval_min_ms = max(args.stock_interval_min_ms, 0)
    args.stock_interval_max_ms = max(args.stock_interval_max_ms, args.stock_interval_min_ms)
    args.advice_interval_ticks = max(args.advice_interval_ticks, 1)
    args.slack_min_confidence = min(max(args.slack_min_confidence, 0.0), 1.0)
    args.slack_cooldown_ticks_per_symbol = max(args.slack_cooldown_ticks_per_symbol, 0)
    args.slack_digest_every_ticks = max(args.slack_digest_every_ticks, 0)
    args.litellm_timeout_seconds = max(args.litellm_timeout_seconds, 0.1)
    args.litellm_max_tokens = max(args.litellm_max_tokens, 1)
    args.litellm_num_retries = max(args.litellm_num_retries, 0)
    args.litellm_retry_backoff_seconds = max(args.litellm_retry_backoff_seconds, 0.0)
    args.llm_market_data_every_ticks = max(args.llm_market_data_every_ticks, 0)
    args.llm_order_sample_rate = max(args.llm_order_sample_rate, 0)
    args.llm_signal_every_events = max(args.llm_signal_every_events, 0)
    args.llm_signal_min_confidence = min(max(args.llm_signal_min_confidence, 0.0), 1.0)
    args.llm_explanation_interval_events = max(args.llm_explanation_interval_events, 0)
    args.llm_explanation_interval_seconds = max(args.llm_explanation_interval_seconds, 0.0)
    args.llm_explanation_max_pending = max(args.llm_explanation_max_pending, 1)
    args.llm_explanation_retry_delay_seconds = max(args.llm_explanation_retry_delay_seconds, 0.0)
    args.symbols = ",".join(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip())

    log_status(
        "financial_market_realtime_advisor_deamon",
        "generating realtime market advisor daemon bundle",
        phase="generate",
        details={
            "quick_test": quick_test,
            "traders": args.traders,
            "slack_enabled": args.slack_enabled,
            "stock_symbols": args.symbols.split(","),
        },
    )

    root = Path(__file__).resolve().parent
    bundle_dir = args.output_dir
    bundle_dir.mkdir(parents=True, exist_ok=True)

    payloads_dir = bundle_dir / "payloads"
    payloads_dir.mkdir(parents=True, exist_ok=True)
    beam_modules_dest = payloads_dir / "beam_modules"
    beam_modules_dest.mkdir(parents=True, exist_ok=True)

    if bundle_dir.resolve() != root:
        shutil.copytree(root / "payloads" / "beam_modules", beam_modules_dest, dirs_exist_ok=True)
        for payload_name in ["fake_stock_stream", "stock_signal_analyzer", "llm_market_explainer"]:
            shutil.copytree(
                root / "payloads" / payload_name,
                payloads_dir / payload_name,
                dirs_exist_ok=True,
            )

    slack_skill_src = (
        root.parents[1]
        / "mn-skills"
        / "slack_communicate_skill"
        / "src"
        / "mn_slack_communicate_skill"
        / "slack_communicate.ex"
    )
    shutil.copy2(slack_skill_src, beam_modules_dest / "00_slack_communicate_skill.ex")

    fake_data_skill_src = root.parents[1] / "mn-skills" / "generate_fake_data_skill"
    fake_data_skill_dest = payloads_dir / "fake_stock_stream" / "_shared_skills" / "generate_fake_data_skill"
    if fake_data_skill_dest.exists():
        shutil.rmtree(fake_data_skill_dest)
    shutil.copytree(
        fake_data_skill_src,
        fake_data_skill_dest,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
    )

    litellm_skill_src = root.parents[1] / "mn-skills" / "litellm_communicate_skill"
    litellm_skill_dest = payloads_dir / "llm_market_explainer" / "_shared_skills" / "litellm_communicate_skill"
    if litellm_skill_dest.exists():
        shutil.rmtree(litellm_skill_dest)
    shutil.copytree(
        litellm_skill_src,
        litellm_skill_dest,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
    )

    write_manifest(
        bundle_dir / "manifest.json",
        build_manifest(args),
        blueprint_id="financial_market_realtime_advisor_deamon",
        quick_test=quick_test,
    )

    print(progress("bundle generated", 1, 1), file=sys.stderr)
    print(bundle_dir)


if __name__ == "__main__":
    main()
