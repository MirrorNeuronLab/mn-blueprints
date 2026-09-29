"""Bounded, shell-free OpenCode invocation for caller-owned OpenShell workers."""

from __future__ import annotations

import json
import math
import os
import re
import selectors
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

DEFAULT_MODEL = "opencode/muse-spark-1.3-contributor-free"
DEFAULT_MODEL_LABEL = "Muse Spark 1.3 FreeOpenCode Zen"
_MODEL = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_./:-]+$")


class OpenCodeError(RuntimeError):
    """A launch, process, or OpenCode event-stream failure."""


@dataclass(frozen=True)
class OpenCodeRequest:
    folder: str | Path
    prompt: str
    mode: str = "generate"
    model: str = DEFAULT_MODEL
    sandbox_root: str | Path = "/sandbox/job"
    timeout_seconds: float = 600
    max_output_bytes: int = 8 * 1024 * 1024

    def validated(self) -> tuple[Path, str]:
        if self.mode not in {"generate", "edit", "review"}:
            raise ValueError("mode must be generate, edit, or review")
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must be nonblank text")
        if len(self.prompt.encode("utf-8")) > 128 * 1024:
            raise ValueError("prompt exceeds 128 KiB")
        if not isinstance(self.model, str):
            raise ValueError("model must be a provider/model string")
        model = DEFAULT_MODEL if self.model == DEFAULT_MODEL_LABEL else self.model
        if len(model) > 256 or not _MODEL.fullmatch(model):
            raise ValueError("model must use provider/model format")
        if (isinstance(self.timeout_seconds, bool)
                or not isinstance(self.timeout_seconds, (int, float))
                or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 3600):
            raise ValueError("timeout_seconds must be between 0 and 3600")
        if (isinstance(self.max_output_bytes, bool)
                or not isinstance(self.max_output_bytes, int)
                or not 0 < self.max_output_bytes <= 64 * 1024 * 1024):
            raise ValueError("max_output_bytes must be between 1 and 64 MiB")
        root = Path(self.sandbox_root).expanduser().resolve(strict=True)
        folder = Path(self.folder).expanduser().resolve(strict=True)
        if not root.is_dir() or not folder.is_dir() or not folder.is_relative_to(root):
            raise ValueError("folder must be an existing directory inside sandbox_root")
        return folder, model


@dataclass(frozen=True)
class OpenCodeResult:
    model: str
    mode: str
    folder: str
    session_id: str | None
    text: str
    events: list[dict]
    stderr: str
    exit_code: int
    elapsed_seconds: float

    def as_dict(self) -> dict:
        return asdict(self)


def build_command(request: OpenCodeRequest, *, binary: str = "opencode") -> list[str]:
    folder, model = request.validated()
    if not isinstance(binary, str) or not binary or "\x00" in binary:
        raise ValueError("binary must be an executable name or path")
    return [
        binary, "--pure", "run", "--format", "json", "--model", model,
        "--agent", "plan" if request.mode == "review" else "build",
        "--dir", str(folder), "--", request.prompt,
    ]


def _permissions(mode: str) -> dict:
    permissions = {"*": "deny", "read": "allow", "glob": "allow",
                   "grep": "allow", "list": "allow"}
    if mode != "review":
        permissions.update(edit="allow", bash="allow")
    return permissions


def _stop(process: subprocess.Popen) -> None:
    # Kill the group even if the direct process already exited: descendants may
    # still own the capture pipes or continue modifying the workspace.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def run_opencode(
    request: OpenCodeRequest, *, binary: str = "opencode",
    env: Mapping[str, str] | None = None,
) -> OpenCodeResult:
    """Run once in a sandbox folder; raise on process or JSON-event failure."""
    command = build_command(request, binary=binary)
    folder, model = request.validated()
    permissions = _permissions(request.mode)
    process_env = {**os.environ, **(env or {})}
    process_env["OPENCODE_CONFIG_CONTENT"] = json.dumps({
        "share": "disabled", "autoupdate": False, "permission": permissions,
        "agent": {name: {"permission": permissions} for name in ("build", "plan")},
    })
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command, cwd=folder, env=process_env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
    except OSError as exc:
        raise OpenCodeError("Could not launch the installed OpenCode executable") from exc
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    captured = 0
    try:
        with selectors.DefaultSelector() as selector:
            for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
                selector.register(pipe, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = request.timeout_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    raise OpenCodeError("OpenCode exceeded timeout_seconds")
                for key, _ in selector.select(timeout=min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    captured += len(chunk)
                    if captured > request.max_output_bytes:
                        raise OpenCodeError("OpenCode exceeded max_output_bytes")
                    buffers[key.data].extend(chunk)
            remaining = request.timeout_seconds - (time.monotonic() - started)
            try:
                exit_code = process.wait(timeout=max(remaining, 0.001))
            except subprocess.TimeoutExpired as exc:
                raise OpenCodeError("OpenCode exceeded timeout_seconds") from exc
    except BaseException:
        _stop(process)
        raise
    finally:
        process.stdout.close()
        process.stderr.close()
    if exit_code:
        raise OpenCodeError(f"OpenCode exited with status {exit_code}")
    events = []
    try:
        for line in buffers["stdout"].decode("utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError("invalid event")
            if event["type"] == "error" or event.get("error"):
                raise OpenCodeError("OpenCode reported an error event; inspect provider/tool setup")
            if (event.get("part", {}).get("state") or {}).get("status") == "error":
                raise OpenCodeError("OpenCode reported a failed tool call")
            events.append(event)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, AttributeError) as exc:
        raise OpenCodeError("OpenCode returned an invalid JSON event stream") from exc
    if not events:
        raise OpenCodeError("OpenCode returned no JSON events")
    texts = [event.get("part", {}).get("text", "") for event in events
             if event["type"] == "text"]
    return OpenCodeResult(
        model=model, mode=request.mode, folder=str(folder),
        session_id=next((event.get("sessionID") for event in events if event.get("sessionID")), None),
        text="\n".join(texts), events=events,
        stderr=buffers["stderr"].decode("utf-8", errors="replace"),
        exit_code=exit_code, elapsed_seconds=round(time.monotonic() - started, 3),
    )
