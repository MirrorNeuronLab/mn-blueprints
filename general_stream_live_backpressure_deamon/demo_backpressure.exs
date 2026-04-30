blueprint_path = Path.expand(__DIR__)

{:ok, job_id} = MirrorNeuron.run_manifest(blueprint_path, await: false, resource_admission: false)
run_log = Path.join("/tmp", "mn_#{job_id}/run.log")
File.mkdir_p!(Path.dirname(run_log))

log_json = fn event ->
  File.write!(
    run_log,
    "#{DateTime.utc_now() |> DateTime.to_iso8601()} INFO #{Jason.encode!(event)}\n",
    [:append]
  )
end

log_json.(%{
  type: "demo_started",
  payload: %{
    blueprint: "general_stream_live_backpressure_deamon",
    run_log: run_log,
    note: "slow_enricher and metrics_sink are manually delayed to force backpressure"
  }
})

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

Process.sleep(1_500)

{:ok, pressure} = MirrorNeuron.pressure(job_id)
{:ok, events} = MirrorNeuron.events(job_id)

interesting =
  events
  |> Enum.filter(
    &(&1["type"] in [
        "backpressure_state",
        "external_input_rejected",
        "slow_event_processed",
        "stream_metrics_updated",
          "live_stream_event_generated"
      ])
  )
  |> Enum.take(-12)

Enum.each(interesting, log_json)

log_json.(%{
  type: "demo_summary",
  payload: %{
    job_id: job_id,
    accepted: accepted,
    retry_later: retry_later,
    pressure: pressure
  }
})

IO.puts(
  Jason.encode!(
    %{
      job_id: job_id,
      accepted: accepted,
      retry_later: retry_later,
      run_log: run_log,
      pressure: pressure,
      recent_events: interesting
    },
    pretty: true
  )
)

MirrorNeuron.cancel(job_id)
