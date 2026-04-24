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

        res = stub.GetContext(context_pb2.GetContextRequest(job_id=job_id, agent_role="evidence_extractor", focus_id=focus_id, max_items=10))
        seen_types = [i.type for i in res.items]

        se = context_pb2.MemoryItem(
            id="structured_evidence_1",
            type="StructuredEvidence",
            status="validated",
            source="evidence_extractor",
            content_json=json.dumps({
                "evidence_items": [
                    {"speaker": "agent", "quote": "I can waive that fee for you today."},
                    {"speaker": "agent", "quote": "The fee is $50. Do you agree?"}
                ]
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=se))
        stub.LinkItems(context_pb2.LinkItemsRequest(job_id=job_id, source_id=focus_id, target_id="structured_evidence_1", relation="extracts"))

        print(json.dumps({"job_id": job_id, "focus_id": focus_id, "seen_by_extractor": seen_types}))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__": main()
