from __future__ import annotations

import keyword
import re
from typing import Any


RESERVED_FILENAMES = {"con", "prn", "aux", "nul", "com1", "lpt1"}


def safe_filename(value: str, *, default_extension: str = ".py") -> str:
    """Return a conservative file name for generated code artifacts."""

    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("._-")
    if not stem:
        stem = "script"
    if stem.lower() in RESERVED_FILENAMES:
        stem = f"{stem}_file"
    extension = default_extension if default_extension.startswith(".") else f".{default_extension}"
    if "." not in stem.rsplit("/", maxsplit=1)[-1]:
        stem += extension
    return stem


def build_script_spec(
    name: str,
    purpose: str,
    *,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    language: str = "python",
) -> dict[str, Any]:
    """Create a portable script generation specification."""

    filename = safe_filename(name, default_extension=".py" if language == "python" else ".txt")
    return {
        "name": _clean(name),
        "filename": filename,
        "language": _clean(language).lower() or "python",
        "purpose": _clean(purpose),
        "inputs": [_clean(item) for item in inputs or [] if _clean(item)],
        "outputs": [_clean(item) for item in outputs or [] if _clean(item)],
    }


def build_file_plan(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize several file specs into a generation plan."""

    plan = []
    for index, spec in enumerate(specs):
        filename = safe_filename(spec.get("filename") or spec.get("name") or f"file_{index + 1}.py")
        plan.append(
            {
                "path": filename,
                "purpose": _clean(spec.get("purpose") or ""),
                "language": _clean(spec.get("language") or _language_from_filename(filename)),
            }
        )
    validate_file_plan(plan)
    return plan


def validate_file_plan(plan: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate generated file paths for duplicate or unsafe entries."""

    issues: list[str] = []
    seen: set[str] = set()
    for item in plan:
        path = _clean(item.get("path"))
        if not path:
            issues.append("File path is empty.")
            continue
        if path.startswith(("/", "~")) or ".." in path.split("/"):
            issues.append(f"{path} is not a safe relative path.")
        if path in seen:
            issues.append(f"{path} is duplicated.")
        seen.add(path)
    if issues:
        raise ValueError("; ".join(issues))
    return {"file_count": len(plan), "paths": [item["path"] for item in plan]}


def render_python_script(spec: dict[str, Any]) -> str:
    """Render a minimal, runnable Python CLI skeleton from a script spec."""

    normalized = build_script_spec(
        spec.get("name") or spec.get("filename") or "script",
        spec.get("purpose") or "",
        inputs=spec.get("inputs") or [],
        outputs=spec.get("outputs") or [],
        language="python",
    )
    function_name = _safe_identifier(normalized["name"])
    docstring = normalized["purpose"] or "Generated script entry point."
    input_help = ", ".join(normalized["inputs"]) or "input value"
    output_help = ", ".join(normalized["outputs"]) or "result"
    return (
        '"""' + docstring + '"""\n\n'
        "from __future__ import annotations\n\n"
        "import argparse\n\n\n"
        f"def {function_name}(value: str) -> str:\n"
        f"    \"\"\"Transform {input_help} into {output_help}.\"\"\"\n"
        "    return value\n\n\n"
        "def main() -> None:\n"
        "    parser = argparse.ArgumentParser(description=__doc__)\n"
        "    parser.add_argument(\"value\")\n"
        "    args = parser.parse_args()\n"
        f"    print({function_name}(args.value))\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    main()\n"
    )


def _language_from_filename(filename: str) -> str:
    suffix = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""
    return {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "sh": "shell",
        "sql": "sql",
    }.get(suffix, "text")


def _safe_identifier(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").lower()).strip("_")
    if not name or name[0].isdigit() or keyword.iskeyword(name):
        name = f"run_{name or 'script'}"
    return name


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
