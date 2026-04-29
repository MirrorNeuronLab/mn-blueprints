import json
import os
import sys
from pathlib import Path
import grpc
import context_pb2
import context_pb2_grpc

def call_llm(system_prompt, user_prompt, mock_response):
    quick_mode = os.environ.get("MN_BLUEPRINT_QUICK_TEST", "").strip().lower() in {"1", "true", "yes", "on"}
    if quick_mode:
        print("STATUS: quick test mode enabled; using mock LLM response.", file=sys.stderr)
        return json.dumps(mock_response)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY not set. Falling back to mock response.", file=sys.stderr)
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
        print(f"LLM Error: {str(e)}. Falling back to mock.", file=sys.stderr)
        return json.dumps(mock_response)

def main():
    try:
        input_data = json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())
        source = input_data.get("input", input_data)
        job_id = source.get("job_id", "job_ctx_123")
        goal = source.get("goal", "Default Goal")
        
        channel = grpc.insecure_channel('host.docker.internal:50052') 
        stub = context_pb2_grpc.ContextEngineStub(channel)
        
        # Use LLM to generate the command and hypothesis
        sys_prompt = "You are a network planner. You translate goals into linux bash commands. Output JSON with 'command' and 'theory' fields."
        user_prompt = f"Goal: {goal}"
        
        mock_resp = {"command": "ping -c 2 127.0.0.1", "theory": "Network is probably slow"}
        llm_response = json.loads(call_llm(sys_prompt, user_prompt, mock_resp))
        
        task_cmd = llm_response.get("command", "ping -c 2 127.0.0.1")
        theory = llm_response.get("theory", "Unknown hypothesis")

        task_item = context_pb2.MemoryItem(
            id="task_001",
            type="Task",
            status="validated",
            source="planner",
            confidence=1.0,
            content_json=json.dumps({
                "goal": goal,
                "command": task_cmd,
                "priority": "high",
                "internal_notes": "Generated via LLM."
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=task_item))
        
        hypo_item = context_pb2.MemoryItem(
            id="hypo_001",
            type="Hypothesis",
            status="draft",
            source="planner",
            confidence=0.5,
            content_json=json.dumps({
                "theory": theory
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=hypo_item))
        
        stub.LinkItems(context_pb2.LinkItemsRequest(
            job_id=job_id,
            source_id="task_001",
            target_id="hypo_001",
            relation="based_on"
        ))

        print(json.dumps({
            "job_id": job_id,
            "focus_id": "task_001",
            "message": "Plan stored in Working Memory via LLM"
        }))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
