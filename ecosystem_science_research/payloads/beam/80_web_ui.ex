defmodule MnBlueprints.EcosystemScience.V1.WebUI do
  @moduledoc false

  @placeholder "__ECOSYSTEM_UI_DATA__"

  def write!(payloads_path, run_dir, run_id, blueprint_id, data) do
    template_path = Path.join([payloads_path, "web", "index.html"])
    template = File.read!(template_path)
    encoded = data |> Jason.encode!() |> escape_script_text()
    html = String.replace(template, @placeholder, encoded)

    if html == template or String.contains?(html, @placeholder) do
      raise "ecosystem web UI template placeholder was not replaced"
    end

    web_dir = Path.join(run_dir, "web")
    index_path = Path.join(web_dir, "index.html")
    handle_path = Path.join(run_dir, "web_ui.json")
    File.mkdir_p!(web_dir)

    handle = %{
      "enabled" => true,
      "kind" => "output",
      "adapter" => "static_html",
      "status" => "available",
      "url" => file_url(index_path),
      "path" => index_path,
      "run_id" => run_id,
      "run_dir" => run_dir,
      "title" => "Ecosystem Simulation Replay",
      "metadata" => %{
        "blueprint_id" => blueprint_id,
        "data_mode" => "embedded",
        "schema_version" => "mn.ecosystem.visualization.v1"
      }
    }

    atomic_write!(index_path, html)
    atomic_write!(handle_path, Jason.encode_to_iodata!(handle, pretty: true))
    {:ok, handle, index_path, handle_path}
  end

  defp escape_script_text(json) do
    json
    |> String.replace("<", "\\u003c")
    |> String.replace(">", "\\u003e")
    |> String.replace("&", "\\u0026")
  end

  defp file_url(path) do
    URI.to_string(%URI{scheme: "file", path: Path.expand(path)})
  end

  defp atomic_write!(path, content) do
    temporary = path <> ".tmp-" <> Integer.to_string(System.unique_integer([:positive]))
    File.write!(temporary, content)
    File.rename!(temporary, path)
  end
end
