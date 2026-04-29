# Infinite Drug Discovery Loop

This blueprint runs an infinite multi-agent loop for AI drug discovery, built on top of [BioTarget](https://github.com/homerquan/BioTarget). It demonstrates how to port complex ML pipelines into long-running, self-sustaining agent workflows using the MirrorNeuron runtime.

## Overview

The blueprint consists of two executor agents that run in a continuous cycle:

1.  **Protein Generator (`protein_generator`)**:
    *   Queries Open Targets Platform for the top protein targets related to a disease (default: Alzheimer's).
    *   Generates a 3D structural conformation of the target using AlphaFold/OpenFold3 representations.
    *   Emits the generated protein structure to the drug docker.

2.  **Drug Docker (`drug_docker`)**:
    *   Receives the 3D protein structure.
    *   Selects a candidate molecule (SMILES) from a pool of seeds.
    *   Uses **GNINA** (a deep learning framework for molecular docking) to evaluate binding affinity.
    *   Saves promising candidates (score < -5.0) to a job-specific tracking file.
    *   Emits a message back to the `protein_generator` to trigger the next round, continuing the loop indefinitely.

## Requirements

*   **MirrorNeuron**: The runtime environment.
*   **BioTarget**: The core pipeline logic must be accessible.
*   **GNINA**: You **must** have [GNINA](https://github.com/gnina/gnina) and Docker installed for the docking stage to work. The `drug_docker` agent runs GNINA inside a temporary Docker container to evaluate the binding affinity.

## Running

We have provided a convenient launch script that starts the loop and prints the exact locations of the unique output files based on the generated Job ID.

```bash
./launch.sh
```

If you prefer to run it manually using the CLI:

```bash
# Validate
mn validate science_drug_discovery_daemon

# Run in background
mn run science_drug_discovery_daemon --no-await
```

## Outputs

All outputs are saved to shared files unique to each job run to keep a continuous record across the infinite loop:
*   **Best Drugs:** `/tmp/mirror_neuron_<job_id>/best_drugs.txt` (Appends every SMILES that scores well).
*   **All Attempts Log:** `/tmp/mirror_neuron_<job_id>/docking.log` (Appends every docking score calculation).

The launch script will automatically output the correct `tail -f` command for you to run to watch these files in real-time.

## Operations

### Status logging

Blueprint helper scripts and payloads report important running status as JSON lines on stderr. Each line includes `ts`, `level`, `blueprint`, `phase`, and `message`, with optional `details`. This keeps stdout reserved for bundle paths or machine-readable result JSON.

### Quick test mode

Use quick test mode for cheap logic validation before calling paid or slow external systems:

```bash
MN_BLUEPRINT_QUICK_TEST=1 python3 generate_bundle.py --quick-test
```

Generated blueprints shrink worker counts, durations, retries, and delays. LLM/email/API-facing paths use mock or dry-run providers where supported.

### Output contract

CLI output is intentionally uniform:

- stderr: JSON status lines and ASCII progress bars such as `[########--------] 50% phase`.
- stdout: one bundle path, one JSON object, or MirrorNeuron event envelopes.
- events: typed objects with a `type` and `payload` field.

### Shared skills

Reusable helpers live in `mn-skills` instead of being reimplemented inside blueprints:

- `blueprint_support_skill`: logging, progress, quick-test, and manifest helpers.
- `marketing_email_skill`: deterministic customer segmentation, offer selection, and email rendering helpers.
- `email_delivery_skill`: dry-run/live email and Slack delivery wrappers.

