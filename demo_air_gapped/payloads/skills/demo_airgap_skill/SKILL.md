---
name: demo.airgap.note_analysis
package: mn-demo-airgap-skill
folder: demo_airgap_skill
import: mn_demo_airgap_skill
description: Analyze a local operational note with the model bundled in the same blueprint. Use only for the demo_air_gapped workflow and do not send note content to external services.
---

# Air-Gapped Note Analysis

Use `build_analysis_prompt(payload)` to extract a bounded note from an incoming
workflow payload and construct the model prompt. Use `finalize_report(payload)`
to normalize the analyzer output for the final run artifact.

The skill uses only the Python standard library. It does not access the
network, package indexes, GAR, or files outside the workflow payload.
