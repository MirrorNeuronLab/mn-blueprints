"""Offline launch-contract checks; never submit jobs or read customer inputs."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINTS = ("vc_assistant", "financial_advisor")


@pytest.mark.parametrize("name", BLUEPRINTS)
def test_compiled_worker_build_uses_declared_packages(name):
    from mn_sdk.version_constraints import dependency_requirement
    from mn_sdk.blueprints import compile_blueprint, read_blueprint
    from mn_sdk.submission_preparation import (
        stage_skill_dependency_payloads_for_manifest,
    )

    root = ROOT / name
    manifest = compile_blueprint(read_blueprint(root)).manifest
    payloads = {
        str(path.relative_to(root / "payloads")): path.read_bytes()
        for path in (root / "payloads" / "docker_worker").iterdir()
        if path.is_file()
    }
    stage_skill_dependency_payloads_for_manifest(manifest, payloads, bundle_dir=root)
    requirements = payloads["docker_worker/requirements.txt"].decode().splitlines()
    declarations = json.loads((root / "dependencies.json").read_text())
    for dependency in declarations["skills"] + declarations["agents"]:
        assert dependency_requirement(dependency["name"], dependency["version"]) in requirements
    if name == "vc_assistant":
        assert "mirrorneuron-membrane-python-sdk>=1.3.47" in requirements
    assert not payloads.get("docker_worker/local-requirements.txt", b"").strip()
    assert not any("__mn_skill_dependencies/local/" in path for path in payloads)
