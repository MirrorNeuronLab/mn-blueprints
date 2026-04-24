import json
import os
import sys
from pathlib import Path

import context_pb2
import context_pb2_grpc
import grpc

def main():
    try:
        input_data = json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())
        
        if "input" in input_data:
            source = input_data["input"]
        else:
            source = input_data
            
        job_id = source.get("job_id", "job_ctx_123")
        goal = source.get("goal", "Default Goal")
        
        # Use host network to reach rust grpc server running on host
        # If in openshell container, use host.docker.internal
        channel = grpc.insecure_channel('host.docker.internal:50052') 
        stub = context_pb2_grpc.ContextEngineStub(channel)
        
        # Check if stub can connect (add dummy fact) to catch network errors early
        try:
            task_item = context_pb2.MemoryItem(
                id="task_001",
                type="Task",
                status="validated",
                source="planner",
                confidence=1.0,
                content_json=json.dumps({
                    "goal": goal,
                    "command": "ping -c 2 127.0.0.1",
                    "priority": "high",
                    "internal_notes": "We are just testing networking."
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
                    "theory": "Network is probably slow"
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
        except Exception as grpc_err:
            print(json.dumps({"error": f"GRPC connection failed: {str(grpc_err)}"}), file=sys.stderr)
            sys.exit(1)

        print(json.dumps({
            "job_id": job_id,
            "focus_id": "task_001",
            "message": "Plan stored in Working Memory"
        }))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
