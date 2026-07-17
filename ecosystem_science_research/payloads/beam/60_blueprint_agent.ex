defmodule MnBlueprints.EcosystemScience.V1.BlueprintAgent do
  use MirrorNeuron.AgentTemplate

  alias MnBlueprints.EcosystemScience.V1.{Core, WorldActor}

  @defaults %{
    seed: 517_498_978,
    total_animals: 2_000,
    duration_seconds: 300,
    tick_seconds: 5,
    max_food: 420.0,
    food_regen_per_tick: 72.0,
    max_region_population: 220,
    migration_rate: 0.035,
    mutation_rate: 0.05,
    tick_delay_ms: 0,
    local_top_k: 20,
    require_multi_node: false
  }

  @impl true
  def init(node) do
    {:ok, %{node_config: node.config || %{}, processed: false}}
  end

  @impl true
  def handle_message(_message, %{processed: true} = state, _context),
    do: {:ok, state, []}

  def handle_message(message, state, context) do
    input = payload(message) || %{}

    with {:ok, config} <- normalize_config(input),
         options <- world_options(state.node_config),
         {:ok, result} <- WorldActor.run(config, options, 120_000),
         {:ok, artifact_paths, final_artifact} <- write_artifacts(result, state.node_config, context) do
      event_type = if result.llm_usage.mode == "fallback",
        do: :ecosystem_explanation_fallback, else: :ecosystem_explanation_completed

      output = Map.put(final_artifact, "artifact_paths", artifact_paths)

      {:ok, %{state | processed: true},
       [
         {:event, :native_ecosystem_started,
          %{"regions" => 16, "animals" => config.total_animals, "ticks" => config.total_steps}},
         {:event, :native_ecosystem_completed,
          %{"final_population" => result.simulation.population_alive,
            "migration_batches" => result.simulation.migration_batches}},
         {:event, event_type,
          %{"mode" => result.llm_usage.mode, "warnings" => result.warnings}},
         {:emit, "simulation_done", output},
         {:complete_step, output},
         {:event, :ecosystem_artifacts_written,
          %{"artifacts" => Map.values(artifact_paths)}}
       ]}
    else
      {:error, reason} -> {:error, reason, state}
    end
  end

  @impl true
  def recover(state, _context), do: {:ok, state, []}
  @impl true
  def snapshot_state(state), do: state
  @impl true
  def restore_state(snapshot), do: {:ok, snapshot}
  @impl true
  def inspect_state(state), do: %{processed: state.processed}

  defp normalize_config(input) do
    ecosystem = fetch(input, "ecosystem", input)
    requested_regions = fetch(ecosystem, "region_count", 16)

    config = %{
      seed: integer(ecosystem, "seed", @defaults.seed),
      total_animals: integer(ecosystem, "total_animals", @defaults.total_animals),
      duration_seconds: integer(ecosystem, "duration_seconds", @defaults.duration_seconds),
      tick_seconds: integer(ecosystem, "tick_seconds", @defaults.tick_seconds),
      max_food: number(ecosystem, "max_food", @defaults.max_food),
      food_regen_per_tick: number(ecosystem, "food_regen_per_tick", @defaults.food_regen_per_tick),
      max_region_population: integer(ecosystem, "max_region_population", @defaults.max_region_population),
      migration_rate: number(ecosystem, "migration_rate", @defaults.migration_rate),
      mutation_rate: number(ecosystem, "mutation_rate", @defaults.mutation_rate),
      tick_delay_ms: integer(ecosystem, "tick_delay_ms", @defaults.tick_delay_ms),
      local_top_k: integer(ecosystem, "local_top_k", @defaults.local_top_k),
      require_multi_node: boolean(ecosystem, "require_multi_node", @defaults.require_multi_node)
    }

    cond do
      requested_regions != 16 -> {:error, "region_count is fixed at exactly 16"}
      config.total_animals < 1 -> {:error, "total_animals must be positive"}
      config.duration_seconds < 1 -> {:error, "duration_seconds must be positive"}
      config.tick_seconds < 1 -> {:error, "tick_seconds must be positive"}
      config.max_food <= 0 -> {:error, "max_food must be positive"}
      config.food_regen_per_tick < 0 -> {:error, "food_regen_per_tick cannot be negative"}
      config.max_region_population < 1 -> {:error, "max_region_population must be positive"}
      config.migration_rate < 0 or config.migration_rate > 1 -> {:error, "migration_rate must be between 0 and 1"}
      config.mutation_rate < 0 or config.mutation_rate > 1 -> {:error, "mutation_rate must be between 0 and 1"}
      config.tick_delay_ms < 0 -> {:error, "tick_delay_ms cannot be negative"}
      config.local_top_k < 1 -> {:error, "local_top_k must be positive"}
      true -> {:ok, Map.put(config, :total_steps, Core.steps(config))}
    end
  rescue
    error -> {:error, "invalid ecosystem input: #{Exception.message(error)}"}
  end

  defp world_options(node_config) do
    environment = Map.get(node_config, "environment", %{})

    %{
      payloads_path: Map.fetch!(node_config, "__payloads_path"),
      environment: environment,
      llm_mode: if(Map.get(environment, "MN_LLM_PROVIDER") == "fake", do: "fake", else: "live"),
      llm_model: Map.get(environment, "MN_LLM_MODEL", "default"),
      llm_timeout_seconds: env_integer(environment, "MN_LLM_TIMEOUT_SECONDS", 60),
      llm_max_tokens: env_integer(environment, "MN_LLM_MAX_TOKENS", 700)
    }
  end

  defp write_artifacts(result, node_config, context) do
    environment = Map.get(node_config, "environment", %{})
    runs_root = Map.get(environment, "MN_RUNS_ROOT", Path.expand("~/.mn/runs"))
    run_id = Map.get(environment, "MN_RUN_ID", context.job_id)
    run_dir = if Path.basename(runs_root) == run_id, do: runs_root, else: Path.join(runs_root, run_id)
    File.mkdir_p!(run_dir)

    paths = %{
      "simulation_result" => Path.join(run_dir, "simulation_result.json"),
      "actor_topology" => Path.join(run_dir, "actor_topology.json"),
      "final_artifact" => Path.join(run_dir, "final_artifact.json")
    }

    final_artifact = %{
      "schema_version" => "mn.blueprint.final_artifact.v1",
      "blueprint_id" => "ecosystem_science_research",
      "status" => "complete",
      "simulation" => result.simulation,
      "topology" => result.topology,
      "explanation" => result.explanation,
      "llm_usage" => result.llm_usage,
      "warnings" => result.warnings,
      "authority_boundary" => %{
        "simulation" => "authoritative deterministic output",
        "explanation" => "non-authoritative interpretation"
      }
    }

    atomic_json!(paths["simulation_result"], result.simulation)
    atomic_json!(paths["actor_topology"], result.topology)
    atomic_json!(paths["final_artifact"], final_artifact)

    {:ok, paths, final_artifact}
  rescue
    error -> {:error, {:artifact_write_failed, Exception.message(error)}}
  end

  defp atomic_json!(path, value) do
    temporary = path <> ".tmp-" <> Integer.to_string(System.unique_integer([:positive]))
    File.write!(temporary, Jason.encode_to_iodata!(value, pretty: true))
    File.rename!(temporary, path)
  end

  defp fetch(map, key, default) when is_map(map) do
    Map.get(map, key, Map.get(map, String.to_atom(key), default))
  end

  defp integer(map, key, default) do
    case fetch(map, key, default) do
      value when is_integer(value) -> value
      value when is_float(value) -> trunc(value)
      value when is_binary(value) -> String.to_integer(value)
    end
  end

  defp number(map, key, default) do
    case fetch(map, key, default) do
      value when is_number(value) -> value * 1.0
      value when is_binary(value) -> String.to_float(value)
    end
  end

  defp boolean(map, key, default) do
    case fetch(map, key, default) do
      value when is_boolean(value) -> value
      "true" -> true
      "false" -> false
      _ -> default
    end
  end

  defp env_integer(environment, key, default) do
    case Map.get(environment, key) do
      nil -> default
      value when is_integer(value) -> value
      value -> String.to_integer(to_string(value))
    end
  end
end
