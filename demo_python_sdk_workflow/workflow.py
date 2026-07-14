import os

from mn_sdk import agent, workflow


class IncidentAgents:
    @agent.defn(name="normalize", type="map", runner="host_local", timeout_seconds=10)
    def normalize(self, incident):
        return {"service": incident["service"], "severity": int(incident["severity"]), "normalized": True}

    @agent.defn(name="summarize", type="reduce", runner="host_local", timeout_seconds=10)
    def summarize(self, incident):
        from run_store import write_run_store

        result = {"status": "ready", "incident": incident, "compiler": "mn-python-sdk"}
        os.environ.setdefault("MN_DEMO_ID", "demo_python_sdk_workflow")
        write_run_store(
            result,
            [{"type": "python_workflow_compiled", "payload": {"agents": ["normalize", "summarize"]}}],
        )
        return result


@workflow.defn(name="demo_python_sdk_workflow_v1", recovery_mode="local_restart")
class DemoPythonSdkWorkflow:
    def __init__(self):
        self.agents = IncidentAgents()

    @workflow.run
    def run(self):
        normalized = self.agents.normalize({"service": "checkout", "severity": 2})
        return self.agents.summarize(normalized)
