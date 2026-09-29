import base64
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "payloads/worker"))
from verify import verify_page

spec = importlib.util.spec_from_file_location("runner", ROOT / "scripts/run_demo.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class DemoTests(unittest.TestCase):
    def test_verify_uses_shared_outputs_across_separate_workspaces(self):
        spec = importlib.util.spec_from_file_location("demo_worker", ROOT / "payloads/worker/worker.py")
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        with tempfile.TemporaryDirectory() as directory:
            shared = Path(directory) / "shared/outputs/user"
            workspaces = [Path(directory).resolve() / step for step in ("generate", "verify")]
            for workspace in workspaces:
                (workspace / "prompts").mkdir(parents=True)
                (workspace / "prompts/pizza.md").write_text("Generate HTML")

            def generate(request):
                (request.folder / "index.html").write_bytes(self.html())
                return SimpleNamespace(as_dict=lambda: {"model": "test", "session_id": "session"})

            with patch.dict(os.environ, {"MN_DEMO_STANDALONE": "1", "MN_JOB_OUTPUT_DIR": str(shared), "MN_BLUEPRINT_CONFIG_JSON": "{}"}), \
                 patch.object(worker, "run_opencode", side_effect=generate) as coding, \
                 patch("builtins.print"):
                with patch.object(worker, "ROOT", workspaces[0]), patch.object(sys, "argv", ["worker.py"]):
                    worker.main()
                with patch.object(worker, "ROOT", workspaces[1]), patch.object(sys, "argv", ["worker.py", "--verify-only"]):
                    worker.main()
                coding.assert_called_once()
            self.assertEqual((shared / "index.html").read_bytes(), self.html())
            self.assertEqual(json.loads((shared / "run.json").read_text())["status"], "completed")
            self.assertFalse((workspaces[1] / "project/index.html").exists())

    def html(self):
        return ('<!doctype html><html lang="en"><head><title>Pizza</title><style></style></head>'
                '<body><main><button>Order</button><input></main><script></script>'
                '<!--' + 'x' * 1100 + '--></body></html>').encode()

    def test_verified_host_export(self):
        content = self.html()
        result = {"status": "completed", "runner": "openshell", "artifact": {
            "content_base64": base64.b64encode(content).decode(),
            "sha256": hashlib.sha256(content).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory:
            page = runner.export_result({"complete_step": result}, Path(directory))
            self.assertEqual(verify_page(page)["sha256"], result["artifact"]["sha256"])
            self.assertNotIn("content_base64", (Path(directory)/"run.json").read_text())
            result["artifact"]["sha256"] = "incorrect"
            with self.assertRaises(ValueError):
                runner.export_result({"complete_step": result}, Path(directory))

    def test_external_assets_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory)/"index.html"
            page.write_bytes(self.html().replace(b'<script>', b'<script src="https://example.com/app.js">'))
            with self.assertRaisesRegex(ValueError, "external"):
                verify_page(page)

    def test_openshell_runner_and_default_model(self):
        execution = json.loads((ROOT/"execution.json").read_text())
        config = json.loads((ROOT/"config/default.json").read_text())
        self.assertEqual(execution["agents"]["nodes"][0]["config"]["runner_module"],
                         "MirrorNeuron.Runner.OpenShell")
        self.assertEqual(config["opencode"]["model"], "opencode/muse-spark-1.3-contributor-free")

    def test_standalone_uploads_worker_and_skill_for_both_clients(self):
        for container in (None, "test-core"):
            with self.subTest(container=container):
                args = ["run_demo.py", "--skip-build"]
                if container:
                    args += ["--runtime-container", container]
                commands = []

                def command(argv, **kwargs):
                    commands.append(argv)
                    return '{"complete_step":{"model":"test-model"}}' if kwargs.get("capture") else ""

                with tempfile.TemporaryDirectory() as output, \
                     patch.object(sys, "argv", args + ["--output", output]), \
                     patch.object(runner.shutil, "which", return_value="openshell"), \
                     patch.object(runner, "command", side_effect=command), \
                     patch.object(runner, "export_result", return_value=Path(output)/"index.html"):
                    self.assertEqual(runner.main(), 0)
                uploads = [argv for argv in commands if "upload" in argv]
                self.assertEqual(len(uploads), 2)
                self.assertEqual([Path(argv[-2]).name for argv in uploads], ["worker", "skills"])
                self.assertTrue(all(argv[-1] == "/sandbox/job" for argv in uploads))
                if container:
                    copies = [argv for argv in commands if argv[:2] == ["docker", "cp"]]
                    self.assertEqual([Path(argv[2]).name for argv in copies], ["worker", "skills"])


if __name__ == "__main__":
    unittest.main()
