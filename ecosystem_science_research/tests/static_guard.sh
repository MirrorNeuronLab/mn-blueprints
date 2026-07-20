#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if rg -n 'Runtime\.deliver|MirrorNeuron\.Runtime|Runner\.HostLocal|Runner\.OpenShell|Runner\.Docker' "$ROOT/payloads/beam"; then
  echo "forbidden simulation transport or runner reference found" >&2
  exit 1
fi

if rg -n '"agent_type"\s*:\s*"(docker|openshell|host_local)"|"runner"\s*:\s*"(docker|openshell|host_local)"' "$ROOT/manifest.json"; then
  echo "forbidden non-native worker configured" >&2
  exit 1
fi

test "$(find "$ROOT/payloads/beam" -name '*.ex' -type f | wc -l | tr -d ' ')" -eq 9
echo "static guard passed"
