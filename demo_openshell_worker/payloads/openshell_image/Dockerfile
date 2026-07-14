FROM mirror-neuron-core:latest

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 sandbox \
    && useradd --uid 1000 --gid sandbox --create-home --shell /bin/bash sandbox \
    && mkdir -p /sandbox/job \
    && chown -R sandbox:sandbox /sandbox
