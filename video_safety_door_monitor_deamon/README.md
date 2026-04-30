# Video Safety Door Monitor Daemon

A live 24/7 door-camera monitoring blueprint. It samples a camera feed or looping demo video, sends representative frames to Nemotron 3 through Ollama, and posts a Slack alert when a person is detected.

Default model endpoint:

```bash
OLLAMA_BASE_URL=http://192.168.4.173:11434
OLLAMA_MODEL=nemotron3:33b
```

The blueprint treats video as sampled images because Ollama multimodal models accept image inputs. For RTSP/HTTP cameras, local MP4 files, or demo clips, the worker extracts one JPEG frame per tick and asks the model for strict JSON:

```json
{"person_detected": true, "confidence": 0.83, "summary": "A person is standing near the door.", "risk_level": "medium"}
```

## Run

```bash
mn run mn-blueprints/video_safety_door_monitor_deamon
```

For a real camera:

```bash
VIDEO_SOURCE_URI=rtsp://user:pass@camera.local/stream1 \
SLACK_BOT_TOKEN=xoxb-... \
SLACK_DEFAULT_CHANNEL=#safety \
mn run mn-blueprints/video_safety_door_monitor_deamon
```

For a demo clip:

```bash
cd mn-blueprints/video_safety_door_monitor_deamon
python3 payloads/person_detector/scripts/download_sample_video.py
VIDEO_SOURCE_URI=samples/door-demo.mp4 mn run .
```

The download script stores the clip at `payloads/person_detector/samples/door-demo.mp4`, which is uploaded as `samples/door-demo.mp4` inside the worker sandbox. The monitor loops the clip forever by advancing the extraction timestamp and wrapping back to the start.

The default demo URL is Intel's archived `people-detection.mp4` sample video, licensed CC-BY-4.0.

## Configuration

- `VIDEO_SOURCE_URI`: RTSP URL, HTTP URL, local MP4/MOV/WebM path, or local image path. Defaults to `samples/door-demo.mp4`.
- `FRAME_SAMPLE_SECONDS`: seconds between sampled positions inside a file or stream. Defaults to `5.0`.
- `FRAME_JPEG_MAX_WIDTH`: maximum JPEG width passed to the model. Defaults to `896`.
- `OLLAMA_BASE_URL`: Ollama API base URL. Defaults to `http://192.168.4.173:11434`.
- `OLLAMA_MODEL`: model name. Defaults to `nemotron3:33b`.
- `OLLAMA_THINK`: whether to allow thinking output from Ollama. Defaults to `false`; this is important for `nemotron3:33b`, which can otherwise place content in `thinking` while returning an empty `response`.
- `PERSON_DETECTION_CONFIDENCE_THRESHOLD`: minimum confidence for an alert. Defaults to `0.65`.
- `PERSON_ALERT_COOLDOWN_SECONDS`: per-camera alert cooldown. Defaults to `60`.
- `SLACK_ALERT_ENABLED`: set to `false` to dry-run alerts. Defaults to `true`.
- `SLACK_BOT_TOKEN` or `MIRROR_NEURON_SLACK_BOT_TOKEN`: Slack bot token.
- `SLACK_DEFAULT_CHANNEL` or `MIRROR_NEURON_SLACK_DEFAULT_CHANNEL`: Slack channel.

## Quick Test

Generate a fast dry-run bundle:

```bash
MN_BLUEPRINT_QUICK_TEST=1 python3 generate_bundle.py --quick-test --output-dir /tmp/video-door-monitor-quick
```

Quick test disables Slack and uses deterministic mock VLM output unless `OLLAMA_LIVE_IN_QUICK_TEST=1` is set.

## Operational Notes

- Install `ffmpeg` on workers that read video files or RTSP streams, or provide Python OpenCV (`cv2`) as a fallback.
- The detector emits `door_camera_frame_analyzed`, `door_camera_person_detected`, `door_camera_slack_alert_sent`, and `door_camera_slack_alert_skipped` events.
- Slack delivery is cooldown-gated so a person standing in frame does not spam a channel.
- This blueprint is a monitoring aid, not a safety-critical access-control system. Keep physical safety systems independent.
