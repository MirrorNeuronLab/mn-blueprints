defmodule MnBlueprints.EcosystemScience.V1.FinalPublisherAgent do
  use MirrorNeuron.AgentTemplate

  @impl true
  def init(_node), do: {:ok, %{published: false}}

  @impl true
  def handle_message(_message, %{published: true} = state, _context),
    do: {:ok, state, []}

  def handle_message(message, state, _context) do
    final_artifact = payload(message) || %{}

    {:ok, %{state | published: true},
     [
       {:emit, "final_result", final_artifact},
       {:complete_step, final_artifact},
       {:event, :run_completed, %{"status" => "complete"}}
     ]}
  end

  @impl true
  def recover(state, _context), do: {:ok, state, []}
  @impl true
  def snapshot_state(state), do: state
  @impl true
  def restore_state(snapshot), do: {:ok, snapshot}
  @impl true
  def inspect_state(state), do: state
end
