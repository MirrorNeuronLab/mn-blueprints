defmodule MnBlueprints.EcosystemScience.V1.RegionActor do
  @moduledoc false
  use GenServer

  alias MnBlueprints.EcosystemScience.V1.Core

  def start_link(region_id), do: GenServer.start_link(__MODULE__, region_id)

  @impl true
  def init(region_id) do
    {:ok,
     %{
       region_id: region_id,
       epoch: nil,
       world: nil,
       peers: %{},
       config: nil,
       simulation: nil,
       seen_batches: MapSet.new(),
       pending_acks: MapSet.new(),
       pending_tick: nil,
       counts: empty_counts()
     }}
  end

  @impl true
  def handle_info({:bootstrap, epoch, bootstrap, config, peers, world}, state) do
    simulation = Core.init_region_state(state.region_id, bootstrap)
    send(world, {:bootstrap_ready, epoch, state.region_id, self(), node()})

    {:noreply,
     %{
       state
       | epoch: epoch,
         world: world,
         peers: peers,
         config: config,
         simulation: simulation,
         counts: increment(state.counts, :bootstrap_received)
     }}
  end

  def handle_info({:tick, epoch, tick}, %{epoch: epoch, simulation: simulation} = state)
      when tick == simulation.tick + 1 do
    config =
      if tick > state.config.total_steps - 2 do
        %{state.config | migration_rate: 0.0}
      else
        state.config
      end

    {simulation, arrivals, births, deaths, payloads, outgoing} =
      Core.process_tick(simulation, config, tick)

    {pending, counts} =
      payloads
      |> Enum.sort_by(&elem(&1, 0))
      |> Enum.reduce({MapSet.new(), increment(state.counts, :tick_received)}, fn
        {destination, animals}, {pending, counts} ->
          destination_pid = Map.fetch!(state.peers, destination)
          batch_id = {epoch, tick, state.region_id, destination}

          send(
            destination_pid,
            {:migration_batch, epoch, batch_id, tick + 2, state.region_id, animals, self()}
          )

          counts =
            counts
            |> increment(:migration_batches_sent)
            |> add(:animals_sent, length(animals))
            |> maybe_cross_node(destination_pid)

          {MapSet.put(pending, batch_id), counts}
      end)

    tick_result = %{
      tick: tick,
      arrivals: arrivals,
      births: births,
      deaths: deaths,
      outgoing: outgoing,
      migration_batches: MapSet.size(pending)
    }

    next = %{
      state
      | simulation: simulation,
        pending_acks: pending,
        pending_tick: tick_result,
        counts: counts
    }

    if MapSet.size(pending) == 0, do: complete_tick(next), else: {:noreply, next}
  end

  def handle_info(
        {:migration_batch, epoch, batch_id, arrival_tick, _source_region, animals, source_pid},
        %{epoch: epoch} = state
      ) do
    if MapSet.member?(state.seen_batches, batch_id) do
      {:noreply, state}
    else
      simulation = Core.stage_migrants(state.simulation, arrival_tick, animals)
      send(source_pid, {:migration_ack, epoch, batch_id, state.region_id})

      counts =
        state.counts
        |> increment(:migration_batches_received)
        |> increment(:migration_acks_sent)
        |> add(:animals_received_in_batches, length(animals))

      {:noreply,
       %{
         state
         | simulation: simulation,
           seen_batches: MapSet.put(state.seen_batches, batch_id),
           counts: counts
       }}
    end
  end

  def handle_info({:migration_ack, epoch, batch_id, _destination}, %{epoch: epoch} = state) do
    if MapSet.member?(state.pending_acks, batch_id) do
      pending = MapSet.delete(state.pending_acks, batch_id)
      next = %{state | pending_acks: pending, counts: increment(state.counts, :migration_acks_received)}
      if MapSet.size(pending) == 0, do: complete_tick(next), else: {:noreply, next}
    else
      {:noreply, state}
    end
  end

  def handle_info({:region_summary, epoch, collector}, %{epoch: epoch} = state) do
    summary =
      state.simulation
      |> Core.region_summary(Atom.to_string(node()), state.config.local_top_k)
      |> Map.put(:direct_message_counts, increment(state.counts, :region_summary_sent))
      |> Map.put(:migration_batches_acknowledged_exactly_once,
        state.counts.migration_batches_sent == state.counts.migration_acks_received
      )

    send(collector, {:region_summary, epoch, state.region_id, summary})
    {:noreply, %{state | counts: summary.direct_message_counts}}
  end

  # All protocol messages carry epochs. Old-attempt traffic is intentionally ignored.
  def handle_info(_stale_or_unknown, state), do: {:noreply, state}

  defp complete_tick(state) do
    counts = increment(state.counts, :tick_complete_sent)
    send(state.world, {:tick_complete, state.epoch, state.region_id, state.pending_tick, counts})

    {:noreply,
     %{state | pending_acks: MapSet.new(), pending_tick: nil, counts: counts}}
  end

  defp empty_counts do
    %{
      bootstrap_received: 0,
      tick_received: 0,
      migration_batches_sent: 0,
      migration_batches_received: 0,
      migration_acks_sent: 0,
      migration_acks_received: 0,
      tick_complete_sent: 0,
      region_summary_sent: 0,
      animals_sent: 0,
      animals_received_in_batches: 0,
      cross_node_migration_batches: 0
    }
  end

  defp increment(map, key), do: Map.update!(map, key, &(&1 + 1))
  defp add(map, key, amount), do: Map.update!(map, key, &(&1 + amount))

  defp maybe_cross_node(counts, destination_pid) do
    if node(destination_pid) != node(), do: increment(counts, :cross_node_migration_batches), else: counts
  end
end
