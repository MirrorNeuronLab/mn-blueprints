defmodule MirrorNeuron.Skills.SlackCommunicateSkill do
  require Logger

  @default_api_url "https://slack.com/api/chat.postMessage"

  def send_message(text, opts \\ [])

  def send_message(text, opts) when is_binary(text) do
    :inets.start()
    :ssl.start()

    token = option_or_env(opts, :token, ["MIRROR_NEURON_SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN"])
    channel = option_or_env(opts, :channel, ["MIRROR_NEURON_SLACK_DEFAULT_CHANNEL", "SLACK_DEFAULT_CHANNEL"])
    api_url = option_or_env(opts, :api_url, ["MIRROR_NEURON_SLACK_API_BASE_URL", "SLACK_API_BASE_URL"], @default_api_url)

    cond do
      blank?(token) ->
        {:skipped, %{reason: "missing_slack_bot_token", channel: channel}}

      blank?(channel) ->
        {:skipped, %{reason: "missing_slack_channel", channel: channel}}

      true ->
        post_message(api_url, token, channel, text)
    end
  end

  def send_message(_text, _opts), do: {:error, %{reason: "invalid_text"}}

  def enabled?(config \\ %{}) do
    Map.get(config, "slack_enabled", false) or truthy?(System.get_env("FINANCIAL_MARKET_ADVISOR_SLACK_ENABLED"))
  end

  defp post_message(api_url, token, channel, text) do
    headers = [
      {~c"Authorization", to_charlist("Bearer #{token}")},
      {~c"Content-Type", ~c"application/json"}
    ]

    body = Jason.encode!(%{"channel" => channel, "text" => text})

    case :httpc.request(:post, {to_charlist(api_url), headers, ~c"application/json", body}, [], []) do
      {:ok, {{_, 200, _}, _, response_body}} ->
        parse_success_response(response_body, channel)

      {:ok, {{_, status, _}, _, response_body}} ->
        {:error, %{reason: "slack_http_error", status: status, channel: channel, body: to_string(response_body)}}

      {:error, reason} ->
        {:error, %{reason: "slack_request_failed", channel: channel, error: inspect(reason)}}
    end
  end

  defp parse_success_response(response_body, channel) do
    body = to_string(response_body)

    case Jason.decode(body) do
      {:ok, %{"ok" => true} = payload} ->
        {:ok, %{channel: channel, ts: payload["ts"], message: payload["message"]}}

      {:ok, %{"ok" => false, "error" => error}} ->
        {:error, %{reason: "slack_api_error", channel: channel, error: error}}

      {:ok, payload} ->
        {:ok, %{channel: channel, response: payload}}

      {:error, _} ->
        {:ok, %{channel: channel, response: body}}
    end
  end

  defp option_or_env(opts, key, env_names, default \\ "") do
    option_value =
      opts
      |> Keyword.get(key, "")
      |> to_string()
      |> String.trim()

    if option_value != "" do
      option_value
    else
      env_names
      |> Enum.map(&(System.get_env(&1) || ""))
      |> Enum.map(&String.trim/1)
      |> Enum.find(default, &(&1 != ""))
    end
  end

  defp blank?(value), do: is_nil(value) or String.trim(to_string(value)) == ""

  defp truthy?(value) when is_binary(value) do
    value |> String.downcase() |> then(&(&1 in ["1", "true", "yes", "on"]))
  end

  defp truthy?(_), do: false
end
