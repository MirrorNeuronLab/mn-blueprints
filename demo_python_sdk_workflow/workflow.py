import os

try:
    from mn_sdk import agent, workflow
except ModuleNotFoundError as exc:
    if exc.name != "mn_sdk":
        raise

    # The compiler imports the real SDK, but the generated worker only needs
    # the decorators to load this source module.  Keep the compiled bundle
    # runnable in the runtime's minimal Python worker environment.
    class _Agent:
        @staticmethod
        def defn(*args, **kwargs):
            def decorate(function):
                return function

            return decorate

    class _Workflow:
        @staticmethod
        def defn(*args, **kwargs):
            def decorate(cls):
                return cls

            return decorate

        @staticmethod
        def run(function):
            return function

    agent = _Agent()
    workflow = _Workflow()


class IncidentAgents:
    @agent.defn(name="normalize", type="map", runner="host_local", timeout_seconds=10)
    def normalize(self, incident=None):
        # Core versions that do not yet preserve SDK call arguments still
        # invoke the compiled method with an empty input payload.  This demo
        # intentionally has one deterministic fixture, so keep that path
        # runnable while retaining the declared SDK input when it is present.
        if incident is None:
            incident = {"service": "checkout", "severity": 2}
        return {"service": incident["service"], "severity": int(incident["severity"]), "normalized": True}

    @agent.defn(name="summarize", type="reduce", runner="host_local", timeout_seconds=10)
    def summarize(self, incident=None):
        from run_store import write_run_store

        if incident is None:
            incident = {"service": "checkout", "severity": 2, "normalized": True}
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
