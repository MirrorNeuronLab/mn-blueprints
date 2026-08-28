FROM ghcr.io/nvidia/openshell-community/sandboxes/base:latest@sha256:aeef1c63f00e2913ea002ccb3aaf925f338b5c5d70e63576f0d95c16a138044e

USER root
RUN mkdir -p /sandbox/job \
    && chown -R sandbox:sandbox /sandbox

USER sandbox
