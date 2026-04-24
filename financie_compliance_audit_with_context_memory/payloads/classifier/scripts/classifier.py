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

        res = stub.GetContext(context_pb2.GetContextRequest(job_id=job_id, agent_role="risk_classifier", focus_id=focus_id, max_items=10))
        seen_types = [i.type for i in res.items]

        ra = context_pb2.MemoryItem(
            id="risk_assessment_1",
            type="RiskAssessment",
            status="validated",
            source="risk_classifier",
            content_json=json.dumps({
                "policy_id": "FEE_DISCLOSURE_001",
                "status": "potential_violation",
                "risk_level": "medium",
                "reasoning": "Agent mentioned fee after waiver."
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=ra))
        stub.LinkItems(context_pb2.LinkItemsRequest(job_id=job_id, source_id=focus_id, target_id="risk_assessment_1", relation="assesses"))

        print(json.dumps({"job_id": job_id, "focus_id": focus_id, "seen_by_classifier": seen_types}))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__": main()
