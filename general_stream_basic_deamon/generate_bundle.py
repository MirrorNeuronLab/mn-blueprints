#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "mn-skills" / "blueprint_support_skill" / "src"),
)
from mn_blueprint_support import apply_quick_test, log_status, progress, write_manifest


def build_manifest(args: argparse.Namespace) -> dict:
    return {
        "manifest_version": "1.0",
        "graph_id": "general_stream_basic_deamon_v1",
        "job_name": "general_stream_basic_deamon",
        "daemon": True,
        "entrypoints": ["ingress"],
        "initial_inputs": {
            "ingress": [
                {
                    "scenario": "telemetry_stream",
                    "description": "Continuously produce gzipped NDJSON telemetry chunks between stream agents until manually cancelled."
                }
            ]
        },
        "nodes": [
            {
                "node_id": "ingress",
                "agent_type": "router",
                "type": "map",
                "role": "root_coordinator",
                "config": {"emit_type": "stream_start"},
            },
            {
                "node_id": "telemetry_source",
                "agent_type": "module",
                "type": "stream",
                "role": "producer",
                "config": {
                    "module": "MirrorNeuron.Examples.StreamBasicDaemon.TelemetrySource",
                    "module_source": "beam_modules/telemetry_source.ex",
                    "interval_ms": args.interval_ms,
                    "chunk_size": args.chunk_size,
                    "baseline": args.baseline,
                    "jitter": args.jitter,
                    "peak_height": args.peak_height,
                    "peak_every": args.peak_every,
                    "device_id": args.device_id,
                    "content_encoding": args.content_encoding,
                    "target_node": "peak_detector",
                },
            },
            {
                "node_id": "peak_detector",
                "agent_type": "executor",
                "type": "stream",
                "role": "consumer",
                "config": {
                    "runner_module": "MirrorNeuron.Runner.HostLocal",
                    "upload_path": "stream_worker",
                    "upload_as": "stream_worker",
                    "workdir": "/sandbox/job/stream_worker",
                    "command": ["python3", "scripts/detect_stream_peaks.py"],
                    "output_message_type": None,
                    "environment": {
                        "WARMUP_POINTS": str(args.warmup_points),
                        "WINDOW_SIZE": str(args.window_size),
                        "SPIKE_MULTIPLIER": str(args.spike_multiplier),
                        "MIN_SPIKE_DELTA": str(args.min_spike_delta),
                    },
                },
            },
        ],
        "edges": [
            {
                "edge_id": "ingress_to_source",
                "from_node": "ingress",
                "to_node": "telemetry_source",
                "message_type": "stream_start",
            },
            {
                "edge_id": "source_to_detector",
                "from_node": "telemetry_source",
                "to_node": "peak_detector",
                "message_type": "telemetry_chunk",
            },
        ],
        "policies": {"recovery_mode": "cluster_recover", "stream_mode": "live"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the basic live stream daemon bundle.")
    parser.add_argument("--chunk-size", type=int, default=6)
    parser.add_argument("--interval-ms", type=int, default=1000)
    parser.add_argument("--baseline", type=int, default=24)
    parser.add_argument("--jitter", type=int, default=4)
    parser.add_argument("--peak-height", type=int, default=55)
    parser.add_argument("--peak-every", type=int, default=20)
    parser.add_argument("--device-id", default="sensor-alpha")
    parser.add_argument("--content-encoding", default="gzip", choices=["gzip", "identity"])
    parser.add_argument("--warmup-points", type=int, default=5)
    parser.add_argument("--window-size", type=int, default=8)
    parser.add_argument("--spike-multiplier", type=float, default=2.4)
    parser.add_argument("--min-spike-delta", type=float, default=20.0)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Generate a short deterministic stream for fast validation.",
    )
    args = parser.parse_args()

    quick_test = apply_quick_test(
        args,
        {
            "chunk_size": 3,
            "interval_ms": 250,
            "peak_every": 6,
            "content_encoding": "identity",
            "warmup_points": 2,
            "window_size": 4,
        },
    )
    log_status(
        "general_stream_basic_deamon",
        "generating basic stream daemon bundle",
        phase="generate",
        details={"quick_test": quick_test, "chunk_size": args.chunk_size},
    )

    args.chunk_size = max(args.chunk_size, 1)
    args.interval_ms = max(args.interval_ms, 1)
    args.peak_every = max(args.peak_every, 1)

    bundle_dir = args.output_dir

    bundle_dir.mkdir(parents=True, exist_ok=True)
    payloads_dir = bundle_dir / "payloads"
    payloads_dir.mkdir(parents=True, exist_ok=True)
    if bundle_dir.resolve() != Path(__file__).resolve().parent:
        shutil.copytree(Path(__file__).resolve().parent / "payloads", payloads_dir, dirs_exist_ok=True)

    manifest = build_manifest(args)
    write_manifest(
        bundle_dir / "manifest.json",
        manifest,
        blueprint_id="general_stream_basic_deamon",
        quick_test=quick_test,
    )
    print(progress("bundle generated", 1, 1), file=sys.stderr)
    print(bundle_dir)


if __name__ == "__main__":
    main()
