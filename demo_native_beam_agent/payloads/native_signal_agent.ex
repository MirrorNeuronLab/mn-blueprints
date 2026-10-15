defmodule MnBlueprints.NativeSignalAgent do
  use MirrorNeuron.AgentTemplate

  @impl true
  def init(node),
    do:
      {:ok,
       %{
         mode: Map.get(node.config, "mode", "classify"),
         emit_type: Map.get(node.config, "emit_type", "native_done"),
         count: 0
       }}

  @impl true
  def handle_message(message, state, _context) do
    payload = payload(message) || %{}
    values = Map.get(payload, "signals", [12, 71, 38])
    classes = Enum.map(values, fn value -> if value >= 60, do: "alert", else: "normal" end)
    result = %{"runner" => "beam_native", "signals" => values, "classes" => classes, "mode" => state.mode}
    next_state = %{state | count: state.count + 1}
    {:ok, next_state,
     [
       {:emit, state.emit_type, result},
       {:complete_step, result},
       {:event, :native_signal_classified, Map.merge(result, %{"message" => "Classified #{length(values)} signals; #{Enum.count(classes, &(&1 == "alert"))} require attention", "owner_blueprint" => "demo_native_beam_agent", "activity_kind" => "result"})}
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
