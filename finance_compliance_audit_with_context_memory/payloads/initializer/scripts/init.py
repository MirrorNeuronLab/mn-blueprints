import json, os, sys, grpc
from pathlib import Path
import context_pb2, context_pb2_grpc

def main():
    try:
        input_data = json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())
        source = input_data.get("input", input_data)
        job_id = source.get("job_id", "audit_job_777")
        focus_id = source.get("focus_id", "audit_task_1")

        channel = grpc.insecure_channel('host.docker.internal:50052')
        stub = context_pb2_grpc.ContextEngineStub(channel)

        # 1. Add Task
        task = context_pb2.MemoryItem(
            id=focus_id,
            type="Task",
            status="validated",
            source="system",
            content_json=json.dumps({"goal": "Perform financial compliance audit"}),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=task))

        # 2. Add Raw Transcript
        transcript = context_pb2.MemoryItem(
            id="transcript_1",
            type="RawTranscript",
            status="validated",
            source="system",
            content_json=json.dumps({
                "call_id": "C_992",
                "text": "Agent: I can waive that fee for you today. Customer: Oh, okay. Agent: The fee is $50. Do you agree?"
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=transcript))
        stub.LinkItems(context_pb2.LinkItemsRequest(job_id=job_id, source_id=focus_id, target_id="transcript_1", relation="has_transcript"))

        # 3. Add Policy Document
        policy = context_pb2.MemoryItem(
            id="policy_1",
            type="PolicyDocument",
            status="validated",
            source="system",
            content_json=json.dumps({
                "rule_id": "FEE_DISCLOSURE_001",
                "text": "Agent must clearly disclose any fee before confirming customer agreement."
            }),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=policy))
        stub.LinkItems(context_pb2.LinkItemsRequest(job_id=job_id, source_id=focus_id, target_id="policy_1", relation="has_policy"))

        print(json.dumps({"job_id": job_id, "focus_id": focus_id}))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__": main()
