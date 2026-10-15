#!/bin/sh
set -eu
checksum="$(printf 'mirror-neuron-demo' | sha256sum | cut -d' ' -f1)"
printf '%s\n' '__MN_EVENT__{"type":"agent_activity","payload":{"message":"Calculated the demo artifact checksum","activity_kind":"result","owner_blueprint":"demo_docker_worker"}}'
printf '{"complete_step":{"demo":"demo_docker_worker","runner":"docker_worker","sha256":"%s"},"next_state":{"sha256":"%s"}}\n' "$checksum" "$checksum"
