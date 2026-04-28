from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_plan(payload: dict[str, Any]) -> dict[str, Any]:
    sandbox_stdout = str(payload.get("sandbox", {}).get("stdout") or "").strip()
    if sandbox_stdout:
        try:
            return json.loads(sandbox_stdout)
        except json.JSONDecodeError:
            pass
    if "input" in payload:
        return payload["input"]
    return payload


def load_input_plan() -> dict[str, Any]:
    payload = json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())
    return get_plan(payload)


def bundle_asset_dir(name: str) -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / name
        if candidate.exists():
            return candidate
    return current.parents[2] / name


def bundle_templates_dir() -> Path:
    return bundle_asset_dir("templates")


def bundle_input_dir() -> Path:
    return bundle_asset_dir("input")


def _read_input_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    return payload if isinstance(payload, dict) else {}


def read_business_context() -> str:
    return str(load_input_manifest().get("business_context", ""))


def read_email_rules() -> dict[str, Any]:
    return dict(load_input_manifest().get("email_rules", {})) or {
        "minimum_minutes_between_emails": 5
    }


def read_delivery_settings() -> dict[str, Any]:
    return dict(load_input_manifest().get("delivery", {}))


def load_input_manifest() -> dict[str, Any]:
    input_dir = bundle_input_dir()
    manifest = _read_input_json(input_dir / "manifest.json")
    strategy = _read_input_json(input_dir / "strategy.json")
    knowledge = _read_input_json(input_dir / "knowledge.json")
    merged = dict(manifest)
    if "business_context" in strategy:
        merged["business_context"] = strategy["business_context"]
    if "email_rules" in strategy:
        merged["email_rules"] = strategy["email_rules"]
    if "delivery" in strategy:
        merged["delivery"] = strategy["delivery"]
    merged_knowledge = dict(knowledge)
    campaign_playbooks = strategy.get("campaign_playbooks", {})
    if isinstance(campaign_playbooks, dict):
        merged_knowledge["campaign_playbooks"] = campaign_playbooks
    merged["knowledge"] = merged_knowledge
    return merged


def load_knowledge_section(section_name: str) -> dict[str, Any]:
    knowledge = load_input_manifest().get("knowledge", {})
    if not isinstance(knowledge, dict):
        return {}
    section = knowledge.get(section_name, {})
    return section if isinstance(section, dict) else {}


def load_template_library() -> dict[str, dict[str, Any]]:
    library: dict[str, dict[str, Any]] = {}
    template_dirs = [bundle_templates_dir(), bundle_input_dir() / "templates"]
    for templates_dir in template_dirs:
        if not templates_dir.exists():
            continue
        for path in sorted(templates_dir.glob("*.json")):
            payload = json.loads(path.read_text())
            if isinstance(payload, dict) and payload.get("template_id"):
                library[str(payload["template_id"])] = payload
    return library


def db_connect() -> sqlite3.Connection:
    connection_string = os.environ.get("SYNAPTIC_DB_CONNECTION", "").strip()
    if connection_string:
        if not connection_string.startswith("sqlite:///"):
            raise RuntimeError(
                "Unsupported database connection string. Synaptic currently supports sqlite:///... only."
            )
        target = connection_string[len("sqlite:///") :]
    else:
        target = os.environ["SYNAPTIC_DB_PATH"]
    conn = sqlite3.connect(target, timeout=30)
    conn.row_factory = sqlite3.Row
    ensure_db_schema(conn)
    return conn


def ensure_db_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS email_drafts (
            draft_id TEXT PRIMARY KEY,
            customer_id TEXT,
            runtime_job_id TEXT,
            status TEXT,
            subject TEXT,
            preview_text TEXT,
            body_text TEXT,
            html_body TEXT,
            scheduled_send_at TEXT,
            prepared_at TEXT,
            provider_id TEXT,
            sent_at TEXT,
            from_email TEXT,
            thread_message_id TEXT,
            in_reply_to_message_id TEXT,
            references_message_ids_json TEXT,
            source_payload_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS customer_marketing_activity (
            activity_id TEXT PRIMARY KEY,
            customer_id TEXT,
            summary TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_logs (
            runtime_job_id TEXT,
            agent_id TEXT,
            level TEXT,
            message TEXT,
            details_json TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()


def recent_activities(customer_id: str, limit: int = 5) -> list[dict[str, Any]]:
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT summary, created_at
            FROM customer_marketing_activity
            WHERE customer_id = ?
            ORDER BY created_at DESC, activity_id DESC
            LIMIT ?
            """,
            (customer_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def latest_sent_draft(customer_id: str) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM email_drafts
            WHERE customer_id = ? AND status = 'sent'
            ORDER BY sent_at DESC, prepared_at DESC
            LIMIT 1
            """,
            (customer_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def pending_ready_draft(customer_id: str) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM email_drafts
            WHERE customer_id = ? AND status = 'ready'
            ORDER BY prepared_at DESC
            LIMIT 1
            """,
            (customer_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def save_ready_draft(
    *,
    draft_id: str,
    customer_id: str,
    runtime_job_id: str | None,
    subject: str,
    preview_text: str,
    body_text: str,
    html_body: str,
    scheduled_send_at: str,
    source_payload: dict[str, Any],
) -> dict[str, Any]:
    prepared_at = utc_now()
    reply_context = dict(source_payload.get("reply_context") or {})
    references = list(reply_context.get("references_message_ids") or [])
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO email_drafts (
                draft_id,
                customer_id,
                runtime_job_id,
                status,
                subject,
                preview_text,
                body_text,
                html_body,
                scheduled_send_at,
                prepared_at,
                from_email,
                thread_message_id,
                in_reply_to_message_id,
                references_message_ids_json,
                source_payload_json
            ) VALUES (?, ?, ?, 'ready', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                customer_id,
                runtime_job_id,
                subject,
                preview_text,
                body_text,
                html_body,
                scheduled_send_at,
                prepared_at,
                str(reply_context.get("reply_from_email") or ""),
                str(reply_context.get("thread_message_id") or ""),
                str(reply_context.get("in_reply_to_message_id") or ""),
                json.dumps(references, sort_keys=True),
                json.dumps(source_payload, sort_keys=True),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM email_drafts WHERE draft_id = ?",
            (draft_id,),
        ).fetchone()
    return dict(row)


def mark_draft_sent(draft_id: str, provider_id: str | None) -> dict[str, Any] | None:
    sent_at = utc_now()
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE email_drafts
            SET status = 'sent',
                provider_id = ?,
                sent_at = ?
            WHERE draft_id = ?
            """,
            (provider_id, sent_at, draft_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM email_drafts WHERE draft_id = ?",
            (draft_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def add_marketing_activity(customer_id: str, summary: str) -> None:
    import uuid

    timestamp = utc_now().replace('-', '').replace(':', '').replace('+00:00', 'z').lower()
    activity_id = f"activity_{timestamp}_{uuid.uuid4().hex[:8]}"
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO customer_marketing_activity (
                activity_id,
                customer_id,
                summary,
                created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (activity_id, customer_id, summary, utc_now()),
        )
        conn.commit()


def log_agent(
    runtime_job_id: str | None,
    agent_id: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    if not runtime_job_id:
        return
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_logs (
                runtime_job_id,
                agent_id,
                level,
                message,
                details_json,
                created_at
            ) VALUES (?, ?, 'info', ?, ?, ?)
            """,
            (
                runtime_job_id,
                agent_id,
                message,
                json.dumps(details or {}, sort_keys=True),
                utc_now(),
            ),
        )
        conn.commit()


def _resolve_litellm_model(profile: str = "primary") -> str:
    profile_prefix = "PRIMARY_" if profile == "primary" else "SECONDARY_"
    model = (
        os.environ.get(f"{profile_prefix}LITELLM_MODEL")
        or os.environ.get(f"{profile_prefix}LLM_MODEL")
        or (
            os.environ.get("LITELLM_MODEL")
            if profile == "primary"
            else None
        )
        or (
            os.environ.get("LLM_MODEL")
            if profile == "primary"
            else None
        )
        or (
            os.environ.get("GEMINI_MODEL")
            if profile == "primary"
            else None
        )
        or "gemini/gemini-2.5-flash"
    ).strip()
    if model.startswith("gemini/") or model.startswith("ollama/") or "/" in model:
        return model
    ollama_base = (
        os.environ.get(f"{profile_prefix}LITELLM_API_BASE")
        or os.environ.get("OLLAMA_API_BASE")
    )
    if ollama_base:
        return f"ollama/{model}"
    return f"gemini/{model}"


def _resolve_litellm_api_key(model: str, profile: str = "primary") -> str:
    profile_prefix = "PRIMARY_" if profile == "primary" else "SECONDARY_"
    return (
        os.environ.get(f"{profile_prefix}LITELLM_API_KEY")
        or os.environ.get(f"{profile_prefix}LLM_API_KEY")
        or (
            os.environ.get("LITELLM_API_KEY")
            if profile == "primary"
            else None
        )
        or (
            os.environ.get("LLM_API_KEY")
            if profile == "primary"
            else None
        )
        or (
            os.environ.get("GEMINI_API_KEY", "")
            if model.startswith("gemini/")
            else ""
        )
    ).strip()


def _resolve_litellm_api_base(model: str, profile: str = "primary") -> str | None:
    profile_prefix = "PRIMARY_" if profile == "primary" else "SECONDARY_"
    api_base = (
        os.environ.get(f"{profile_prefix}LITELLM_API_BASE")
        or os.environ.get(f"{profile_prefix}LLM_API_BASE")
        or (
            os.environ.get("LITELLM_API_BASE")
            if profile == "primary"
            else None
        )
        or (
            os.environ.get("LLM_API_BASE")
            if profile == "primary"
            else None
        )
        or (
            os.environ.get("GEMINI_API_BASE_URL")
            if model.startswith("gemini/")
            else None
        )
        or (
            os.environ.get("OLLAMA_API_BASE")
            if model.startswith("ollama/")
            else None
        )
    )
    if api_base is None:
        return None
    value = api_base.strip()
    if not value:
        return None
    if model.startswith("gemini/"):
        for suffix in ("/v1beta/models", "/v1/models", "/models"):
            if value.endswith(suffix):
                return value[: -len(suffix)] or None
    if model.startswith("ollama/"):
        for suffix in ("/v1/chat/completions", "/v1"):
            if value.endswith(suffix):
                return value[: -len(suffix)] or None
    return value


def completion_json(
    system_prompt: str, user_prompt: str, *, profile: str = "primary"
) -> dict[str, Any] | None:
    model = _resolve_litellm_model(profile)
    api_key = _resolve_litellm_api_key(model, profile)
    api_base = _resolve_litellm_api_base(model, profile)

    if not api_key and not model.startswith("ollama/"):
        return None

    try:
        import litellm
        from litellm import completion
    except ImportError:
        return None

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    request_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": 800,
    }
    if api_key:
        request_kwargs["api_key"] = api_key
    if api_base:
        request_kwargs["api_base"] = api_base

    supported_params: set[str] = set()
    try:
        supported_params = set(litellm.get_supported_openai_params(model=model) or [])
    except Exception:
        supported_params = set()

    if "response_format" in supported_params:
        request_kwargs["response_format"] = {"type": "json_object"}
    if model.startswith("ollama/"):
        request_kwargs["format"] = "json"

    try:
        response = completion(**request_kwargs)
    except Exception as exc:
        return None

    try:
        finish_reason = response.choices[0].finish_reason
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected LiteLLM response format: {response}") from exc

    if finish_reason == "length":
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Some providers return truncated or non-strict JSON even when asked for JSON.
        # In that case we fall back to the deterministic local generator instead of
        # failing the whole agent pipeline.
        return None
    except Exception as exc:
        raise RuntimeError(f"Unexpected LiteLLM response format: {response}") from exc
