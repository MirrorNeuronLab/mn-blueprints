#!/usr/bin/env python3
import importlib
import json
import os
import pathlib
import sys


def _load_input():
    path = pathlib.Path(os.environ["MIRROR_NEURON_INPUT_FILE"])
    payload = json.loads(path.read_text())
    return payload.get("args", []), payload.get("kwargs", {})


def main():
    source_dir = pathlib.Path(__file__).resolve().parent / "source"
    sys.path.insert(0, str(source_dir))

    module = importlib.import_module(os.environ["MN_PY_SOURCE_MODULE"])
    owner = getattr(module, os.environ["MN_PY_OWNER_CLASS"])
    method = getattr(owner(), os.environ["MN_PY_METHOD"])
    args, kwargs = _load_input()
    result = method(*args, **kwargs)

    if os.environ.get("MN_PY_FINAL") == "1" and os.environ.get("MN_PY_COMPLETE_FINAL") == "1":
        print(json.dumps({"complete_job": result}))
    elif os.environ.get("MN_PY_FINAL") == "1":
        print(json.dumps({
            "next_state": result if isinstance(result, dict) else {"result": result},
            "events": [{
                "type": "python_workflow_result",
                "payload": result if isinstance(result, dict) else {"result": result}
            }]
        }))
    else:
        print(json.dumps({
            "emit_messages": [{
                "type": os.environ["MN_PY_OUTPUT_TYPE"],
                "body": {"args": [result], "kwargs": {}}
            }]
        }))


if __name__ == "__main__":
    main()
