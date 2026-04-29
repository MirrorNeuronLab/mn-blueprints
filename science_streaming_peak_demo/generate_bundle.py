#!/usr/bin/env python3
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "mn-skills" / "blueprint_support_skill" / "src"),
)
from mn_blueprint_support import apply_quick_test, log_status, progress, write_manifest


def parse_peak_positions(value: str, sample_count: int) -> list[int]:
    if not value:
        return sorted({max(sample_count // 3, 1), max((sample_count * 2) // 3, 1)})

    positions = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        index = int(item)
        if 1 <= index <= sample_count:
            positions.append(index)

    return sorted(set(positions))


def build_manifest(args: argparse.Namespace) -> dict:
    return {
        "manifest_version": "1.0",
        "graph_id": "science_streaming_peak_demo_v1",
        "job_name": "streaming-peak-demo",
        "entrypoints": ["ingress"],
        "initial_inputs": {
            "ingress": [
                {
                    "scenario": "telemetry_stream",
                    "description": "Produce gzipped NDJSON telemetry chunks and detect abnormal peaks."
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
                "agent_type": "executor",
                "type": "stream",
                "role": "producer",
                "config": {
                    "runner_module": "MirrorNeuron.Runner.HostLocal",
                    "upload_path": "stream_worker",
                    "upload_as": "stream_worker",
                    "workdir": "/sandbox/job/stream_worker",
                    "command": ["python3", "scripts/emit_telemetry_stream.py"],
                    "output_message_type": None,
                    "environment": {
                        "SAMPLE_COUNT": str(args.sample_count),
                        "CHUNK_SIZE": str(args.chunk_size),
                        "BASELINE": str(args.baseline),
                        "JITTER": str(args.jitter),
                        "PEAK_HEIGHT": str(args.peak_height),
                        "PEAK_POSITIONS": ",".join(str(position) for position in args.peak_positions),
                        "DEVICE_ID": args.device_id,
                        "STREAM_CONTENT_ENCODING": args.content_encoding,
                    },
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
        "policies": {"recovery_mode": "cluster_recover"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the streaming peak detection bundle.")
    parser.add_argument("--sample-count", type=int, default=60)
    parser.add_argument("--chunk-size", type=int, default=6)
    parser.add_argument("--baseline", type=int, default=24)
    parser.add_argument("--jitter", type=int, default=4)
    parser.add_argument("--peak-height", type=int, default=55)
    parser.add_argument("--peak-positions", default="")
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
            "sample_count": 12,
            "chunk_size": 3,
            "peak_positions": "4,9",
            "content_encoding": "identity",
            "warmup_points": 2,
            "window_size": 4,
        },
    )
    log_status(
        "science_streaming_peak_demo",
        "generating streaming peak bundle",
        phase="generate",
        details={"quick_test": quick_test, "sample_count": args.sample_count},
    )

    args.sample_count = max(args.sample_count, 1)
    args.chunk_size = max(args.chunk_size, 1)
    args.peak_positions = parse_peak_positions(args.peak_positions, args.sample_count)

    bundle_name = (
        f"science_streaming_peak_demo_{args.sample_count}_samples_"
        f"{args.chunk_size}_chunk_{args.content_encoding}"
    )

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
        blueprint_id="science_streaming_peak_demo",
        quick_test=quick_test,
    )
    print(progress("bundle generated", 1, 1), file=sys.stderr)
    print(bundle_dir)


if __name__ == "__main__":
    main()
