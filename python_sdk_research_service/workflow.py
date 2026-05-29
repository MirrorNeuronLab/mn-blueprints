import json

try:
    from mn_sdk import BackpressurePolicy, RetryPolicy, RunnerConfig, agent, workflow
except ModuleNotFoundError as error:
    if error.name not in {"grpc", "mn_sdk"}:
        raise
    from mn_blueprint_support.python_sdk_compat import BackpressurePolicy, RetryPolicy, RunnerConfig, agent, workflow

from service_health_simulation import build_probe, evaluate_probe, remember_decision


SERVICE = "charging-station-health"
RUNNER = RunnerConfig.host_local()
RETRY = RetryPolicy(max_attempts=2, backoff_ms=250)
JOB_BACKPRESSURE = {
    "strategy": "bounded_queue",
    "external_input": "retry_later",
    "propagation": "downstream_to_upstream",
}
STREAM_BACKPRESSURE = BackpressurePolicy(
    max_queue_depth=6,
    high_watermark=3,
    low_watermark=1,
    retry_after_ms=500,
)


class ServiceAgents:
    @agent.defn(
        name="service_ingress",
        type="stream",
        runner=RUNNER,
        retries=RETRY,
        backpressure=STREAM_BACKPRESSURE,
        timeout_seconds=10,
    )
    def ingress(self, service: str):
        return build_probe(service)

    @agent.defn(
        name="service_analyzer",
        type="stream",
        runner=RUNNER,
        retries=RETRY,
        backpressure=STREAM_BACKPRESSURE,
        timeout_seconds=10,
    )
    def analyzer(self, probe):
        return evaluate_probe(probe)

    @agent.defn(
        name="service_memory",
        type="stream",
        runner=RUNNER,
        retries=RETRY,
        backpressure=STREAM_BACKPRESSURE,
        timeout_seconds=10,
    )
    def memory(self, decision):
        return remember_decision(decision)


@workflow.defn(
    name="python_sdk_research_service_v1",
    type="service",
    stream_mode="live",
    recovery_mode="cluster_recover",
    backpressure=JOB_BACKPRESSURE,
)
class GeneralPythonSdkLiveResearchService:
    def __init__(self):
        self.agents = ServiceAgents()

    @workflow.run
    def run(self):
        probe = self.agents.ingress(workflow.input("service", default=SERVICE))
        decision = self.agents.analyzer(probe)
        return self.agents.memory(decision)


def run_local(service: str = SERVICE) -> dict:
    """Run one service tick directly for local venv smoke tests."""

    agents = ServiceAgents()
    probe = agents.ingress(service)
    decision = agents.analyzer(probe)
    return agents.memory(decision)


if __name__ == "__main__":
    print(json.dumps(run_local(), indent=2, sort_keys=True))
