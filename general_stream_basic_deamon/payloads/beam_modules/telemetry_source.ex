defmodule MirrorNeuron.Examples.StreamBasicDaemon.TelemetrySource do
  use MirrorNeuron.AgentTemplate

  alias MirrorNeuron.Message
  alias MirrorNeuron.Runtime

  @impl true
  def init(node) do
    {:ok,
     %{
       config: node.config || %{},
       sample_index: 0,
       chunk_seq: 0,
       scheduled_token: nil,
       stream_id: nil
     }}
  end

  @impl true
  def handle_message(message, state, context) do
    case type(message) do
      "stream_start" ->
        payload = payload(message) || %{}
        stream_id = payload["stream_id"] || default_stream_id(context)
        {:ok, schedule_next(%{state | stream_id: stream_id}, context, 0), []}

      "tick" ->
        emit_scheduled_chunk(message, state, context)

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
    %{
      sample_index: state.sample_index,
      chunk_seq: state.chunk_seq,
      stream_id: state.stream_id
    }
  end

  defp emit_scheduled_chunk(message, %{scheduled_token: token} = state, context) do
    if Map.get(payload(message) || %{}, "token") == token do
      stream_id = state.stream_id || default_stream_id(context)
      chunk_size = chunk_size(state.config)
      start_index = state.sample_index + 1
      rows = Enum.map(start_index..(start_index + chunk_size - 1), &sample(&1, state.config))
      next_chunk_seq = state.chunk_seq + 1

      stream = %{
        "stream_id" => stream_id,
        "seq" => next_chunk_seq,
        "open" => next_chunk_seq == 1
      }

      next_state =
        state
        |> Map.put(:sample_index, state.sample_index + chunk_size)
        |> Map.put(:chunk_seq, next_chunk_seq)
        |> Map.put(:stream_id, stream_id)
        |> Map.put(:scheduled_token, nil)
        |> schedule_next(context, interval_ms(state.config))

      {:ok, next_state,
       [
         {:event, :telemetry_chunk_generated,
          %{
            "stream_id" => stream_id,
            "chunk_seq" => next_chunk_seq,
            "first_sample_index" => start_index,
            "sample_count" => chunk_size
          }},
         {:emit_to, target_node(state.config), "telemetry_chunk", rows,
          [
            class: "stream",
            content_type: "application/x-ndjson",
            content_encoding: content_encoding(state.config),
            headers: %{
              "schema_ref" => "com.mirrorneuron.streaming.telemetry.chunk",
              "schema_version" => "1.0.0",
              "stream_role" => "telemetry"
            },
            stream: stream
          ]}
       ]}
    else
      {:ok, state, []}
    end
  end

  defp emit_scheduled_chunk(_message, state, _context), do: {:ok, state, []}

  defp schedule_next(state, context, delay_ms) do
    token = state.chunk_seq + 1

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

  defp sample(index, config) do
    baseline = Map.get(config, "baseline", 24)
    jitter = Map.get(config, "jitter", 4)
    peak_height = Map.get(config, "peak_height", 55)
    peak_every = Map.get(config, "peak_every", 20)
    device_id = Map.get(config, "device_id", "sensor-alpha")

    value = baseline + oscillation(index, jitter)
    value = if peak_every > 0 and rem(index, peak_every) == 0, do: value + peak_height, else: value

    %{
      "sample_index" => index,
      "device_id" => device_id,
      "metric" => "throughput",
      "value" => value,
      "unit" => "events_per_second",
      "ts" => "sample-#{index}"
    }
  end

  defp oscillation(index, jitter) when jitter > 0 do
    rem(index * 7, jitter * 2 + 1) - jitter
  end

  defp oscillation(_index, _jitter), do: 0

  defp default_stream_id(context), do: "#{context.job_id}:#{context.node.node_id}:telemetry"

  defp interval_ms(config), do: Map.get(config, "interval_ms", 1000)

  defp chunk_size(config), do: max(Map.get(config, "chunk_size", 6), 1)

  defp content_encoding(config), do: Map.get(config, "content_encoding", "gzip")

  defp target_node(config), do: Map.get(config, "target_node", "peak_detector")
end
