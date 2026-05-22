#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse


def main() -> int:
    uri = video_source_uri()
    parsed = urlparse(uri)
    if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.netloc:
        print("video_source.uri must be an rtsp:// or rtsps:// URL", file=sys.stderr)
        return 2

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        print("ffprobe is required to validate RTSP video streams", file=sys.stderr)
        return 2

    command = [
        ffprobe,
        "-v",
        "error",
        "-rtsp_transport",
        os.environ.get("FFMPEG_RTSP_TRANSPORT", "tcp"),
        "-rw_timeout",
        str(int(float(os.environ.get("RTSP_VALIDATE_TIMEOUT_SECONDS", "5")) * 1_000_000)),
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "csv=p=0",
        uri,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    if result.returncode != 0 or "video" not in result.stdout.lower():
        detail = (result.stderr or result.stdout or "no video stream reported").strip()
        print(f"RTSP video stream is not reachable: {detail}", file=sys.stderr)
        return 1

    print(f"RTSP video stream validated: {uri}")
    return 0


def video_source_uri() -> str:
    config = {}
    raw_config = os.environ.get("MN_BLUEPRINT_CONFIG_JSON")
    if raw_config:
        try:
            config = json.loads(raw_config)
        except json.JSONDecodeError:
            config = {}
    video_source = config.get("video_source") if isinstance(config, dict) else {}
    uri = video_source.get("uri") if isinstance(video_source, dict) else None
    return str(uri or os.environ.get("VIDEO_SOURCE_URI") or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
