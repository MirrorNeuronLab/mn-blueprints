# Financial Market Realtime Advisor Daemon

This blueprint merges the market simulation pattern from `finance_market_observe` with Slack posting support inspired by `finance_slack_monitor_deamon`.

It runs as a live daemon until manually cancelled. The exchange publishes continuous market ticks, trader agents place simulated orders, and a fake-data stream agent uses `mn-skills/generate_fake_data_skill` to publish synthetic Magnificent 7 stock price ticks. `stock_signal_analyzer` applies deterministic technical analysis, then `market_advisor` emits realtime advice events and can optionally send them to Slack.

## Run

```bash
mn run mn-blueprints/financial_market_realtime_advisor_deamon
```

## Slack Option

Slack posting is off by default. The advisor delegates Slack OAuth bot messaging to `mn-skills/slack_communicate_skill`, which is vendored into generated bundles as `payloads/beam_modules/00_slack_communicate_skill.ex`.

To send advisor messages to Slack, provide a bot token and enable Slack delivery:

```bash
FINANCIAL_MARKET_ADVISOR_SLACK_ENABLED=true \
SLACK_BOT_TOKEN="<your slack bot oauth token>" \
SLACK_DEFAULT_CHANNEL="#claw" \
mn run mn-blueprints/financial_market_realtime_advisor_deamon
```

You can also generate a manifest with Slack enabled in node config:

```bash
python3 generate_bundle.py --slack-enabled --slack-channel "#claw"
```

Slack uses an `important_only` policy by default. The advisor emits analysis events continuously, but sends Slack only when a symbol has an actionable high-confidence signal, an actionable action change, or a periodic digest is due. Every Slack message includes this claim: `this is based on mockup market data, not real market data or financial advice.`

Policy knobs:

```bash
python3 generate_bundle.py \
  --slack-enabled \
  --slack-min-confidence 0.65 \
  --slack-cooldown-ticks-per-symbol 20 \
  --slack-digest-every-ticks 100
```

## Fake Stock Stream

`fake_stock_stream` is a Python executor agent that vendors `mn-skills/generate_fake_data_skill` into its payload and keeps itself alive with streaming control messages. It emits `stock_price_tick` records for `AAPL`, `MSFT`, `NVDA`, `GOOGL`, `AMZN`, `META`, and `TSLA` by default.

Useful generation knobs:

```bash
python3 generate_bundle.py \
  --symbols AAPL,MSFT,NVDA \
  --stock-interval-min-ms 500 \
  --stock-interval-max-ms 1500 \
  --daily-volatility 0.018 \
  --max-daily-move 0.06
```

`stock_signal_analyzer` consumes each `stock_price_tick` and computes common non-LLM indicators:

- SMA-5 and SMA-20 trend stack
- EMA-12, EMA-26, and MACD
- RSI-14
- 5-tick momentum
- 10-tick volatility

It emits `market_signal` messages with `buy_watch`, `sell_or_reduce_watch`, or `hold_watch`, plus confidence, indicators, and rationale.

## What To Watch

Runtime events include:

- `fake_stock_tick_generated`: fake-data skill sourced stock tick.
- `stock_signal_generated`: technical analysis result for a stock tick.
- `market_advice_generated`: advisor signal for either exchange ticks or stock analysis signals, including Slack enabled state.
- `market_data`: exchange tick data delivered to traders and the advisor.
- `place_order`: simulated trader order flow back to the exchange.

## Quick Test

```bash
MN_BLUEPRINT_QUICK_TEST=1 python3 generate_bundle.py --quick-test
```

The quick bundle uses fewer traders and a faster tick delay for local validation.
