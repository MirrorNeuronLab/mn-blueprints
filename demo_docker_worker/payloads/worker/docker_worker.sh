#!/bin/sh
set -eu
checksum="$(printf 'mirror-neuron-demo' | sha256sum | cut -d' ' -f1)"
printf '{"complete_step":{"demo":"demo_docker_worker","runner":"docker_worker","sha256":"%s"},"next_state":{"sha256":"%s"}}\n' "$checksum" "$checksum"
