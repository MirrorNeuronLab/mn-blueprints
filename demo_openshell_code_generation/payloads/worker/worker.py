"""Generate and validate the demo page inside an OpenShell worker."""

import base64
import json
import os
import shutil
import sys
from pathlib import Path

# This payload ships the declared skill source for standalone OpenShell execution.
# MirrorNeuron can also install it through dependencies.json when building images.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "skills/opencode_skill/src"))

from mn_opencode_skill import DEFAULT_MODEL, OpenCodeRequest, run_opencode
from verify import verify_page


def main():
    if os.environ.get("MN_ARTIFACT_OUTPUT_DIR"):
        return handoff_main()
    if os.environ.get("MN_DEMO_STANDALONE") != "1":
        raise RuntimeError("This blueprint requires artifact_handoff v1 in Core and SDK")
    config = json.loads(os.environ.get("MN_BLUEPRINT_CONFIG_JSON", "{}"))
    options = config.get("opencode", {})
    folder = (ROOT / options.get("folder", "project")).resolve()
    if not folder.is_relative_to(ROOT):
        raise ValueError("opencode.folder must be inside the uploaded worker payload")
    folder.mkdir(parents=True, exist_ok=True)
    artifact_dir = Path(os.environ.get("MN_JOB_OUTPUT_DIR") or ROOT / "artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = (ROOT / options.get("prompt_file", "prompts/pizza.md")).resolve()
    if not prompt_path.is_relative_to(ROOT) or prompt_path.stat().st_size > 128 * 1024:
        raise ValueError("prompt_file must be a bounded payload-local file")
    if "--verify-only" in sys.argv:
        result = json.loads((artifact_dir / "opencode_result.json").read_text())
    else:
        result = run_opencode(OpenCodeRequest(
            folder=folder, prompt=prompt_path.read_text(),
            model=options.get("model", DEFAULT_MODEL), mode=options.get("mode", "generate"),
            timeout_seconds=options.get("timeout_seconds", 600),
        )).as_dict()
        (artifact_dir / "opencode_result.json").write_text(json.dumps(result, indent=2) + "\n")
    page = artifact_dir / "index.html"
    if "--verify-only" not in sys.argv:
        verify_page(folder / "index.html")
        shutil.copy2(folder / "index.html", page)
    verification = verify_page(page)
    (artifact_dir / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    output = {
        "status": "completed", "runner": "openshell", "model": result["model"],
        "session_id": result["session_id"], "verification": verification,
        "artifact": {"path": "index.html", "media_type": "text/html",
                     "sha256": verification["sha256"],
                     "content_base64": base64.b64encode(page.read_bytes()).decode("ascii")},
    }
    summary = {key: value for key, value in output.items() if key != "artifact"}
    summary["artifact"] = {key: value for key, value in output["artifact"].items() if key != "content_base64"}
    (artifact_dir / "run.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({
        "events": [{"type": "opencode_completed", "payload": {
            "model": result["model"], "session_id": result["session_id"]}},
            {"type": "html_verified", "payload": verification}],
        "complete_step": output, "next_state": output,
    }))


def handoff_main():
    """Runtime path: immutable declarations, no shared writable directories."""
    from mn_sdk.artifact_handoff import output_directory, register_output, resolve_input
    from mn_sdk.step_runtime import find_message_payload
    config = json.loads(os.environ.get("MN_BLUEPRINT_CONFIG_JSON", "{}"))
    options = config.get("opencode", {})
    output = output_directory()
    exports = {}
    if "--verify-only" in sys.argv:
        incoming = json.loads(Path(os.environ["MN_INPUT_FILE"]).read_text())
        refs = find_message_payload(incoming, required_keys={"html", "generation"})
        page = resolve_input(refs["html"])
        metadata = json.loads(resolve_input(refs["generation"]).read_text())
        verification = verify_page(page)
        (output / "verification.json").write_text(json.dumps(verification))
        verification_ref = register_output("verification.json", kind="html_verification")
        summary = {"status": "completed", "model": metadata["model"], "verification": verification}
        (output / "run.json").write_text(json.dumps(summary))
        run_ref = register_output("run.json", kind="generation_summary")
        outputs = {"html": refs["html"], "generation": refs["generation"], "verification": verification_ref,
                   "run": run_ref, "output_files": ["index.html", "opencode_result.json", "verification.json", "run.json"]}
        exports = {"index.html": refs["html"], "opencode_result.json": refs["generation"],
                   "verification.json": verification_ref, "run.json": run_ref}
    else:
        folder = (ROOT / options.get("folder", "project")).resolve()
        prompt = (ROOT / options.get("prompt_file", "prompts/pizza.md")).resolve()
        if not folder.is_relative_to(ROOT) or not prompt.is_relative_to(ROOT) or prompt.stat().st_size > 128 * 1024:
            raise ValueError("generation paths must stay inside worker payload")
        folder.mkdir(parents=True, exist_ok=True)
        result = run_opencode(OpenCodeRequest(folder=folder, prompt=prompt.read_text(),
            model=options.get("model", DEFAULT_MODEL), mode=options.get("mode", "generate"),
            timeout_seconds=options.get("timeout_seconds", 600))).as_dict()
        page = folder / "index.html"
        if page.is_symlink() or not page.is_file():
            raise ValueError("generator must produce a regular HTML file")
        shutil.copyfile(page, output / "index.html")
        (output / "opencode_result.json").write_text(json.dumps(result))
        outputs = {"html": register_output("index.html", kind="html"),
                   "generation": register_output("opencode_result.json", kind="generation_metadata")}
    refs = [ref for ref in outputs.values() if isinstance(ref, dict) and ref.get("type") == "artifact_ref"]
    print(json.dumps({"outputs": outputs, "artifacts": refs, "metrics": {}, "status": "completed", "exports": exports}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Code generation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
