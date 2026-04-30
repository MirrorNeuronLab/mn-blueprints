from mn_sdk import RetryPolicy, RunnerConfig, agent, workflow
from existing_research import collect_research_summary, save_summary


TOPIC = "electric vehicle charging adoption in New England"
RETRY = RetryPolicy(max_attempts=2, backoff_ms=250)
RUNNER = RunnerConfig.host_local()


class ResearchAgents:
    @agent.defn(name="ingress", type="map", runner=RUNNER, retries=RETRY, timeout_seconds=10)
    def ingress(self, topic: str):
        return {
            "message_type": "research_request",
            "topic": topic,
            "text": "Collect a short research summary.",
        }

    @agent.defn(name="retriever", type="map", runner=RUNNER, retries=RETRY, timeout_seconds=10)
    def retriever(self, request):
        summary = collect_research_summary(
            topic=request["topic"],
            instructions=request["text"],
        )
        return {"message_type": "research_summary", "summary": summary}

    @agent.defn(name="reviewer", type="reduce", runner=RUNNER, retries=RETRY, timeout_seconds=10)
    def reviewer(self, result):
        saved_path = save_summary(result["summary"])
        return {"status": "saved", "path": saved_path, "summary": result["summary"]}


@workflow.defn(name="general_python_defined_basic_v1", recovery_mode="cluster_recover")
class GeneralPythonDefinedBasic:
    def __init__(self):
        self.agents = ResearchAgents()

    @workflow.run
    def run(self):
        request = self.agents.ingress(workflow.input("topic", default=TOPIC))
        result = self.agents.retriever(request)
        return self.agents.reviewer(result)
