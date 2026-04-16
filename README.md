# MirrorNeuron Blueprints

This repository contains examples and blueprints for running workflows with [MirrorNeuron](https://github.com/MirrorNeuron/MirrorNeuron).

## Prerequisites

Before running these blueprints, ensure you have the `MirrorNeuron` repository cloned and built locally.

You must set the `MIRROR_NEURON_HOME` environment variable to point to your `MirrorNeuron` directory.

```bash
export MIRROR_NEURON_HOME=/path/to/MirrorNeuron
```

## Running the Examples

Each example is located in its own subdirectory and contains a runner script. For example, to run the `streaming_peak_demo`:

```bash
cd streaming_peak_demo
./run_streaming_e2e.sh
```

Please refer to the README files within each specific example directory for more detailed instructions and configurations.
