import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
import grpc
import context_pb2
import context_pb2_grpc


def _setup_logger():
    logger = logging.getLogger("mn.blueprint.context_memory_basic.executor")
    logger.setLevel(os.environ.get("MIRROR_NEURON_LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    log_path = Path(os.environ.get("MIRROR_NEURON_BLUEPRINT_LOG_PATH", "/tmp/mn-blueprint.log"))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=int(os.environ.get("MIRROR_NEURON_LOG_MAX_BYTES", "1048576")),
            backupCount=int(os.environ.get("MIRROR_NEURON_LOG_BACKUP_COUNT", "5")),
        )
    except OSError:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = _setup_logger()

def call_llm(system_prompt, user_prompt, mock_response):
    quick_mode = os.environ.get("MN_BLUEPRINT_QUICK_TEST", "").strip().lower() in {"1", "true", "yes", "on"}
    if quick_mode:
        logger.info("quick test mode enabled; using mock LLM response")
        return json.dumps(mock_response)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; falling back to mock response")
        return json.dumps(mock_response)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.exception("LLM error; falling back to mock")
        return json.dumps(mock_response)

def main():
    try:
        input_data = json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())
        if "sandbox" in input_data and "stdout" in input_data["sandbox"]:
            source = json.loads(input_data["sandbox"]["stdout"])
        else:
            source = input_data.get("input", input_data)
            
        job_id = source.get("job_id", "job_ctx_123")
        focus_id = source.get("focus_id", "task_001")
        
        channel = grpc.insecure_channel('host.docker.internal:50052') 
        stub = context_pb2_grpc.ContextEngineStub(channel)
        
        response = stub.GetContext(context_pb2.GetContextRequest(
            job_id=job_id,
            agent_role="executor", 
            focus_id=focus_id,
            max_items=5
        ))
        
        task_command = None
        for item in response.items:
            content = json.loads(item.content_json)
            if item.type == "Task":
                task_command = content.get("command")
                
        if task_command:
            result = subprocess.run(task_command.split(), capture_output=True, text=True)
            output = result.stdout
        else:
            output = "No command found in context"
            
        # Use LLM to summarize output
        sys_prompt = "You are a log analyzer. Read the raw bash execution output and summarize it in a JSON field called 'summary'."
        user_prompt = f"Command run: {task_command}\nOutput: {output}"
        mock_resp = {"summary": "Command executed, returned ping statistics."}
        
        llm_resp = json.loads(call_llm(sys_prompt, user_prompt, mock_resp))
        summary = llm_resp.get("summary", "No summary generated")

        fact_item = context_pb2.MemoryItem(
            id="fact_001",
            type="Fact",
            status="validated",
            source="executor",
            confidence=0.9,
            content_json=json.dumps({
                "execution_output": output,
                "summary": summary
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=fact_item))

        print(json.dumps({
            "job_id": job_id,
            "llm_summary": summary,
            "execution_output_preview": output[:50]
        }))
        
    except Exception as e:
        logger.exception("Executor failed")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
