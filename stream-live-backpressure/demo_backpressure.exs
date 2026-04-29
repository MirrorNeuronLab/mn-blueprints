blueprint_path = Path.expand(__DIR__)

{:ok, job_id} = MirrorNeuron.run_manifest(blueprint_path, await: false)

IO.puts("started #{job_id}")
Process.sleep(400)

results =
  1..20
  |> Task.async_stream(
    fn index ->
      MirrorNeuron.send_message(job_id, "slow_enricher", %{
        "type" => "telemetry_event",
        "body" => %{"seq" => "external-#{index}", "value" => index},
        "class" => "stream",
        "stream" => %{
          "stream_id" => "external-live",
          "seq" => index,
          "open" => index == 1,
          "close" => index == 20
        }
      })
    end,
    max_concurrency: 20,
    timeout: 5_000
  )
  |> Enum.map(fn {:ok, result} -> result end)

accepted = Enum.count(results, &match?({:ok, "delivered"}, &1))
retry_later = Enum.count(results, &match?({:error, {:retry_later, _}}, &1))

{:ok, pressure} = MirrorNeuron.pressure(job_id)
{:ok, events} = MirrorNeuron.events(job_id)

interesting =
  events
  |> Enum.filter(&(&1["type"] in ["backpressure_state", "external_input_rejected", "slow_event_processed"]))
  |> Enum.take(-12)

IO.puts(
  Jason.encode!(
    %{
      job_id: job_id,
      accepted: accepted,
      retry_later: retry_later,
      pressure: pressure,
      recent_events: interesting
    },
    pretty: true
  )
)

MirrorNeuron.cancel(job_id)
