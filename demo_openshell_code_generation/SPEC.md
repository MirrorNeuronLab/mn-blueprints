# Demo contract

- ID: `demo_openshell_code_generation`.
- Reusable capability: `mirrorneuron-opencode-skill`, bundled as source at
  `payloads/skills/opencode_skill` with snapshot version `0.0.0`.
- Both runners upload the worker and skill trees as sibling directories.
- Runtime: `MirrorNeuron.Runner.OpenShell`; no native coding fallback.
- Default model: `opencode/muse-spark-1.3-contributor-free`.
- Input: bundled pizza prompt and configurable sandbox project folder.
- Output: self-contained `index.html`, generation identity, verification,
  and SHA-256. Both launch paths export to `~/Download/demo_openshell_code_generation`.
- Generation publishes HTML and generation metadata through `mn.artifact_handoff/v1`.
  Verification resolves those committed references in its own workspace and
  publishes verification metadata. Core exports only after successful commit.
- Shared sandboxes provide disposable verified input caches; replacing a sandbox
  between steps does not invalidate the durable owner artifacts.
- The CLI runtime requires compatible Core/SDK handoff support and rejects legacy
  whole-tree synchronization. The standalone script explicitly selects its
  single-workspace mode with `MN_DEMO_STANDALONE=1`.
- An uncertain worker execution blocks automatic replay; transfer retries never
  invoke OpenCode again. Owner-storage loss is outside the durability guarantee.
- Failure: model/tool errors, failed process, missing HTML, or invalid structure
  stop the run. No automatic retries or paid-model fallback.
- Live requirements: Docker, OpenShell gateway, downloadable image assets,
  and permitted OpenCode Zen API. Python tests require none of these.
