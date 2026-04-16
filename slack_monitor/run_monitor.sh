#!/usr/bin/env bash
set -euo pipefail

if [ -z "${MIRROR_NEURON_HOME:-}" ]; then
  echo "Error: MIRROR_NEURON_HOME environment variable is not set."
  echo "Please set it to the root directory of the MirrorNeuron repository."
  exit 1
fi
ROOT_DIR="$MIRROR_NEURON_HOME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"





# Verify the monitor runs
echo "Validating bundle..."
"$ROOT_DIR/mirror_neuron" validate "$SCRIPT_DIR"

echo "Starting slack monitor in MirrorNeuron runtime..."
echo "Press Ctrl+C to stop."

# Run the monitor continuously
"$ROOT_DIR/mirror_neuron" run "$SCRIPT_DIR"
