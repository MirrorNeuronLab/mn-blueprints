from datetime import datetime, timezone


def build_probe(service: str) -> dict:
    return {
        "service": service,
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "signals": {"queue_depth": 3, "error_rate": 0.01, "latency_ms": 42},
    }


def evaluate_probe(probe: dict) -> dict:
    signals = probe["signals"]
    healthy = signals["queue_depth"] < 10 and signals["error_rate"] < 0.05
    return {
        "service": probe["service"],
        "healthy": healthy,
        "severity": "ok" if healthy else "warn",
        "reason": f"queue={signals['queue_depth']} error_rate={signals['error_rate']}",
        "observed_at": probe["observed_at"],
    }


def remember_decision(decision: dict) -> dict:
    return {
        "last_decision": decision,
        "heartbeat_count": 1,
        "status": "daemon_observed",
    }
