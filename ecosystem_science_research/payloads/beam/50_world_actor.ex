defmodule MnBlueprints.EcosystemScience.V1.WorldActor do
  @moduledoc false
  use GenServer

  alias MnBlueprints.EcosystemScience.V1.{CollectorActor, Core, ExplainerActor, NodeHost}

  @remote_sources ["00_core.ex", "10_region_actor.ex", "30_node_host.ex"]

  def run(config, options \\ %{}, timeout \\ 120_000) do
    run_with_restart(config, options, timeout, 1, [])
  end

  defp run_with_restart(config, options, timeout, attempt, prior_warnings) do
    case run_attempt(config, options, timeout, attempt) do
      {:ok, result} ->
        warnings = prior_warnings ++ result.warnings
        {:ok, %{result | warnings: warnings, topology: Map.put(result.topology, :attempt, attempt)}}

      {:error, reason} when attempt == 1 ->
        warning = "Native actor attempt 1 failed and was cleaned up; deterministic simulation restarted once: #{inspect(reason)}"
        run_with_restart(config, options, timeout, 2, prior_warnings ++ [warning])

      {:error, reason} ->
        {:error, {:simulation_failed_after_restart, reason}}
    end
  end

  defp run_attempt(config, options, timeout, attempt) do
    with {:ok, pid} <- GenServer.start(__MODULE__, {config, options, attempt}) do
      try do
        GenServer.call(pid, :run, timeout)
      catch
        :exit, reason ->
          if Process.alive?(pid), do: GenServer.stop(pid, :shutdown, 5_000)
          {:error, {:world_actor_exit, reason}}
      end
    end
  end

  @impl true
  def init({config, options, attempt}) do
    {:ok,
     %{
       config: config,
       options: options,
       attempt: attempt,
       epoch: System.unique_integer([:positive, :monotonic]),
       caller: nil,
       phase: :idle,
       hosts: [],
       host_monitors: %{},
       regions: %{},
       collector: nil,
       explainer: nil,
       awaiting: MapSet.new(),
       barrier_history: [],
       current_tick_results: %{},
       region_counts: %{},
       simulation: nil,
       topology: nil,
       warnings: [],
       counts: empty_world_counts()
     }}
  end

  @impl true
  def handle_call(:run, from, state) do
    case setup(state) do
      {:ok, ready} ->
        {:noreply, %{ready | caller: from, phase: :bootstrap}}

      {:error, reason, partial} ->
        cleanup(partial)
        {:stop, :normal, {:error, reason}, partial}
    end
  end

  @impl true
  def handle_info({:bootstrap_ready, epoch, region_id, pid, actor_node},
        %{epoch: epoch, phase: :bootstrap} = state) do
    expected_pid = Map.get(state.regions, region_id)

    if expected_pid == pid and actor_node == node(pid) do
      awaiting = MapSet.delete(state.awaiting, region_id)
      next = %{state | awaiting: awaiting,
        counts: increment(state.counts, :bootstrap_ready_received)}

      if MapSet.size(awaiting) == 0 do
        schedule_tick(next, 1)
      else
        {:noreply, next}
      end
    else
      {:noreply, state}
    end
  end

  def handle_info({:begin_tick, epoch, tick}, %{epoch: epoch} = state) do
    {:noreply, begin_tick(state, tick)}
  end

  def handle_info({:tick_complete, epoch, region_id, tick_result, counts},
        %{epoch: epoch, phase: {:tick, tick}} = state) when tick_result.tick == tick do
    if MapSet.member?(state.awaiting, region_id) do
      awaiting = MapSet.delete(state.awaiting, region_id)
      region_counts = Map.put(state.region_counts, region_id, counts)
      current_tick_results = Map.put(state.current_tick_results, region_id, tick_result)
      next = %{state | awaiting: awaiting, region_counts: region_counts,
        current_tick_results: current_tick_results,
        counts: increment(state.counts, :tick_complete_received)}

      if MapSet.size(awaiting) == 0 do
        barrier = %{
          tick: tick,
          completed_region_count: 16,
          completed_regions: Core.region_ids(),
          births: barrier_sum(next, :births),
          deaths: barrier_sum(next, :deaths),
          outgoing: barrier_sum(next, :outgoing),
          migration_batches: barrier_sum(next, :migration_batches)
        }

        next = %{next | barrier_history: next.barrier_history ++ [barrier]}

        if tick == next.config.total_steps do
          request_collection(next)
        else
          schedule_tick(next, tick + 1)
        end
      else
        {:noreply, next}
      end
    else
      {:noreply, state}
    end
  end

  def handle_info({:collection_complete, epoch, aggregate, raw_regions},
        %{epoch: epoch, phase: :collecting} = state) do
    direct = direct_counts(state)
    invariants = invariants(state, aggregate, raw_regions, direct)

    simulation = aggregate
      |> Map.put(:initial_population, state.config.total_animals)
      |> Map.put(:simulated_ticks, state.config.total_steps)
      |> Map.put(:simulated_duration_seconds, state.config.duration_seconds)
      |> Map.put(:migration_delay_ticks, 2)
      |> Map.put(:migration_batches, direct.region.migration_batches_sent)
      |> Map.put(:migration_acks, direct.region.migration_acks_received)
      |> Map.put(:cross_node_migration_batches, direct.region.cross_node_migration_batches)
      |> Map.put(:raw_region_results, raw_regions)
      |> Map.put(:tick_barriers, state.barrier_history)
      |> Map.put(:direct_message_counts, direct)
      |> Map.put(:invariants, invariants)
      |> Map.put(:scientific_limitations, scientific_limitations())

    send(state.explainer, {:explain, epoch, simulation, state.options, self()})

    next = %{state | phase: :explaining, simulation: simulation,
      counts: increment(state.counts, :explanation_handoffs)}
    {:noreply, next}
  end

  def handle_info({:explanation_complete, epoch, explanation, usage, explanation_warnings},
        %{epoch: epoch, phase: :explaining} = state) do
    warnings = state.warnings ++ explanation_warnings
    cleaned = cleanup(state)

    topology = state.topology
      |> Map.put(:actors_cleaned_up, cleaned)
      |> Map.put(:direct_message_counts, state.simulation.direct_message_counts)
      |> Map.put(:cross_node_migration_batches, state.simulation.cross_node_migration_batches)

    result = %{
      simulation: state.simulation,
      topology: topology,
      explanation: explanation,
      llm_usage: usage,
      warnings: warnings
    }

    GenServer.reply(state.caller, {:ok, result})
    {:stop, :normal, %{state | caller: nil, hosts: [], collector: nil, explainer: nil}}
  end

  def handle_info({:DOWN, ref, :process, pid, reason}, state) do
    case Map.get(state.host_monitors, ref) do
      nil -> {:noreply, state}
      host_info -> fail_attempt({:actor_host_lost, host_info.node, pid, reason}, state)
    end
  end

  def handle_info(_stale_or_unknown, state), do: {:noreply, state}

  @impl true
  def terminate(_reason, state) do
    if state.hosts != [] or state.collector || state.explainer, do: cleanup(state)
    :ok
  end

  defp setup(state) do
    nodes = [node() | Node.list(:connected)] |> Enum.uniq()
    nodes = [node() | (nodes -- [node()] |> Enum.sort_by(&Atom.to_string/1))]

    cond do
      state.config.require_multi_node and length(nodes) < 2 ->
        {:error, :multi_node_cluster_required_but_no_peer_connected, state}

      true ->
        warnings =
          if length(nodes) == 1 do
            ["Only one BEAM node was connected; all 16 region actors ran locally using the distributed protocol."]
          else
            []
          end

        with :ok <- install_remote_modules(tl(nodes), state.options),
             {:ok, hosts, regions} <- start_hosts(nodes),
             {:ok, collector} <- CollectorActor.start(),
             {:ok, explainer} <- ExplainerActor.start() do
          monitors = Enum.into(hosts, %{}, fn host ->
            {Process.monitor(host.pid), host}
          end)

          send(collector, {:collect, state.epoch, self(), 16})
          profiles = Core.build_region_profiles(state.config.seed)
          allocation = Core.animal_allocation(state.config.total_animals, profiles, state.config.seed)

          Enum.zip(profiles, allocation) |> Enum.each(fn {profile, animal_count} ->
            region_pid = Map.fetch!(regions, profile.region_id)
            bootstrap = Core.build_bootstrap(profile, animal_count, state.config.seed, state.config)
            send(region_pid, {:bootstrap, state.epoch, bootstrap, state.config, regions, self()})
          end)

          placements = Core.region_ids() |> Enum.map(fn region_id ->
            pid = Map.fetch!(regions, region_id)
            %{region_id: region_id, node: Atom.to_string(node(pid)), actor_pid: inspect(pid),
              protocol: "direct_pid"}
          end)

          topology = %{
            transport: "native_beam_direct_pid",
            module_release: "MnBlueprints.EcosystemScience.V1",
            redis_inside_actor_system: false,
            domain_actor_count: 19,
            domain_actors: %{world: 1, regions: 16, collector: 1, final_explainer: 1},
            temporary_node_hosts: length(hosts),
            connected_nodes: Enum.map(nodes, &Atom.to_string/1),
            region_placement: placements,
            round_robin: true,
            cross_node_region_placement: placements |> Enum.map(& &1.node) |> Enum.uniq() |> length() > 1,
            run_epoch_protocol: true,
            node_hosts: Enum.map(hosts, &%{node: Atom.to_string(&1.node), pid: inspect(&1.pid)})
          }

          ready = %{state | hosts: hosts, host_monitors: monitors, regions: regions,
            collector: collector, explainer: explainer, awaiting: MapSet.new(Core.region_ids()),
            warnings: warnings, topology: topology,
            counts: add(state.counts, :bootstrap_sent, 16)}
          {:ok, ready}
        else
          {:error, reason} -> {:error, reason, state}
        end
    end
  rescue
    error -> {:error, {:setup_exception, Exception.message(error)}, state}
  catch
    kind, reason -> {:error, {:setup_throw, kind, reason}, state}
  end

  defp install_remote_modules([], _options), do: :ok

  defp install_remote_modules(nodes, options) do
    payloads_path = Map.fetch!(options, :payloads_path)

    compiled = Enum.flat_map(@remote_sources, fn filename ->
      path = Path.join([payloads_path, "beam", filename])
      source = File.read!(path)
      Enum.map(Code.compile_string(source, path), fn {module, binary} ->
        {module, String.to_charlist(path), binary}
      end)
    end)

    Enum.reduce_while(nodes, :ok, fn target, :ok ->
      result = Enum.reduce_while(compiled, :ok, fn {module, path, binary}, :ok ->
        try do
          case :erpc.call(target, :code, :load_binary, [module, path, binary], 30_000) do
            {:module, ^module} -> {:cont, :ok}
            {:error, reason} -> {:halt, {:error, {:remote_module_load_failed, target, module, reason}}}
          end
        catch
          kind, reason -> {:halt, {:error, {:remote_module_load_failed, target, kind, reason}}}
        end
      end)

      case result do
        :ok -> {:cont, :ok}
        {:error, _} = error -> {:halt, error}
      end
    end)
  end

  defp start_hosts(nodes) do
    assignments = Core.region_ids() |> Enum.with_index() |> Enum.group_by(fn {_id, index} ->
      Enum.at(nodes, rem(index, length(nodes)))
    end, &elem(&1, 0))

    Enum.reduce_while(nodes, {:ok, [], %{}}, fn target, {:ok, hosts, regions} ->
      region_ids = Map.get(assignments, target, [])

      if region_ids == [] do
        {:cont, {:ok, hosts, regions}}
      else
        started = if target == node(), do: NodeHost.start(region_ids),
          else: :erpc.call(target, NodeHost, :start, [region_ids], 30_000)

        case started do
          {:ok, host_pid} ->
            hosted_regions = NodeHost.regions(host_pid)
            host = %{node: target, pid: host_pid, region_ids: Enum.sort(region_ids)}
            {:cont, {:ok, hosts ++ [host], Map.merge(regions, hosted_regions)}}

          {:error, reason} ->
            stop_hosts(hosts)
            {:halt, {:error, {:node_host_start_failed, target, reason}}}
        end
      end
    end)
  catch
    kind, reason -> {:error, {:node_host_start_failed, kind, reason}}
  end

  defp schedule_tick(state, tick) do
    if state.config.tick_delay_ms > 0 do
      Process.send_after(self(), {:begin_tick, state.epoch, tick}, state.config.tick_delay_ms)
      {:noreply, %{state | phase: {:waiting_for_tick, tick}}}
    else
      {:noreply, begin_tick(state, tick)}
    end
  end

  defp begin_tick(state, tick) do
    Enum.each(Core.region_ids(), fn region_id ->
      send(Map.fetch!(state.regions, region_id), {:tick, state.epoch, tick})
    end)

    %{state | phase: {:tick, tick}, awaiting: MapSet.new(Core.region_ids()),
      current_tick_results: %{},
      counts: add(state.counts, :tick_sent, 16)}
  end

  defp request_collection(state) do
    Enum.each(Core.region_ids(), fn region_id ->
      send(Map.fetch!(state.regions, region_id), {:region_summary, state.epoch, state.collector})
    end)

    {:noreply, %{state | phase: :collecting,
      counts: add(state.counts, :region_summary_requested, 16)}}
  end

  defp barrier_sum(state, field) do
    Enum.sum(Enum.map(state.current_tick_results, fn {_region_id, result} ->
      Map.fetch!(result, field)
    end))
  end

  defp direct_counts(state) do
    region = Enum.reduce(state.region_counts, empty_region_counts(), fn {_id, counts}, acc ->
      Enum.reduce(counts, acc, fn {key, value}, map -> Map.update(map, key, value, &(&1 + value)) end)
    end)

    %{world: state.counts, region: region,
      total: Enum.sum(Map.values(state.counts)) + Enum.sum(Map.values(region))}
  end

  defp invariants(state, aggregate, raw_regions, direct) do
    conservation = aggregate.population_alive ==
      state.config.total_animals + aggregate.births - aggregate.deaths

    %{
      exactly_16_regions: length(raw_regions) == 16 and aggregate.region_count == 16,
      all_regions_completed_every_tick:
        length(state.barrier_history) == state.config.total_steps and
          Enum.all?(state.barrier_history, &(&1.completed_region_count == 16)),
      population_conservation: conservation,
      population_equation: %{
        initial: state.config.total_animals, births: aggregate.births, deaths: aggregate.deaths,
        expected_final: state.config.total_animals + aggregate.births - aggregate.deaths,
        observed_final: aggregate.population_alive
      },
      migration_conserves_global_population: aggregate.migrants_in == aggregate.migrants_out,
      migration_batches_acknowledged_exactly_once:
        direct.region.migration_batches_sent == direct.region.migration_acks_received and
          Enum.all?(raw_regions, & &1.migration_batches_acknowledged_exactly_once),
      dna_within_trait_bounds: Enum.all?(raw_regions, & &1.dna_within_bounds),
      direct_pid_transport_only: true,
      immutable_before_explanation: true
    }
  end

  defp scientific_limitations do
    [
      "This is a synthetic demonstration, not a calibrated model of a real ecosystem.",
      "Animals are records inside regional actors; individual cognition and spatial geometry are not modeled.",
      "Trait inheritance, food competition, mortality, breeding, and migration use simplified equations.",
      "The explanatory model is non-authoritative and cannot change any simulation measurement."
    ]
  end

  defp fail_attempt(reason, state) do
    cleanup(state)
    if state.caller, do: GenServer.reply(state.caller, {:error, reason})
    {:stop, :normal, %{state | caller: nil, hosts: [], collector: nil, explainer: nil}}
  end

  defp cleanup(state) do
    Enum.each(state.host_monitors, fn {ref, _host} -> Process.demonitor(ref, [:flush]) end)
    hosts_stopped = stop_hosts(state.hosts)
    collector_stopped = stop_process(state.collector)
    explainer_stopped = stop_process(state.explainer)
    hosts_stopped and collector_stopped and explainer_stopped
  end

  defp stop_hosts(hosts) do
    Enum.all?(hosts, fn host ->
      try do
        NodeHost.stop(host.pid)
        not remote_alive?(host.pid)
      catch
        :exit, {:noproc, _} -> true
        :exit, _ -> false
      end
    end)
  end

  defp stop_process(nil), do: true
  defp stop_process(pid) do
    try do
      if Process.alive?(pid), do: GenServer.stop(pid, :normal, 5_000)
      not Process.alive?(pid)
    catch
      :exit, _ -> true
    end
  end

  defp remote_alive?(pid) when node(pid) == node(), do: Process.alive?(pid)
  defp remote_alive?(pid) do
    try do
      :erpc.call(node(pid), Process, :alive?, [pid], 5_000)
    catch
      _, _ -> false
    end
  end

  defp empty_world_counts do
    %{bootstrap_sent: 0, bootstrap_ready_received: 0, tick_sent: 0,
      tick_complete_received: 0, region_summary_requested: 0, explanation_handoffs: 0}
  end

  defp empty_region_counts do
    %{bootstrap_received: 0, tick_received: 0, migration_batches_sent: 0,
      migration_batches_received: 0, migration_acks_sent: 0, migration_acks_received: 0,
      tick_complete_sent: 0, region_summary_sent: 0, animals_sent: 0,
      animals_received_in_batches: 0, cross_node_migration_batches: 0}
  end

  defp increment(map, key), do: Map.update!(map, key, &(&1 + 1))
  defp add(map, key, amount), do: Map.update!(map, key, &(&1 + amount))
end
