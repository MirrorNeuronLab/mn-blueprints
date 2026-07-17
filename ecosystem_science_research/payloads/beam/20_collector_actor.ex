defmodule MnBlueprints.EcosystemScience.V1.CollectorActor do
  @moduledoc false
  use GenServer

  alias MnBlueprints.EcosystemScience.V1.Core

  def start, do: GenServer.start(__MODULE__, :ok)

  @impl true
  def init(:ok), do: {:ok, %{epoch: nil, world: nil, expected: 16, summaries: %{}}}

  @impl true
  def handle_info({:collect, epoch, world, expected}, state) do
    {:noreply, %{state | epoch: epoch, world: world, expected: expected, summaries: %{}}}
  end

  def handle_info({:region_summary, epoch, region_id, summary}, %{epoch: epoch} = state) do
    summaries = Map.put_new(state.summaries, region_id, summary)
    next = %{state | summaries: summaries}

    if map_size(summaries) == state.expected do
      ordered = summaries |> Map.values() |> Enum.sort_by(& &1.region_id)
      aggregate = Core.summarize_regions(ordered)
      send(state.world, {:collection_complete, epoch, aggregate, ordered})
      {:noreply, next}
    else
      {:noreply, next}
    end
  end

  def handle_info(_stale_or_unknown, state), do: {:noreply, state}
end
