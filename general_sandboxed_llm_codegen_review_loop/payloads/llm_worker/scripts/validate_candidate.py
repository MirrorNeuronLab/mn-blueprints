#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import os
from typing import List, Optional, Tuple

def load_message() -> dict:
    return json.loads(Path(os.environ["MN_MESSAGE_FILE"]).read_text())

def extract_payload(message: dict) -> dict:
    body = message.get("body") or {}
    if isinstance(body, dict) and isinstance(body.get("sandbox"), dict):
        stdout = (body.get("sandbox", {}).get("stdout") or "").strip()
        if stdout:
            return json.loads(stdout)
    return body

def run_command(command: List[str], stdin_text: Optional[str] = None) -> Tuple[int, str, str]:
    proc = subprocess.run(
        command,
        input=stdin_text,
        text=True,
        capture_output=True,
        timeout=20,
    )
    return proc.returncode, proc.stdout, proc.stderr

def main() -> None:
    payload = extract_payload(load_message())
    task = payload["task"]
    validation = task["validation"]

    with tempfile.TemporaryDirectory(prefix="mirror_neuron_llm_validate_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        script_path = tmp_path / payload.get("file_name", "log_analyzer.py")
        log_path = tmp_path / "sample.log"
        script_path.write_text(payload["code"])
        log_path.write_text(task["sample_log"])
        
        assertions = []
        
        # Clean up any existing helper script to ensure it's generated dynamically
        helper_path = Path("/tmp/log_parser_helper.sh")
        if helper_path.exists():
            helper_path.unlink()

        json_code, json_stdout, json_stderr = run_command(
            [sys.executable, str(script_path), "--log-file", str(log_path)]
        )
        
        # Check if helper path is referenced in code
        helper_created = "/tmp/log_parser_helper.sh" in payload["code"]
        assertions.append({
            "name": "helper_script_referenced",
            "passed": helper_created,
            "details": "The string /tmp/log_parser_helper.sh was found in the code" if helper_created else "The string /tmp/log_parser_helper.sh was not found in the code"
        })
        
        if json_code == 0:
            try:
                # Find JSON part in case there's extra print output
                import re
                match = re.search(r"\{.*\}", json_stdout, re.DOTALL)
                if not match:
                    raise json.JSONDecodeError("No JSON found", json_stdout, 0)
                    
                parsed_json = json.loads(match.group(0))
                expected = validation["expected"]
                
                err_ok = parsed_json.get("total_errors") == expected["total_errors"]
                warn_ok = parsed_json.get("total_warnings") == expected["total_warnings"]
                ips_ok = sorted(parsed_json.get("unique_error_ips", [])) == sorted(expected["unique_error_ips"])
                
                json_ok = err_ok and warn_ok and ips_ok
                
                assertions.append({
                    "name": "json_output_matches_expected",
                    "passed": json_ok,
                    "details": parsed_json if json_ok else {"expected": expected, "actual": parsed_json, "stdout": json_stdout, "stderr": json_stderr},
                })
            except Exception as e:
                assertions.append({
                    "name": "json_output_matches_expected",
                    "passed": False,
                    "details": {"error": str(e), "stdout": json_stdout, "stderr": json_stderr},
                })
        else:
            assertions.append({
                "name": "json_output_matches_expected",
                "passed": False,
                "details": {"exit_code": json_code, "stdout": json_stdout, "stderr": json_stderr},
            })

        tests_passed = all(assertion["passed"] for assertion in assertions)
        result = {
            "kind": "validation_result",
            "task": task,
            "file_name": payload.get("file_name", "log_analyzer.py"),
            "tests_passed": tests_passed,
            "summary": "All validator assertions passed." if tests_passed else "One or more validator assertions failed.",
            "assertions": assertions,
            "history": payload.get("history", []),
            "code": payload["code"],
        }

        print(json.dumps(result, indent=2))
        if not tests_passed:
            sys.exit(1)

if __name__ == "__main__":
    main()
