# Financial Market Realtime Advisor Daemon

This blueprint merges the market simulation pattern from `finance_market_observe` with Slack posting support inspired by `finance_slack_monitor_deamon`.

It runs as a live daemon until manually cancelled. The exchange publishes continuous market ticks, trader agents place simulated orders, and a fake-data stream agent uses `mn-skills/generate_fake_data_skill` to publish synthetic Magnificent 7 stock price ticks. `stock_signal_analyzer` applies deterministic technical analysis, then `market_advisor` emits realtime advice events and can optionally send them to Slack.

## Run

```bash
mn run mn-blueprints/financial_market_realtime_advisor_deamon
```

## Slack Delivery

Slack posting is enabled in the default generated manifest and remains optional at runtime: the advisor sends to Slack only when a bot token is present. It delegates Slack OAuth bot messaging to `mn-skills/slack_communicate_skill`, which is vendored into generated bundles as `payloads/beam_modules/00_slack_communicate_skill.ex`.

To send advisor messages to Slack, provide a bot token:

```bash
SLACK_BOT_TOKEN="<your slack bot oauth token>" \
SLACK_DEFAULT_CHANNEL="#claw" \
mn run mn-blueprints/financial_market_realtime_advisor_deamon
```

You can explicitly generate with Slack enabled or disabled:

```bash
python3 generate_bundle.py --slack-enabled --slack-channel "#claw"
python3 generate_bundle.py --slack-disabled
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

## LLM Explanation

`llm_market_explainer` watches both sides of the blueprint:

- exchange `market_data`, including recent matched trades and trader IDs
- `market_signal` records from the stock technical analyzer

It keeps lightweight trader performance stats such as buy/sell count, filled volume, and notional activity, then periodically asks an LLM to produce a concise human explanation. The output is sent to `market_advisor` as `llm_market_explanation`, which can post it to Slack when Slack is enabled.

The explainer uses `mn-skills/litellm_communicate_skill` and only the LiteLLM-style environment variables:

```bash
LITELLM_MODEL="ollama/gemma4:latest"
LITELLM_API_BASE="http://192.168.4.173:11434"
LITELLM_API_KEY=""
```

Generator knobs:

```bash
python3 generate_bundle.py \
  --litellm-model "ollama/gemma4:latest" \
  --litellm-api-base "http://192.168.4.173:11434" \
  --llm-explanation-interval-seconds 300
```

By default this blueprint asks the LLM for an initial advisory as soon as market context is available, then asks for a fresh advisory every 5 minutes and routes the result through `market_advisor` to Slack. LLM calls use timeout and retry settings, and explanation requests are queued in the explainer agent state when the provider is slow or unavailable. The daemon keeps ingesting market/trader/signal events while pending explanations retry later, so Slack receives delayed LLM explanations instead of losing them or replacing them with non-LLM text.

Backpressure knobs:

```bash
python3 generate_bundle.py \
  --litellm-timeout-seconds 20 \
  --litellm-num-retries 2 \
  --litellm-retry-backoff-seconds 1.0 \
  --llm-explanation-max-pending 25 \
  --llm-explanation-retry-delay-seconds 5
```

Every Slack explanation includes the mock-data claim. LLM advisories are formatted for Slack as a few short chunks: takeaway, current read, and watch/risk. Routine market ticks stay in MirrorNeuron events; Slack is reserved for important market moves, actionable stock-signal alerts, digests, and LLM advisories.

## What To Watch

Runtime events include:

- `fake_stock_tick_generated`: fake-data skill sourced stock tick.
- `stock_signal_generated`: technical analysis result for a stock tick.
- `llm_market_explanation_generated`: LLM-generated explanation across exchange activity, trader activity, and stock signals.
- `llm_market_explanation_deferred`: LLM explanation request retained for retry because the provider was slow, timed out, or unavailable.
- `market_advice_generated`: advisor signal for either exchange ticks or stock analysis signals, including Slack enabled state.
- `market_data`: exchange tick data delivered to traders and the advisor.
- `place_order`: simulated trader order flow back to the exchange.

## Quick Test

```bash
MN_BLUEPRINT_QUICK_TEST=1 python3 generate_bundle.py --quick-test
```

The quick bundle uses fewer traders and a faster tick delay for local validation.
