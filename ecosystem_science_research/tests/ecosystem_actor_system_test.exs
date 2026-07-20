ExUnit.start(seed: 0)

blueprint_root = Path.expand("..", __DIR__)
beam_root = Path.join([blueprint_root, "payloads", "beam"])

for file <- ~w(00_core.ex 10_region_actor.ex 20_collector_actor.ex 30_node_host.ex 40_explainer_actor.ex 50_world_actor.ex) do
  Code.require_file(Path.join(beam_root, file))
end

defmodule MnBlueprints.EcosystemScience.V1.ActorSystemTest do
  use ExUnit.Case, async: false

  alias MnBlueprints.EcosystemScience.V1.WorldActor

  @payloads Path.expand("../payloads", __DIR__)

  defp config(overrides \\ %{}) do
    Map.merge(
      %{
        seed: 517_498_978,
        total_animals: 160,
        duration_seconds: 30,
        tick_seconds: 5,
        total_steps: 6,
        max_food: 420.0,
        food_regen_per_tick: 72.0,
        max_region_population: 40,
        migration_rate: 0.20,
        mutation_rate: 0.05,
        tick_delay_ms: 0,
        local_top_k: 20,
        require_multi_node: false
      },
      overrides
    )
  end

  defp fake_options do
    %{
      payloads_path: @payloads,
      environment: %{
        "MN_LLM_PROVIDER" => "fake",
        "MN_LLM_MODEL" => "fake-deterministic-blueprint-agent"
      },
      llm_mode: "fake"
    }
  end

  test "same seed produces identical scientific output despite actor scheduling" do
    assert {:ok, first} = WorldActor.run(config(), fake_options(), 30_000)
    assert {:ok, second} = WorldActor.run(config(), fake_options(), 30_000)

    assert first.simulation == second.simulation
    assert first.topology.actors_cleaned_up
    assert second.topology.actors_cleaned_up
  end

  test "conservation, barriers, migration acknowledgements, and DNA bounds hold" do
    assert {:ok, result} = WorldActor.run(config(), fake_options(), 30_000)
    invariants = result.simulation.invariants

    assert invariants.exactly_16_regions
    assert invariants.all_regions_completed_every_tick
    assert invariants.population_conservation
    assert invariants.migration_conserves_global_population
    assert invariants.migration_batches_acknowledged_exactly_once
    assert invariants.dna_within_trait_bounds
    assert length(result.simulation.tick_barriers) == 6
    assert Enum.all?(result.simulation.tick_barriers, &(&1.completed_region_count == 16))
    assert result.simulation.migration_batches == result.simulation.migration_acks
    assert result.simulation.births > 0
    assert result.simulation.mutations > 0
    assert length(result.simulation.ecology_timeline) == 7
    assert Enum.map(result.simulation.ecology_timeline, & &1.tick) == Enum.to_list(0..6)
    assert Enum.sum(Enum.map(result.simulation.ecology_timeline, & &1.births)) == result.simulation.births
    assert Enum.sum(Enum.map(result.simulation.ecology_timeline, & &1.deaths)) == result.simulation.deaths
    assert Enum.sum(Enum.map(result.simulation.ecology_timeline, & &1.migrants_in)) == result.simulation.migrants_in
    assert Enum.sum(Enum.map(result.simulation.ecology_timeline, & &1.migrants_out)) == result.simulation.migrants_out

    Enum.each(result.simulation.region_timelines, fn {_region_id, timeline} ->
      assert length(timeline) == 7
      assert Enum.map(timeline, & &1.tick) == Enum.to_list(0..6)
      assert Enum.all?(timeline, &Map.has_key?(&1, :food_ratio))
    end)
  end

  test "one live OpenAI-compatible response explains but cannot mutate the simulation" do
    {server, port} = openai_server()
    on_exit(fn -> Process.exit(server, :kill) end)

    options = %{
      payloads_path: @payloads,
      environment: %{
        "MN_LLM_PROVIDER" => "litellm",
        "MN_LLM_MODEL" => "test-explainer",
        "MN_LLM_API_BASE" => "http://127.0.0.1:#{port}/v1"
      },
      llm_mode: "live",
      llm_timeout_seconds: 5,
      llm_max_tokens: 200
    }

    assert {:ok, result} = WorldActor.run(config(), options, 30_000)
    assert result.llm_usage.mode == "live"
    assert result.llm_usage.requests == 1
    assert result.explanation["summary"] == "Synthetic live explanation."
    assert result.simulation.invariants.population_conservation
  end

  test "unavailable model succeeds with explicit deterministic fallback" do
    options = %{
      payloads_path: @payloads,
      environment: %{
        "MN_LLM_PROVIDER" => "litellm",
        "MN_LLM_MODEL" => "unavailable-test-model",
        "MN_LLM_API_BASE" => "http://127.0.0.1:1/v1"
      },
      llm_mode: "live",
      llm_timeout_seconds: 1,
      llm_max_tokens: 200
    }

    assert {:ok, result} = WorldActor.run(config(), options, 30_000)
    assert result.llm_usage.mode == "fallback"
    assert result.llm_usage.requests == 1
    assert result.warnings != []
    assert result.explanation["generation"]["mode"] == "deterministic"
    assert result.simulation.invariants.population_conservation
  end

  test "two BEAM nodes place regions remotely and exchange migration batches directly" do
    assert Node.alive?(), "run this test with --sname so a peer can join"

    peer_name = String.to_atom("ecosystem_peer_#{System.unique_integer([:positive])}")
    args = Enum.flat_map(:code.get_path(), &[~c"-pa", &1])
    assert {:ok, peer, peer_node} = :peer.start_link(%{name: peer_name, args: args})
    on_exit(fn ->
      try do
        :peer.stop(peer)
      catch
        :exit, _ -> :ok
      end
    end)

    assert {:ok, result} =
             WorldActor.run(config(%{require_multi_node: true}), fake_options(), 30_000)

    assert peer_node in Node.list(:connected)
    assert result.topology.cross_node_region_placement
    assert length(result.topology.connected_nodes) >= 2
    assert result.simulation.cross_node_migration_batches > 0
    assert result.topology.actors_cleaned_up
    refute remote_domain_actors_alive?(peer_node)
  end

  defp openai_server do
    {:ok, listener} =
      :gen_tcp.listen(0, [:binary, packet: :raw, active: false, reuseaddr: true, ip: {127, 0, 0, 1}])

    {:ok, {_address, port}} = :inet.sockname(listener)

    pid = spawn(fn ->
      {:ok, socket} = :gen_tcp.accept(listener)
      {:ok, _request} = :gen_tcp.recv(socket, 0, 5_000)

      content = Jason.encode!(%{
        "summary" => "Synthetic live explanation.",
        "findings" => ["The frozen measurements were explained."],
        "limitations" => ["Synthetic test response."]
      })

      body = Jason.encode!(%{"choices" => [%{"message" => %{"content" => content}}]})
      response = "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: #{byte_size(body)}\r\nconnection: close\r\n\r\n#{body}"
      :ok = :gen_tcp.send(socket, response)
      :gen_tcp.close(socket)
      :gen_tcp.close(listener)
    end)

    {pid, port}
  end

  defp remote_domain_actors_alive?(peer_node) do
    peer_node
    |> :erpc.call(:erlang, :processes, [])
    |> Enum.any?(fn pid ->
      case :erpc.call(peer_node, :erlang, :process_info, [pid, :dictionary]) do
        {:dictionary, dictionary} ->
          case Keyword.get(dictionary, :"$initial_call") do
            {module, _function, _arity} ->
              module in [
                MnBlueprints.EcosystemScience.V1.NodeHost,
                MnBlueprints.EcosystemScience.V1.RegionActor
              ]

            _ ->
              false
          end

        _ ->
          false
      end
    end)
  end
end
