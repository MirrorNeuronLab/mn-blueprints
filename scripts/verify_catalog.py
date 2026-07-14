#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REQUIRED = ("manifest.json", "README.md", "SPEC.md", "LICENSE.md", "TERM.md", "config/default.json", "payloads")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|authorization|password|private[_-]?key)\s*[:=]\s*[\"']?(?!\s*(?:null|none|false|\"\"))[^\s,}]+")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    index = json.loads((root / "index.json").read_text())
    categories = json.loads((root / "category.json").read_text())
    ids = [row["id"] for row in index]
    dirs = sorted(path.name for path in root.glob("demo_*") if path.is_dir())
    errors = []
    if len(ids) != 25 or len(set(ids)) != 25:
        errors.append(f"index must contain 25 unique rows; found {len(ids)}")
    if sorted(ids) != dirs:
        errors.append("index rows and demo directories differ")
    category_names = {row["name"] for row in categories.get("categories", [])}
    if category_names != {"Execution", "Workflow DAG", "Collaboration", "Memory", "Runtime Operations"}:
        errors.append("category.json must define the five focused catalog categories")
    for blueprint_id in ids:
        folder = root / blueprint_id
        for required in REQUIRED:
            if not (folder / required).exists():
                errors.append(f"{blueprint_id}: missing {required}")
        manifest = json.loads((folder / "manifest.json").read_text())
        config = json.loads((folder / "config/default.json").read_text())
        row = next(item for item in index if item["id"] == blueprint_id)
        if manifest.get("id") != blueprint_id:
            errors.append(f"{blueprint_id}: root manifest id mismatch")
        if manifest.get("metadata", {}).get("blueprint_id") != blueprint_id:
            errors.append(f"{blueprint_id}: manifest identity mismatch")
        if config.get("identity", {}).get("blueprint_id") != blueprint_id:
            errors.append(f"{blueprint_id}: config identity mismatch")
        features = manifest.get("metadata", {}).get("runtime_features") or []
        if len(features) != 1:
            errors.append(f"{blueprint_id}: expected one runtime feature, found {len(features)}")
        if features != row.get("product", {}).get("runtime_features"):
            errors.append(f"{blueprint_id}: index and manifest feature differ")
        if row.get("category") not in category_names:
            errors.append(f"{blueprint_id}: unknown category {row.get('category')}")
        if manifest.get("apiVersion") != "mn.workflow/v1" or not isinstance(manifest.get("workflow"), dict):
            errors.append(f"{blueprint_id}: current mn.workflow/v1 workflow contract is required")
        if "flow" in manifest or "graph_id" in manifest:
            errors.append(f"{blueprint_id}: obsolete root flow/graph_id field found")
        if not isinstance(manifest.get("runtime", {}).get("bindings"), dict):
            errors.append(f"{blueprint_id}: runtime.bindings must be an object")
        adapters = config.get("interfaces", {}).get("input_adapters") or []
        if not {"mock", "json", "file", "env_json"}.issubset(adapters):
            errors.append(f"{blueprint_id}: all four input adapters are required")
        llm_enabled = bool(config.get("llm", {}).get("enabled"))
        if llm_enabled != (blueprint_id == "demo_llm_tool_call"):
            errors.append(f"{blueprint_id}: llm.enabled violates the focused catalog default")
        size = sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())
        if size > 1_000_000:
            errors.append(f"{blueprint_id}: checked-in size {size} exceeds 1 MB")
        forbidden_dirs = {"_vendor", "site-packages", "__pycache__", ".venv", "node_modules"}
        if any(part in forbidden_dirs for path in folder.rglob("*") for part in path.parts):
            errors.append(f"{blueprint_id}: generated or vendored dependency directory found")
        oversized = [path for path in folder.rglob("*") if path.is_file() and path.stat().st_size > 250_000]
        if oversized:
            errors.append(f"{blueprint_id}: individual file exceeds 250 KB: {oversized[0].relative_to(folder)}")
        text_files = []
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            try:
                text_files.append((path, path.read_text(encoding="utf-8")))
            except UnicodeDecodeError:
                pass
        content = "\n".join(value for _, value in text_files)
        if "nemotron" in content.lower() or "192.168." in content:
            errors.append(f"{blueprint_id}: hard-coded model or LAN endpoint found")
        if SECRET_RE.search(content):
            errors.append(f"{blueprint_id}: secret-like value found")
        if args.validate:
            proc = subprocess.run(["mn", "blueprint", "validate", str(folder), "--output", "json"], text=True, capture_output=True)
            if proc.returncode:
                errors.append(f"{blueprint_id}: mn validation failed\n{proc.stdout or proc.stderr}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"catalog ok: {len(ids)} focused blueprints")


if __name__ == "__main__":
    main()
