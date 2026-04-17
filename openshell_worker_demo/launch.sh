#!/usr/bin/env bash
set -euo pipefail

if [ -z "${MIRROR_NEURON_HOME:-}" ]; then
  echo "Error: MIRROR_NEURON_HOME environment variable is not set."
  echo "Please set it to the root directory of the MirrorNeuron repository."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Validating openshell_worker_demo bundle..."
"${MIRROR_NEURON_HOME}/mn" validate "$SCRIPT_DIR"

echo "Running..."
"${MIRROR_NEURON_HOME}/mn" run "$SCRIPT_DIR"
