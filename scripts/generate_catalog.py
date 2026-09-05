#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def generated(root: Path):
    """Validate and format the explicitly published, ordered package inventory."""
    from mn_sdk.blueprints import read_catalog

    return [record["path"] for record in read_catalog(root / "index.json")]


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
