#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def generated(root: Path):
    rows = []
    for folder in sorted(root.glob("demo_*")):
        if not folder.is_dir():
            continue
        manifest = json.loads((folder / "manifest.json").read_text())
        meta = manifest["metadata"]
        rows.append({
            "id": manifest["id"], "name": manifest["name"], "path": folder.name,
            "category": meta["category"], "description": meta["description"],
            "workflow_id": manifest["workflow"]["workflow_id"], "job_name": manifest["job_name"],
            "product": {"problem": meta["problem_solved"], "input": "Small deterministic mock input; json, file, and env_json are also supported.", "output": meta["output"], "how_it_works": meta["description"], "benefit": f"Demonstrates {meta['runtime_features'][0]} with minimal setup.", "target_users": meta["target_user"], "runtime_features": meta["runtime_features"]},
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    rows = generated(root)
    rendered = json.dumps(rows, indent=2, sort_keys=True) + "\n"
    if args.check:
        if (root / "index.json").read_text() != rendered:
            raise SystemExit("index.json is stale; run scripts/generate_catalog.py")
        print("index.json is current")
    else:
        (root / "index.json").write_text(rendered)


if __name__ == "__main__":
    main()
