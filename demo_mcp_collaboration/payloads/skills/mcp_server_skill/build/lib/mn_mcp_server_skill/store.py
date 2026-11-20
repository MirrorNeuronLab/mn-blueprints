from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "mn.mcp.job_exchange.v1"
VALID_KINDS = {"status", "knowledge", "result"}
VALID_PUBLICATION_STATES = {"staged", "final"}
SENSITIVE_FIELD_NAMES = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "bearer_token",
    "cookie",
    "password",
    "private_key",
    "refresh_token",
    "secret",
}
DEFAULT_MAX_PAYLOAD_BYTES = 256 * 1024
DEFAULT_MAX_HISTORY = 2_000
DEFAULT_QUERY_LIMIT = 200
MAX_QUERY_LIMIT = 1_000


class JobExchangeStoreError(ValueError):
    """Base error for invalid or unsafe exchange-store operations."""


class IdempotencyConflictError(JobExchangeStoreError):
    """Raised when one idempotency key is reused for different content."""


class SensitivePayloadError(JobExchangeStoreError):
    """Raised when a payload contains a credential-shaped field."""


class JobExchangeStore:
    """Durable, bounded status/knowledge/result journal for one job."""

    def __init__(
        self,
        path: str | Path,
        *,
        allowed_root: str | Path,
        job_id: str,
        blueprint_id: str | None = None,
        run_id: str | None = None,
        goal_id: str | None = None,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        max_history: int = DEFAULT_MAX_HISTORY,
        reject_sensitive_fields: bool = True,
        sqlite_timeout_seconds: float = 5.0,
    ) -> None:
        self.allowed_root = Path(allowed_root).expanduser().resolve()
        self.path = _resolve_store_path(path, self.allowed_root)
        self.identity = {
            "job_id": _bounded_text(job_id, "job_id", required=True),
            "blueprint_id": _bounded_text(blueprint_id, "blueprint_id"),
            "run_id": _bounded_text(run_id, "run_id"),
            "goal_id": _bounded_text(goal_id, "goal_id"),
        }
        self.identity = {key: value for key, value in self.identity.items() if value is not None}
        self.max_payload_bytes = _positive_int(max_payload_bytes, "max_payload_bytes")
        self.max_history = _positive_int(max_history, "max_history")
        self.reject_sensitive_fields = bool(reject_sensitive_fields)
        self.sqlite_timeout_seconds = float(sqlite_timeout_seconds)
        if self.sqlite_timeout_seconds <= 0:
            raise JobExchangeStoreError("sqlite_timeout_seconds must be greater than 0")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def publish_status(
        self,
        status: str,
        *,
        stage: str,
        summary: str = "",
        progress: float | None = None,
        metadata: Mapping[str, Any] | None = None,
        publication_state: str = "staged",
        idempotency_key: str,
        record_id: str = "job",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": _bounded_text(status, "status", required=True)}
        if progress is not None:
            resolved_progress = float(progress)
            if resolved_progress < 0 or resolved_progress > 1:
                raise JobExchangeStoreError("progress must be between 0 and 1")
            payload["progress"] = resolved_progress
        if metadata:
            payload["metadata"] = dict(metadata)
        return self.publish(
            "status",
            record_id,
            payload,
            stage=stage,
            summary=summary,
            publication_state=publication_state,
            idempotency_key=idempotency_key,
        )

    def publish_knowledge(
        self,
        record_id: str,
        knowledge: Any,
        *,
        stage: str,
        summary: str = "",
        publication_state: str = "staged",
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self.publish(
            "knowledge",
            record_id,
            knowledge,
            stage=stage,
            summary=summary,
            publication_state=publication_state,
            idempotency_key=idempotency_key,
        )

    def publish_result(
        self,
        record_id: str,
        result: Any,
        *,
        stage: str,
        summary: str = "",
        publication_state: str = "staged",
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self.publish(
            "result",
            record_id,
            result,
            stage=stage,
            summary=summary,
            publication_state=publication_state,
            idempotency_key=idempotency_key,
        )

    def publish(
        self,
        kind: str,
        record_id: str,
        payload: Any,
        *,
        stage: str,
        summary: str = "",
        publication_state: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        resolved_kind = _kind(kind)
        resolved_record_id = _bounded_text(record_id, "record_id", required=True)
        resolved_stage = _bounded_text(stage, "stage", required=True)
        resolved_summary = _bounded_text(summary, "summary", max_length=2_000) or ""
        resolved_state = _publication_state(publication_state)
        resolved_key = _bounded_text(idempotency_key, "idempotency_key", required=True)
        if self.reject_sensitive_fields:
            sensitive_path = _first_sensitive_path(payload)
            if sensitive_path:
                raise SensitivePayloadError(
                    f"payload contains sensitive field {sensitive_path}; publish a safe reference instead"
                )
        payload_json = _canonical_json(payload)
        payload_bytes = len(payload_json.encode("utf-8"))
        if payload_bytes > self.max_payload_bytes:
            raise JobExchangeStoreError(
                f"payload is {payload_bytes} bytes; maximum is {self.max_payload_bytes}"
            )
        fingerprint = _fingerprint(
            {
                "kind": resolved_kind,
                "record_id": resolved_record_id,
                "stage": resolved_stage,
                "summary": resolved_summary,
                "publication_state": resolved_state,
                "payload": json.loads(payload_json),
            }
        )
        published_at = _utc_now()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                "SELECT * FROM updates WHERE idempotency_key = ?",
                (resolved_key,),
            ).fetchone()
            if replay is not None:
                if replay["fingerprint"] != fingerprint:
                    connection.rollback()
                    raise IdempotencyConflictError(
                        f"idempotency key {resolved_key!r} was already used for different content"
                    )
                connection.commit()
                return {**_row_to_record(replay), "idempotent_replay": True}

            cursor = connection.execute(
                """
                INSERT INTO updates (
                    kind, record_id, stage, summary, publication_state,
                    payload_json, idempotency_key, fingerprint, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolved_kind,
                    resolved_record_id,
                    resolved_stage,
                    resolved_summary,
                    resolved_state,
                    payload_json,
                    resolved_key,
                    fingerprint,
                    published_at,
                ),
            )
            revision = int(cursor.lastrowid)
            self._prune_history(connection, revision)
            row = connection.execute(
                "SELECT * FROM updates WHERE revision = ?",
                (revision,),
            ).fetchone()
            connection.commit()
        return {**_row_to_record(row), "idempotent_replay": False}

    def snapshot(
        self,
        *,
        kinds: Iterable[str] | None = None,
        include_staged: bool = True,
        limit: int = DEFAULT_QUERY_LIMIT,
    ) -> dict[str, Any]:
        selected_kinds = _kinds(kinds)
        resolved_limit = _query_limit(limit)
        placeholders = ",".join("?" for _ in selected_kinds)
        state_clause = "" if include_staged else "AND publication_state = 'final'"
        query = f"""
            SELECT updates.*
            FROM updates
            INNER JOIN (
                SELECT kind, record_id, MAX(revision) AS latest_revision
                FROM updates
                WHERE kind IN ({placeholders}) {state_clause}
                GROUP BY kind, record_id
            ) latest
            ON updates.revision = latest.latest_revision
            ORDER BY updates.revision ASC
            LIMIT ?
        """
        with self._connect() as connection:
            current_revision = _current_revision(connection)
            rows = connection.execute(
                query,
                (*selected_kinds, resolved_limit + 1),
            ).fetchall()
        truncated = len(rows) > resolved_limit
        records = {"status": [], "knowledge": [], "results": []}
        for row in rows[:resolved_limit]:
            record = _row_to_record(row)
            key = "results" if record["kind"] == "result" else record["kind"]
            records[key].append(record)
        return {
            "schema_version": SCHEMA_VERSION,
            "identity": dict(self.identity),
            "revision": current_revision,
            "records": records,
            "include_staged": bool(include_staged),
            "truncated": truncated,
        }

    def updates(
        self,
        *,
        after_revision: int = 0,
        kinds: Iterable[str] | None = None,
        include_staged: bool = True,
        limit: int = DEFAULT_QUERY_LIMIT,
    ) -> dict[str, Any]:
        if int(after_revision) < 0:
            raise JobExchangeStoreError("after_revision must be zero or greater")
        selected_kinds = _kinds(kinds)
        resolved_limit = _query_limit(limit)
        placeholders = ",".join("?" for _ in selected_kinds)
        state_clause = "" if include_staged else "AND publication_state = 'final'"
        query = f"""
            SELECT * FROM updates
            WHERE revision > ?
              AND kind IN ({placeholders})
              {state_clause}
            ORDER BY revision ASC
            LIMIT ?
        """
        with self._connect() as connection:
            current_revision = _current_revision(connection)
            rows = connection.execute(
                query,
                (int(after_revision), *selected_kinds, resolved_limit + 1),
            ).fetchall()
        has_more = len(rows) > resolved_limit
        records = [_row_to_record(row) for row in rows[:resolved_limit]]
        next_revision = records[-1]["revision"] if records else int(after_revision)
        return {
            "schema_version": SCHEMA_VERSION,
            "identity": dict(self.identity),
            "current_revision": current_revision,
            "after_revision": int(after_revision),
            "next_revision": next_revision,
            "has_more": has_more,
            "updates": records,
        }

    def get_record(
        self,
        kind: str,
        record_id: str,
        *,
        include_staged: bool = True,
    ) -> dict[str, Any] | None:
        resolved_kind = _kind(kind)
        resolved_record_id = _bounded_text(record_id, "record_id", required=True)
        state_clause = "" if include_staged else "AND publication_state = 'final'"
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM updates
                WHERE kind = ? AND record_id = ? {state_clause}
                ORDER BY revision DESC
                LIMIT 1
                """,
                (resolved_kind, resolved_record_id),
            ).fetchone()
        return _row_to_record(row) if row is not None else None

    def _initialize(self) -> None:
        identity_json = _canonical_json(self.identity)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS updates (
                    revision INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    publication_state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    fingerprint TEXT NOT NULL,
                    published_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS updates_record_revision_idx
                    ON updates(kind, record_id, revision DESC);
                """
            )
            existing = connection.execute(
                "SELECT value FROM metadata WHERE key = 'identity'"
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES ('identity', ?)",
                    (identity_json,),
                )
            elif existing["value"] != identity_json:
                raise JobExchangeStoreError(
                    "store identity does not match the existing job exchange"
                )
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES ('schema_version', ?)",
                (SCHEMA_VERSION,),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=self.sqlite_timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(self.sqlite_timeout_seconds * 1000)}")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def _prune_history(self, connection: sqlite3.Connection, revision: int) -> None:
        cutoff = revision - self.max_history
        if cutoff <= 0:
            return
        connection.execute(
            """
            DELETE FROM updates
            WHERE revision <= ?
              AND revision NOT IN (
                  SELECT MAX(revision) FROM updates GROUP BY kind, record_id
              )
            """,
            (cutoff,),
        )


def _resolve_store_path(path: str | Path, allowed_root: Path) -> Path:
    root = allowed_root.resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise JobExchangeStoreError(
            f"store path {resolved} is outside allowed root {root}"
        ) from exc
    if resolved == root:
        raise JobExchangeStoreError("store path must be a file below allowed_root")
    return resolved


def _kind(value: str) -> str:
    kind = str(value).strip().lower()
    if kind not in VALID_KINDS:
        raise JobExchangeStoreError(
            f"kind must be one of {', '.join(sorted(VALID_KINDS))}"
        )
    return kind


def _kinds(values: Iterable[str] | None) -> tuple[str, ...]:
    if values is None:
        return tuple(sorted(VALID_KINDS))
    if isinstance(values, (str, bytes)):
        values = [str(values)]
    resolved = tuple(dict.fromkeys(_kind(value) for value in values))
    if not resolved:
        raise JobExchangeStoreError("kinds must not be empty")
    return resolved


def _publication_state(value: str) -> str:
    state = str(value).strip().lower()
    if state not in VALID_PUBLICATION_STATES:
        raise JobExchangeStoreError(
            "publication_state must be staged or final"
        )
    return state


def _bounded_text(
    value: Any,
    name: str,
    *,
    required: bool = False,
    max_length: int = 512,
) -> str | None:
    if value is None:
        if required:
            raise JobExchangeStoreError(f"{name} is required")
        return None
    text = str(value).strip()
    if required and not text:
        raise JobExchangeStoreError(f"{name} is required")
    if not text:
        return None
    if len(text) > max_length:
        raise JobExchangeStoreError(
            f"{name} exceeds the {max_length} character limit"
        )
    return text


def _positive_int(value: Any, name: str) -> int:
    resolved = int(value)
    if resolved <= 0:
        raise JobExchangeStoreError(f"{name} must be greater than 0")
    return resolved


def _query_limit(value: Any) -> int:
    resolved = _positive_int(value, "limit")
    if resolved > MAX_QUERY_LIMIT:
        raise JobExchangeStoreError(f"limit must not exceed {MAX_QUERY_LIMIT}")
    return resolved


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise JobExchangeStoreError("payload must be finite JSON data") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _first_sensitive_path(value: Any, path: str = "payload") -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            normalized = key_text.strip().lower().replace("-", "_")
            item_path = f"{path}.{key_text}"
            if normalized in SENSITIVE_FIELD_NAMES:
                return item_path
            nested = _first_sensitive_path(item, item_path)
            if nested:
                return nested
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            nested = _first_sensitive_path(item, f"{path}[{index}]")
            if nested:
                return nested
    return None


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "revision": int(row["revision"]),
        "kind": str(row["kind"]),
        "record_id": str(row["record_id"]),
        "stage": str(row["stage"]),
        "summary": str(row["summary"]),
        "publication_state": str(row["publication_state"]),
        "payload": json.loads(row["payload_json"]),
        "published_at": str(row["published_at"]),
        "idempotency_key": str(row["idempotency_key"]),
    }


def _current_revision(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(revision), 0) AS revision FROM updates"
    ).fetchone()
    return int(row["revision"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
