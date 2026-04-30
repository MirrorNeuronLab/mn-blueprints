from mn_sdk import BackpressurePolicy, RetryPolicy, RunnerConfig, agent, workflow
from daemon_helpers import build_probe, evaluate_probe, remember_decision


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


class DaemonAgents:
    @agent.defn(
        name="daemon_ingress",
        type="stream",
        runner=RUNNER,
        retries=RETRY,
        backpressure=STREAM_BACKPRESSURE,
        timeout_seconds=10,
    )
    def ingress(self, service: str):
        return build_probe(service)

    @agent.defn(
        name="daemon_analyzer",
        type="stream",
        runner=RUNNER,
        retries=RETRY,
        backpressure=STREAM_BACKPRESSURE,
        timeout_seconds=10,
    )
    def analyzer(self, probe):
        return evaluate_probe(probe)

    @agent.defn(
        name="daemon_memory",
        type="stream",
        runner=RUNNER,
        retries=RETRY,
        backpressure=STREAM_BACKPRESSURE,
        timeout_seconds=10,
    )
    def memory(self, decision):
        return remember_decision(decision)


@workflow.defn(
    name="general_python_defined_advanced_deamon_v1",
    daemon=True,
    stream_mode="live",
    recovery_mode="cluster_recover",
    backpressure=JOB_BACKPRESSURE,
)
class GeneralPythonDefinedAdvancedDeamon:
    def __init__(self):
        self.agents = DaemonAgents()

    @workflow.run
    def run(self):
        probe = self.agents.ingress(workflow.input("service", default=SERVICE))
        decision = self.agents.analyzer(probe)
        return self.agents.memory(decision)
