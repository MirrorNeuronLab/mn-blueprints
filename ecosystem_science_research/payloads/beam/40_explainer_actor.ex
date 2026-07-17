defmodule MnBlueprints.EcosystemScience.V1.ExplainerActor do
  @moduledoc false
  use GenServer

  def start, do: GenServer.start(__MODULE__, :ok)

  @impl true
  def init(:ok), do: {:ok, %{}}

  @impl true
  def handle_info({:explain, epoch, simulation, options, world}, state) do
    {explanation, usage, warnings} = explain_once(simulation, options)
    send(world, {:explanation_complete, epoch, explanation, usage, warnings})
    {:noreply, state}
  end

  def handle_info(_stale_or_unknown, state), do: {:noreply, state}

  defp explain_once(simulation, options) do
    environment = Map.get(options, :environment, %{})
    provider = Map.get(environment, "MN_LLM_PROVIDER", "")

    if provider == "fake" or Map.get(options, :llm_mode) == "fake" do
      explanation = deterministic_explanation(simulation, "fake model mode")

      {explanation,
       %{mode: "fake", model: Map.get(environment, "MN_LLM_MODEL", "fake"), requests: 0,
         authoritative: false}, []}
    else
      case live_request(simulation, environment, options) do
        {:ok, explanation, model} ->
          {explanation, %{mode: "live", model: model, requests: 1, authoritative: false}, []}

        {:error, reason, attempted_model} ->
          warning = "LLM explanation unavailable; deterministic explanation used: #{format_reason(reason)}"

          {deterministic_explanation(simulation, warning),
           %{mode: "fallback", model: attempted_model, requests: 1, authoritative: false,
             error: format_reason(reason)}, [warning]}
      end
    end
  end

  defp live_request(simulation, environment, options) do
    model = Map.get(environment, "MN_LLM_MODEL", Map.get(options, :llm_model, "default"))
    base = Map.get(environment, "MN_LLM_API_BASE", "http://127.0.0.1:4000/v1")
      |> String.trim_trailing("/")
    timeout = Map.get(options, :llm_timeout_seconds, 60) * 1_000
    max_tokens = Map.get(options, :llm_max_tokens, 700)
    api_key = Map.get(environment, "MN_LLM_API_KEY", "")

    prompt = """
    Explain this immutable synthetic ecosystem result for a science researcher.
    Do not alter, recompute, or invent measurements. Return JSON only with exactly:
    {"summary": string, "findings": [string], "limitations": [string]}.

    Measurements:
    #{Jason.encode!(prompt_measurements(simulation))}
    """

    body = Jason.encode!(%{
      model: model,
      temperature: 0.0,
      max_tokens: max_tokens,
      messages: [
        %{role: "system", content: "You explain frozen simulation measurements; you never modify them."},
        %{role: "user", content: prompt}
      ]
    })

    headers =
      [{~c"content-type", ~c"application/json"}] ++
        if(api_key == "", do: [], else: [{~c"authorization", String.to_charlist("Bearer " <> api_key)}])

    :inets.start()
    :ssl.start()

    response =
      :httpc.request(
        :post,
        {String.to_charlist(base <> "/chat/completions"), headers, ~c"application/json", body},
        [timeout: timeout, connect_timeout: min(timeout, 10_000)],
        body_format: :binary
      )

    case response do
      {:ok, {{_http, status, _reason}, _headers, response_body}} when status in 200..299 ->
        with {:ok, envelope} <- Jason.decode(response_body),
             content when is_binary(content) <- get_in(envelope, ["choices", Access.at(0), "message", "content"]),
             {:ok, decoded} <- decode_json_object(content),
             :ok <- validate_explanation(decoded) do
          {:ok, decoded, model}
        else
          error -> {:error, {:invalid_model_output, error}, model}
        end

      {:ok, {{_http, status, _reason}, _headers, response_body}} ->
        {:error, {:http_status, status, String.slice(response_body, 0, 240)}, model}

      {:error, reason} ->
        {:error, {:request_failed, reason}, model}
    end
  rescue
    error ->
      attempted_model =
        Map.get(environment, "MN_LLM_MODEL", Map.get(options, :llm_model, "default"))

      {:error, {:request_exception, Exception.message(error)}, attempted_model}
  end

  defp decode_json_object(content) do
    cleaned = content |> String.trim() |> String.replace(~r/^```(?:json)?\s*|\s*```$/i, "")
    Jason.decode(cleaned)
  end

  defp validate_explanation(%{
         "summary" => summary,
         "findings" => findings,
         "limitations" => limitations
       })
       when is_binary(summary) and is_list(findings) and is_list(limitations) do
    if Enum.all?(findings ++ limitations, &is_binary/1), do: :ok, else: {:error, :non_string_items}
  end

  defp validate_explanation(_), do: {:error, :wrong_schema}

  defp prompt_measurements(simulation) do
    %{
      seed: simulation.simulation_seed,
      initial_population: simulation.initial_population,
      final_population: simulation.population_alive,
      births: simulation.births,
      deaths: simulation.deaths,
      mutations: simulation.mutations,
      ticks: simulation.simulated_ticks,
      migration_batches: simulation.migration_batches,
      cross_node_migration_batches: simulation.cross_node_migration_batches,
      population_timeline: simulation.population_timeline,
      regions: Enum.map(simulation.raw_region_results, fn region ->
        %{region_id: region.region_id, population: region.population, births: region.births,
          deaths: region.deaths, resource_band: region.resource_profile.band}
      end),
      top_lineages: simulation.top_10_dna,
      invariants: simulation.invariants,
      scientific_limitations: simulation.scientific_limitations
    }
  end

  defp deterministic_explanation(simulation, reason) do
    ordered = Enum.sort_by(simulation.raw_region_results, &{-&1.population, &1.region_id})
    strongest = List.first(ordered)
    weakest = List.last(ordered)
    top = List.first(simulation.top_10_dna)

    lineage_finding =
      if top do
        "The leading retained lineage #{top.dna_key} has #{top.alive} living members across #{length(top.regions_present)} region(s)."
      else
        "No living lineage remained to rank at the final barrier."
      end

    %{
      "summary" =>
        "The deterministic run ended with #{simulation.population_alive} animals after #{simulation.simulated_ticks} ticks (#{simulation.births} births, #{simulation.deaths} deaths, and #{simulation.mutations} inherited-trait mutation events).",
      "findings" => [
        "#{strongest.region_id} had the largest final regional population (#{strongest.population}); #{weakest.region_id} had the smallest (#{weakest.population}).",
        lineage_finding,
        "All 16 regions crossed every tick barrier, and migration changed placement but not the global population total."
      ],
      "limitations" => simulation.scientific_limitations,
      "generation" => %{"mode" => "deterministic", "reason" => reason}
    }
  end

  defp format_reason(reason), do: inspect(reason, limit: 8, printable_limit: 300)
end
