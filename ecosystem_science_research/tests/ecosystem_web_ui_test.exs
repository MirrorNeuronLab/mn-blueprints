ExUnit.start(seed: 0)

blueprint_root = Path.expand("..", __DIR__)
beam_root = Path.join([blueprint_root, "payloads", "beam"])

for file <- ~w(00_core.ex 80_web_ui.ex) do
  Code.require_file(Path.join(beam_root, file))
end

defmodule MnBlueprints.EcosystemScience.V1.WebUITest do
  use ExUnit.Case, async: false

  alias MnBlueprints.EcosystemScience.V1.WebUI

  @payloads Path.expand("../payloads", __DIR__)

  test "writes an embedded static replay and standard handle atomically" do
    run_dir = Path.join(System.tmp_dir!(), "ecosystem-web-ui-#{System.unique_integer([:positive])}")
    on_exit(fn -> File.rm_rf!(run_dir) end)

    data = %{
      "visualization" => %{
        "schema_version" => "mn.ecosystem.visualization.v1",
        "global_timeline" => [%{"tick" => 0, "population" => 1}],
        "regions" => %{}
      },
      "explanation" => %{"summary" => "A </script> safe summary."}
    }

    assert {:ok, handle, index_path, handle_path} =
             WebUI.write!(@payloads, run_dir, "run-test", "ecosystem_science_research", data)

    assert handle["enabled"]
    assert handle["adapter"] == "static_html"
    assert handle["run_id"] == "run-test"
    assert handle["run_dir"] == run_dir
    assert handle["path"] == index_path
    assert handle["url"] == URI.to_string(%URI{scheme: "file", path: Path.expand(index_path)})
    assert File.exists?(index_path)
    assert File.exists?(handle_path)
    assert Path.wildcard(Path.join(run_dir, "**/*.tmp-*")) == []

    html = File.read!(index_path)
    refute html =~ "__ECOSYSTEM_UI_DATA__"
    assert html =~ "\\u003c/script\\u003e"

    [json] = Regex.run(~r/<script id="ecosystem-data" type="application\/json">(.*?)<\/script>/s, html, capture: :all_but_first)
    embedded = Jason.decode!(json)
    assert embedded["visualization"]["schema_version"] == "mn.ecosystem.visualization.v1"
    assert embedded["explanation"]["summary"] == "A </script> safe summary."
    assert Jason.decode!(File.read!(handle_path))["adapter"] == "static_html"
  end
end
