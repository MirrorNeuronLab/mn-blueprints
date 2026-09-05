# Demo Contract

`demo_air_gapped` demonstrates the `mn.payloads.v1` contract and
`mn.backup.v2` air-gap capsule.

The manifest pins every Python package by distribution name and version. A
package with `source: payload` resolves only from its declared path below
`payloads/skills` or `payloads/agents`. Payload packages take precedence over a
GAR package with the same normalized name and version.

The `runtime.models.primary.source` object declares a GGUF model below
`payloads/models`, plus the projector and license. MirrorNeuron hashes these
files, stages large files in its content-addressed blob store, and packages the
model into Docker Model Runner before model validation or workflow execution.

An air-gapped backup contains the runtime snapshot, blueprint bundle, payload
blobs, locally built wheels, required Docker images, compatibility metadata,
and checksums. Restoring or running the extracted `bundle` rejects incompatible
platforms and forbids package-index access.

## Blueprint package format

This blueprint uses the canonical blueprint/v1 format in both folders and ZIPs.
`manifest.json` contains identity, semantic release version, and document references.
`workflow.json` owns logical topology and policies; `execution.json` owns workers,
resources, and services; `contracts.json` owns input/output and artifact contracts.
Platform descriptors live in `extensions/`, package requirements in
`dependencies.json` when present, and operator defaults in `config/default.json`.
The SDK reads these documents together and compiles the Core execution artifact.
A ZIP contains the same files as the folder. Local overrides and invocation
configuration are resolved by the SDK before launch.
