defmodule MirrorNeuron.Examples.FinancialMarket.MarketAdvisorAgent do
  use MirrorNeuron.AgentTemplate
  require Logger

  alias MirrorNeuron.Skills.SlackCommunicateSkill

  @impl true
  def init(node) do
    {:ok,
     %{
       config: node.config || %{},
       last_price: nil,
       last_sent_tick: 0,
       advice_count: 0,
       signal_count: 0,
       slack_symbols: %{},
       latest_signals: %{}
     }}
  end

  @impl true
  def handle_message(message, state, _context) do
    case type(message) do
      "market_data" ->
        market_data = payload(message) || %{}
        tick = Map.get(market_data, "tick", 0)
        price = to_float(Map.get(market_data, "last_price", 0.0))
        previous = state.last_price
        change = if previous, do: price - previous, else: 0.0
        pct = if previous && previous != 0.0, do: change / previous * 100.0, else: 0.0
        signal = signal_for(change, pct, market_data)

        advice = %{
          "tick" => tick,
          "price" => Float.round(price, 4),
          "change" => Float.round(change, 4),
          "change_pct" => Float.round(pct, 3),
          "signal" => signal,
          "bid_depth" => Map.get(market_data, "bid_depth", 0),
          "ask_depth" => Map.get(market_data, "ask_depth", 0),
          "message" => advice_text(tick, price, pct, signal)
        }

        should_publish = publish_tick?(tick, state, pct)
        next_state = %{state | last_price: price}

        actions =
          if should_publish do
            maybe_send_slack(next_state.config, advice)

            [
              {:event, :market_advice_generated,
               Map.put(advice, "slack_enabled", slack_enabled?(next_state.config))}
            ]
          else
            []
          end

        next_state =
          if should_publish do
            %{next_state | last_sent_tick: tick, advice_count: next_state.advice_count + 1}
          else
            next_state
          end

        {:ok, next_state, actions}

      "market_signal" ->
        signal = payload(message) || %{}
        signal_count = state.signal_count + 1
        {slack_messages, slack_symbols} = slack_messages_for_signal(signal, state, signal_count)

        Enum.each(slack_messages, &maybe_send_slack(state.config, %{"message" => &1}))

        advice =
          signal
          |> Map.put("slack_enabled", slack_enabled?(state.config))
          |> Map.put("slack_policy", slack_policy_summary(state.config))
          |> Map.put("slack_message_count", length(slack_messages))
          |> Map.put("source", "stock_signal_analyzer")

        {:ok,
         %{
           state
           | advice_count: state.advice_count + 1,
             signal_count: signal_count,
             slack_symbols: slack_symbols,
             latest_signals: update_latest_signals(state.latest_signals, signal)
         },
         [
           {:event, :market_advice_generated, advice}
         ]}

      _ ->
        {:ok, state, []}
    end
  end

  @impl true
  def inspect_state(state) do
    %{
      last_price: state.last_price,
      last_sent_tick: state.last_sent_tick,
      advice_count: state.advice_count,
      signal_count: state.signal_count,
      slack_symbols: map_size(state.slack_symbols),
      slack_enabled: slack_enabled?(state.config)
    }
  end

  defp publish_tick?(tick, state, pct) do
    interval = Map.get(state.config, "advice_interval_ticks", 5)
    threshold = Map.get(state.config, "important_move_pct", 1.5)

    tick == 1 or tick - state.last_sent_tick >= interval or abs(pct) >= threshold
  end

  defp signal_for(change, pct, market_data) do
    bid_depth = Map.get(market_data, "bid_depth", 0)
    ask_depth = Map.get(market_data, "ask_depth", 0)

    cond do
      pct >= 1.5 -> "momentum_breakout"
      pct <= -1.5 -> "risk_off_drop"
      bid_depth > ask_depth * 1.5 -> "buy_pressure"
      ask_depth > bid_depth * 1.5 -> "sell_pressure"
      change > 0 -> "mild_uptrend"
      change < 0 -> "mild_downtrend"
      true -> "neutral"
    end
  end

  defp advice_text(tick, price, pct, signal) do
    "Market advisor tick #{tick}: #{signal}; price #{Float.round(price, 2)}; move #{Float.round(pct, 2)}%."
  end

  defp slack_messages_for_signal(signal, state, signal_count) do
    policy = slack_policy(state.config)
    symbol = Map.get(signal, "symbol", "UNKNOWN")
    action = Map.get(signal, "action", "hold_watch")
    confidence = to_float(Map.get(signal, "confidence", 0.0))
    previous = Map.get(state.slack_symbols, symbol, %{})
    last_alert_tick = Map.get(previous, "last_alert_tick", -1_000_000)
    last_action = Map.get(previous, "last_action")

    action_changed? = last_action not in [nil, action]
    high_confidence? = confidence >= policy.min_confidence
    actionable? = action in ["buy_watch", "sell_or_reduce_watch"]
    cooldown_ok? = signal_count - last_alert_tick >= policy.cooldown_ticks_per_symbol

    should_alert? =
      policy.mode != "off" and
        cooldown_ok? and
        actionable? and
        ((policy.alert_on_action_change and action_changed?) or high_confidence?)

    updated_symbol =
      previous
      |> Map.put("last_action", action)
      |> Map.put("last_confidence", confidence)
      |> maybe_put_alert_tick(should_alert?, signal_count)

    slack_symbols = Map.put(state.slack_symbols, symbol, updated_symbol)

    alert_messages =
      if should_alert? do
        [format_signal_alert(signal, action_changed?)]
      else
        []
      end

    digest_messages =
      if policy.digest_every_ticks > 0 and rem(signal_count, policy.digest_every_ticks) == 0 do
        [format_digest(update_latest_signals(state.latest_signals, signal))]
      else
        []
      end

    {alert_messages ++ digest_messages, slack_symbols}
  end

  defp maybe_put_alert_tick(symbol_state, true, signal_count),
    do: Map.put(symbol_state, "last_alert_tick", signal_count)

  defp maybe_put_alert_tick(symbol_state, false, _signal_count), do: symbol_state

  defp update_latest_signals(latest_signals, %{"symbol" => symbol} = signal) when is_binary(symbol) do
    Map.put(latest_signals || %{}, symbol, signal)
  end

  defp update_latest_signals(latest_signals, _signal), do: latest_signals || %{}

  defp format_signal_alert(signal, action_changed?) do
    symbol = Map.get(signal, "symbol", "UNKNOWN")
    action = Map.get(signal, "action", "hold_watch") |> human_action()
    price = signal |> Map.get("price", 0.0) |> to_float() |> Float.round(2)
    confidence = signal |> Map.get("confidence", 0.0) |> to_float() |> percent()
    indicators = Map.get(signal, "indicators", %{})
    rationale = Map.get(signal, "rationale", [])
    reason = List.first(rationale) || "multiple technical indicators aligned"
    next_watch = next_watch_text(signal)
    change_text = if action_changed?, do: "Signal changed: ", else: ""

    "#{change_text}#{symbol} shifted to #{action} at #{price}, confidence #{confidence}. " <>
      "Why: #{reason}. " <>
      "Indicators: MACD #{Map.get(indicators, "macd", "n/a")}, RSI #{Map.get(indicators, "rsi_14", "warming")}, momentum #{Map.get(indicators, "momentum_5_pct", "warming")}%. " <>
      "Watch next: #{next_watch}. " <>
      mock_data_claim()
  end

  defp format_digest(latest_signals) do
    signals = Map.values(latest_signals || %{})
    buys = top_symbols(signals, "buy_watch")
    sells = top_symbols(signals, "sell_or_reduce_watch")
    strongest = strongest_signal(signals)

    "Market advisor digest. " <>
      "Buy watch: #{join_or_none(buys)}. " <>
      "Sell/reduce watch: #{join_or_none(sells)}. " <>
      "Strongest setup: #{strongest}. " <>
      mock_data_claim()
  end

  defp top_symbols(signals, action) do
    signals
    |> Enum.filter(&(Map.get(&1, "action") == action))
    |> Enum.sort_by(&(to_float(Map.get(&1, "confidence", 0.0))), :desc)
    |> Enum.take(3)
    |> Enum.map(&Map.get(&1, "symbol", "UNKNOWN"))
  end

  defp strongest_signal([]), do: "none"

  defp strongest_signal(signals) do
    signal = Enum.max_by(signals, &(to_float(Map.get(&1, "confidence", 0.0))), fn -> %{} end)
    "#{Map.get(signal, "symbol", "UNKNOWN")} #{human_action(Map.get(signal, "action", "hold_watch"))} at #{percent(to_float(Map.get(signal, "confidence", 0.0)))} confidence"
  end

  defp join_or_none([]), do: "none"
  defp join_or_none(items), do: Enum.join(items, ", ")

  defp next_watch_text(signal) do
    price = signal |> Map.get("price", 0.0) |> to_float()
    action = Map.get(signal, "action", "hold_watch")

    case action do
      "buy_watch" -> "confirmation above #{Float.round(price * 1.005, 2)}, cancel below #{Float.round(price * 0.99, 2)}"
      "sell_or_reduce_watch" -> "risk easing above #{Float.round(price * 1.01, 2)}, renewed weakness below #{Float.round(price * 0.995, 2)}"
      _ -> "wait for stronger trend, MACD, and RSI confirmation"
    end
  end

  defp human_action("buy_watch"), do: "BUY WATCH"
  defp human_action("sell_or_reduce_watch"), do: "SELL/REDUCE WATCH"
  defp human_action("hold_watch"), do: "HOLD WATCH"
  defp human_action(action), do: String.upcase(to_string(action))

  defp percent(value), do: "#{round(value * 100)}%"

  defp mock_data_claim do
    "Claim: this is based on mockup market data, not real market data or financial advice."
  end

  defp slack_policy(config) do
    policy = Map.get(config, "slack_policy", %{})

    %{
      mode: Map.get(policy, "mode", "important_only"),
      min_confidence: policy |> Map.get("min_confidence", 0.65) |> to_float(),
      cooldown_ticks_per_symbol: Map.get(policy, "cooldown_ticks_per_symbol", 20),
      alert_on_action_change: Map.get(policy, "alert_on_action_change", true),
      digest_every_ticks: Map.get(policy, "digest_every_ticks", 100)
    }
  end

  defp slack_policy_summary(config) do
    policy = slack_policy(config)

    %{
      "mode" => policy.mode,
      "min_confidence" => policy.min_confidence,
      "cooldown_ticks_per_symbol" => policy.cooldown_ticks_per_symbol,
      "alert_on_action_change" => policy.alert_on_action_change,
      "digest_every_ticks" => policy.digest_every_ticks
    }
  end

  defp maybe_send_slack(config, advice) do
    if slack_enabled?(config) do
      channel = System.get_env("SLACK_DEFAULT_CHANNEL") || Map.get(config, "slack_channel", "#claw")

      case SlackCommunicateSkill.send_message(ensure_mock_data_claim(advice["message"]), channel: channel) do
        {:ok, result} ->
          Logger.info("[MarketAdvisor] Sent advice to Slack: #{inspect(result)}")

        {:skipped, result} ->
          Logger.warning("[MarketAdvisor] Skipped Slack advice: #{inspect(result)}")

        {:error, result} ->
          Logger.error("[MarketAdvisor] Failed to send Slack advice: #{inspect(result)}")
      end
    end
  end

  defp ensure_mock_data_claim(message) do
    message = to_string(message || "")

    if String.contains?(message, "mockup market data") do
      message
    else
      "#{message} #{mock_data_claim()}"
    end
  end

  defp slack_enabled?(config) do
    SlackCommunicateSkill.enabled?(config)
  end

  defp to_float(v) when is_number(v), do: v * 1.0
  defp to_float(v) when is_binary(v), do: String.to_float(v)
  defp to_float(_), do: 0.0
end
