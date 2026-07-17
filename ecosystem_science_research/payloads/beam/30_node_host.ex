defmodule MnBlueprints.EcosystemScience.V1.NodeHost do
  @moduledoc false
  use GenServer

  alias MnBlueprints.EcosystemScience.V1.RegionActor

  # Deliberately unlinked from the short-lived RPC worker that invokes this function.
  def start(region_ids), do: GenServer.start(__MODULE__, region_ids)
  def regions(pid), do: GenServer.call(pid, :regions, 15_000)
  def stop(pid), do: GenServer.stop(pid, :normal, 15_000)

  @impl true
  def init(region_ids) do
    Process.flag(:trap_exit, true)

    with {:ok, regions} <- start_regions(region_ids, %{}) do
      {:ok, %{regions: regions}}
    end
  end

  @impl true
  def handle_call(:regions, _from, state), do: {:reply, state.regions, state}

  @impl true
  def handle_info({:EXIT, pid, reason}, state) do
    case Enum.find(state.regions, fn {_region_id, region_pid} -> region_pid == pid end) do
      nil -> {:noreply, state}
      {region_id, _pid} -> {:stop, {:region_actor_exit, region_id, reason}, state}
    end
  end

  @impl true
  def terminate(_reason, state) do
    Enum.each(state.regions, fn {_id, pid} ->
      if Process.alive?(pid), do: GenServer.stop(pid, :normal, 5_000)
    end)

    :ok
  end

  defp start_regions([], regions), do: {:ok, regions}

  defp start_regions([region_id | rest], regions) do
    case RegionActor.start_link(region_id) do
      {:ok, pid} -> start_regions(rest, Map.put(regions, region_id, pid))
      {:error, reason} -> {:stop, {:region_start_failed, region_id, reason}}
    end
  end
end
