defmodule MirrorNeuron.Examples.StreamLiveBackpressure.LiveSource do
  use MirrorNeuron.AgentTemplate

  alias MirrorNeuron.Message
  alias MirrorNeuron.Runtime

  @impl true
  def init(node) do
    {:ok,
     %{
       config: node.config || %{},
       seq: 0,
       scheduled_token: nil,
       stream_id: nil
     }}
  end

  @impl true
  def handle_message(message, state, context) do
    case type(message) do
      "stream_start" ->
        payload = payload(message) || %{}
        stream_id = payload["stream_id"] || Map.get(state.config, "stream_id", "bp-live")
        {:ok, schedule_next(%{state | stream_id: stream_id}, context, 0), []}

      "tick" ->
        emit_scheduled(message, state, context)

      _ ->
        {:ok, state, []}
    end
  end

  @impl true
  def recover(%{stream_id: nil} = state, _context), do: {:ok, state, []}

  def recover(state, context) do
    {:ok, schedule_next(state, context, interval_ms(state.config)), []}
  end

  @impl true
  def inspect_state(state) do
    %{seq: state.seq, stream_id: state.stream_id}
  end

  defp emit_scheduled(message, %{scheduled_token: token} = state, context) do
    if Map.get(payload(message) || %{}, "token") == token do
      next_seq = state.seq + 1
      stream_id = state.stream_id || Map.get(state.config, "stream_id", "bp-live")

      body = %{
        "seq" => next_seq,
        "value" => next_seq * 10,
        "source" => "live_source"
      }

      stream = %{
        "stream_id" => stream_id,
        "seq" => next_seq,
        "open" => next_seq == 1
      }

      next_state =
        state
        |> Map.put(:seq, next_seq)
        |> Map.put(:stream_id, stream_id)
        |> Map.put(:scheduled_token, nil)
        |> schedule_next(context, interval_ms(state.config))

      {:ok, next_state,
       [
         {:event, :live_stream_event_generated,
          %{"agent" => "live_source", "seq" => next_seq, "stream_id" => stream_id}},
         {:emit_to, target_node(state.config), "telemetry_event", body,
          [class: "stream", stream: stream]}
       ]}
    else
      {:ok, state, []}
    end
  end

  defp emit_scheduled(_message, state, _context), do: {:ok, state, []}

  defp schedule_next(state, context, delay_ms) do
    token = state.seq + 1

    spawn(fn ->
      if delay_ms > 0 do
        Process.sleep(delay_ms)
      end

      Runtime.deliver(
        context.job_id,
        context.node.node_id,
        Message.new(
          context.job_id,
          context.node.node_id,
          context.node.node_id,
          "tick",
          %{"token" => token},
          class: "control"
        )
      )
    end)

    %{state | scheduled_token: token}
  end

  defp interval_ms(config), do: Map.get(config, "interval_ms", 250)

  defp target_node(config), do: Map.get(config, "target_node", "slow_enricher")
end
