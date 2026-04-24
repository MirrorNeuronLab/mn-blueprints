import json, os, sys, grpc
from pathlib import Path
import context_pb2, context_pb2_grpc

def main():
    try:
        input_data = json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())
        source = json.loads(input_data["sandbox"]["stdout"]) if "sandbox" in input_data else input_data.get("input", input_data)
        job_id, focus_id = source["job_id"], source["focus_id"]

        channel = grpc.insecure_channel('host.docker.internal:50052')
        stub = context_pb2_grpc.ContextEngineStub(channel)

        res = stub.GetContext(context_pb2.GetContextRequest(job_id=job_id, agent_role="critic_auditor", focus_id=focus_id, max_items=10))
        seen_types = [i.type for i in res.items]

        ar = context_pb2.MemoryItem(
            id="audit_result_1",
            type="AuditResult",
            status="validated",
            source="critic_auditor",
            content_json=json.dumps({
                "audit_result": "decision_supported",
                "correction_needed": False
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=ar))
        
        # Pull everything we saw along the chain
        outputs = {
            "job_id": job_id, 
            "focus_id": focus_id, 
            "seen_by_critic": seen_types,
            "final_audit": "decision_supported",
            "previous_steps": source
        }
        print(json.dumps(outputs))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__": main()
