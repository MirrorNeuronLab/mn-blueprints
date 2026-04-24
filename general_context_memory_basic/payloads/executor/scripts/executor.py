import json
import os
import sys
from pathlib import Path
import subprocess

import context_pb2
import context_pb2_grpc
import grpc

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
        
        try:
            response = stub.GetContext(context_pb2.GetContextRequest(
                job_id=job_id,
                agent_role="executor", 
                focus_id=focus_id,
                max_items=5
            ))
        except Exception as grpc_err:
            print(json.dumps({"error": f"GRPC connection failed: {str(grpc_err)}"}), file=sys.stderr)
            sys.exit(1)
        
        items_received = []
        task_command = None
        
        for item in response.items:
            content = json.loads(item.content_json)
            items_received.append(item.type)
            
            if item.type == "Task":
                task_command = content.get("command")
                
        if task_command:
            result = subprocess.run(task_command.split(), capture_output=True, text=True)
            output = result.stdout
        else:
            output = "No command found in context"
            
        fact_item = context_pb2.MemoryItem(
            id="fact_001",
            type="Fact",
            status="validated",
            source="executor",
            confidence=0.9,
            content_json=json.dumps({"execution_output": output}),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=fact_item))

        print(json.dumps({
            "job_id": job_id,
            "items_in_context": items_received,
            "execution_output_preview": output[:50],
            "note": "Hypothesis should not be in items_in_context!"
        }))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
