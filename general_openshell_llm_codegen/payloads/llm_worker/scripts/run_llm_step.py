#!/usr/bin/env python3
import json
import os
import sys
import re
from pathlib import Path
from typing import Optional, Tuple

# Insert the vendor directory to sys.path
vendor_dir = Path(__file__).resolve().parent.parent / "vendor"
sys.path.insert(0, str(vendor_dir))

try:
    import litellm
except ImportError as e:
    raise RuntimeError(f"Failed to import litellm from {vendor_dir}: {e}")

def load_message() -> dict:
    return json.loads(Path(os.environ["MIRROR_NEURON_MESSAGE_FILE"]).read_text())

def extract_payload(message: dict) -> dict:
    body = message.get("body") or {}
    if isinstance(body, dict) and isinstance(body.get("sandbox"), dict):
        stdout = (body.get("sandbox", {}).get("stdout") or "").strip()
        if stdout:
            return json.loads(stdout)
    return body

def call_llm(system_instruction: str, prompt: str, schema: dict) -> dict:
    model = os.environ.get("LLM_MODEL", "gemini/gemini-2.5-flash")
    
    # We append the schema instruction to the system prompt to guide models
    system_prompt_with_schema = (
        f"{system_instruction}\n\n"
        f"You MUST output ONLY valid JSON exactly matching this schema:\n"
        f"{json.dumps(schema, indent=2)}"
    )

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_with_schema},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
    except Exception as e:
        raise RuntimeError(f"LiteLLM API request failed: {e}")

    raw_text = response.choices[0].message.content

    # Strip markdown code blocks if present
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}", file=sys.stderr)
        print(f"Raw text was:\n{raw_text}", file=sys.stderr)
        # Fallback dummy to allow pipeline to continue
        if "code" in schema["properties"]:
            return {"file_name": "error.py", "summary": "Error", "changes": [], "code": "# JSON error"}
        else:
            return {"summary": "Error", "strengths": [], "improvement_suggestions": [], "risk_flags": []}

def codegen_prompt(
    task: dict, round_number: int, prior_code: Optional[str], review: Optional[dict]
) -> Tuple[str, str, dict]:
    system_instruction = (
        "You are a careful senior Python engineer. Return only a JSON object."
    )

    review_json = json.dumps(review, indent=2) if review else "null"
    prior_code_text = prior_code or "<none yet>"
    prompt = f"""
Task:
{json.dumps(task, indent=2)}

Round: {round_number}

Prior code:
{prior_code_text}

Latest review:
{review_json}

Write or revise the Python solution so it satisfies the task and validation expectations.
Use only the Python standard library.
Return JSON with file_name, summary, changes (array of strings), and code.
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "file_name": {"type": "string"},
            "summary": {"type": "string"},
            "changes": {"type": "array", "items": {"type": "string"}},
            "code": {"type": "string"}
        },
        "required": ["file_name", "summary", "changes", "code"]
    }
    return system_instruction, prompt, schema

def review_prompt(candidate: dict, round_number: int) -> Tuple[str, str, dict]:
    system_instruction = (
        "You are a strict code reviewer. Return only a JSON object."
    )
    prompt = f"""
Task:
{json.dumps(candidate["task"], indent=2)}

Review round: {round_number}

Candidate file name:
{candidate["file_name"]}

Candidate code:
{candidate["code"]}

Review the code against the task. Focus on correctness, CLI behavior, edge cases, and maintainability.
Return JSON with summary, strengths (array), improvement_suggestions (array), and risk_flags (array).
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "improvement_suggestions": {"type": "array", "items": {"type": "string"}},
            "risk_flags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["summary", "strengths", "improvement_suggestions", "risk_flags"]
    }
    return system_instruction, prompt, schema

def run_codegen(payload: dict, round_number: int) -> dict:
    if payload.get("kind") == "code_review":
        task = payload["task"]
        prior_code = payload["candidate_code"]
        review = payload
        history = payload.get("history", [])
    else:
        task = payload
        prior_code = None
        review = None
        history = []

    system_instruction, prompt, schema = codegen_prompt(task, round_number, prior_code, review)
    response = call_llm(system_instruction, prompt, schema)

    return {
        "kind": "code_generation",
        "round": round_number,
        "task": task,
        "file_name": response.get("file_name", "log_analyzer.py"),
        "summary": response.get("summary", f"Generated round {round_number} code."),
        "changes": response.get("changes", []),
        "code": response.get("code", ""),
        "history": history
        + [
            {
                "stage": "codegen",
                "round": round_number,
                "summary": response.get("summary", ""),
                "changes": response.get("changes", []),
            }
        ],
    }

def run_review(payload: dict, round_number: int) -> dict:
    if payload.get("kind") != "code_generation":
        raise RuntimeError(f"review step expected code_generation payload, got {payload.get('kind')}")

    system_instruction, prompt, schema = review_prompt(payload, round_number)
    response = call_llm(system_instruction, prompt, schema)

    return {
        "kind": "code_review",
        "round": round_number,
        "task": payload["task"],
        "file_name": payload["file_name"],
        "candidate_code": payload["code"],
        "summary": response.get("summary", f"Reviewed round {round_number} code."),
        "strengths": response.get("strengths", []),
        "improvement_suggestions": response.get("improvement_suggestions", []),
        "risk_flags": response.get("risk_flags", []),
        "history": payload.get("history", [])
        + [
            {
                "stage": "review",
                "round": round_number,
                "summary": response.get("summary", ""),
                "improvement_suggestions": response.get("improvement_suggestions", []),
                "risk_flags": response.get("risk_flags", []),
            }
        ],
    }

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_llm_step.py <codegen|review> <round>")

    step_kind = sys.argv[1]
    round_number = int(sys.argv[2])
    message = load_message()
    payload = extract_payload(message)

    if step_kind == "codegen":
        result = run_codegen(payload, round_number)
    elif step_kind == "review":
        result = run_review(payload, round_number)
    else:
        raise SystemExit(f"unknown step kind: {step_kind}")

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
