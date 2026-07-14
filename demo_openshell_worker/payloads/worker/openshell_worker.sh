#!/bin/sh
set -eu

printf '%s\n' '{"events":[{"type":"openshell_policy_verified","payload":{"network_policy":"deny-all"}}],"complete_step":{"config_valid":true,"network_policy":"deny-all","runner":"openshell"},"next_state":{"config_valid":true,"network_policy":"deny-all","runner":"openshell"}}'
