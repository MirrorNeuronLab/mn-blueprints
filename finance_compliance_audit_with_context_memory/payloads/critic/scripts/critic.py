import json, os, sys, grpc
from pathlib import Path
import context_pb2, context_pb2_grpc

def call_llm(system_prompt, user_prompt, mock_response):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY not set. Falling back to mock response.", file=sys.stderr)
        return json.dumps(mock_response)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {str(e)}. Falling back to mock.", file=sys.stderr)
        return json.dumps(mock_response)

def main():
    try:
        input_data = json.loads(Path(os.environ["MIRROR_NEURON_INPUT_FILE"]).read_text())
        source = json.loads(input_data["sandbox"]["stdout"]) if "sandbox" in input_data else input_data.get("input", input_data)
        job_id, focus_id = source["job_id"], source["focus_id"]

        channel = grpc.insecure_channel('host.docker.internal:50052')
        stub = context_pb2_grpc.ContextEngineStub(channel)

        res = stub.GetContext(context_pb2.GetContextRequest(job_id=job_id, agent_role="critic_auditor", focus_id=focus_id, max_items=10))
        context_str = "\n".join([f"[{item.type}]: {item.content_json}" for item in res.items])

        sys_prompt = "You are a Critic Auditor. Challenge the final decision based on the evidence. Is it a false positive? Output JSON with 'audit_result' (decision_supported or rejected), 'correction_needed' (boolean), and 'auditor_note'."
        user_prompt = f"Context:\n{context_str}\n\nTask: Perform final audit on the decision."

        mock_resp = {
            "audit_result": "decision_supported",
            "correction_needed": False,
            "auditor_note": "The cited evidence supports the failed status."
        }
        llm_response = json.loads(call_llm(sys_prompt, user_prompt, mock_resp))

        ar = context_pb2.MemoryItem(
            id="audit_result_1",
            type="AuditResult",
            status="validated",
            source="critic_auditor",
            content_json=json.dumps(llm_response),
            version=1
        )
        stub.AddItem(context_pb2.AddItemRequest(job_id=job_id, item=ar))
        
        outputs = {
            "job_id": job_id, 
            "focus_id": focus_id, 
            "seen_by_critic": [i.type for i in res.items],
            "llm_audit_output": llm_response
        }
        print(json.dumps(outputs))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__": main()
