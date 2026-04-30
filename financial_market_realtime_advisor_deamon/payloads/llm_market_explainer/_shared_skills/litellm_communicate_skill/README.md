# LiteLLM Communicate Skill

Shared LLM wrapper for MirrorNeuron blueprints.

The skill uses LiteLLM-style environment variables only:

| Variable | Default | Usage |
| --- | --- | --- |
| `LITELLM_MODEL` | `ollama/gemma4:latest` | Model name passed to LiteLLM or local Ollama fallback. |
| `LITELLM_API_BASE` | `http://localhost:11434` | Provider API base URL. For Ollama, use the Ollama server base. |
| `LITELLM_API_KEY` | unset | Optional provider API key. Not required for local Ollama. |
| `LITELLM_TIMEOUT_SECONDS` | `60` | Request timeout. |
| `LITELLM_MAX_TOKENS` | `800` | Maximum response tokens. |
| `LITELLM_NUM_RETRIES` | `2` | Provider retry count. Passed to LiteLLM when available. |
| `LITELLM_RETRY_BACKOFF_SECONDS` | `1.0` | Exponential retry backoff base for direct HTTP fallbacks. |

Blueprint workers that need at-least-later delivery should keep failed requests in their agent state and retry them on future messages. This skill provides provider timeout/retry behavior; queueing and backpressure policy belong to the caller because each blueprint knows how much pending work is safe.

Python usage:

```python
from mn_litellm_communicate_skill import completion_text, completion_json

text = completion_text("You are concise.", "Explain this signal.")
data = completion_json("Return JSON only.", "Summarize this event.", fallback={"summary": "LLM unavailable"})
```

If the `litellm` package is installed, the skill calls `litellm.completion`.
If not, it can call local Ollama directly for models like `ollama/gemma4:latest`.
