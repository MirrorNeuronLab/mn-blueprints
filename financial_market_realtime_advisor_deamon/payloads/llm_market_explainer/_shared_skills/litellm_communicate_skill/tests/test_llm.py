from mn_litellm_communicate_skill import LLMConfig, completion_json, completion_text, resolve_config


def test_resolve_config_defaults_to_local_ollama(monkeypatch):
    for key in [
        "LITELLM_MODEL",
        "LITELLM_API_BASE",
        "LITELLM_API_KEY",
        "LITELLM_TIMEOUT_SECONDS",
        "LITELLM_MAX_TOKENS",
        "LITELLM_NUM_RETRIES",
        "LITELLM_RETRY_BACKOFF_SECONDS",
    ]:
        monkeypatch.delenv(key, raising=False)

    config = resolve_config()

    assert config.model == "ollama/gemma4:latest"
    assert config.api_base == "http://localhost:11434"
    assert config.api_key == ""


def test_completion_text_uses_fallback_when_provider_unavailable():
    config = LLMConfig(
        model="ollama/gemma4:latest",
        api_base="http://127.0.0.1:9",
        api_key="",
        timeout_seconds=0.01,
        max_tokens=10,
        num_retries=0,
        retry_backoff_seconds=0,
    )

    assert completion_text("system", "user", fallback="fallback", config=config) == "fallback"


def test_completion_json_uses_fallback_when_provider_unavailable():
    config = LLMConfig(
        model="ollama/gemma4:latest",
        api_base="http://127.0.0.1:9",
        api_key="",
        timeout_seconds=0.01,
        max_tokens=10,
        num_retries=0,
        retry_backoff_seconds=0,
    )

    assert completion_json("system", "user", fallback={"ok": True}, config=config) == {"ok": True}
