---
name: mirrorneuron.opencode
metadata: {internal: true}
package: mirrorneuron-opencode-skill
folder: opencode_skill
import: mn_opencode_skill
description: Launch OpenCode inside an OpenShell worker to generate, edit, or review code in a specified sandbox folder with a selectable provider/model. Use when the user requests OpenCode as the coding tool; the default is Muse Spark 1.3 Free on OpenCode Zen.
---

# OpenCode Skill

Use `mn_opencode_skill` in an OpenShell worker. The caller owns sandbox creation,
upload/download, network policy, credentials, workflow routing, and artifact
publication. This adapter launches the installed OpenCode CLI; it does not create
a sandbox or substitute another coding agent.

## Run

- Stage the selected source folder inside the sandbox and pass its sandbox path
  as `folder`. A native host path is not visible in OpenShell without staging.
- Use `OpenCodeRequest(folder=..., prompt=..., mode="generate" | "edit" | "review")`
  and `run_opencode(request)`, or the `mn-opencode` CLI described in `README.md`.
- Default model: `opencode/muse-spark-1.3-contributor-free` (Muse Spark 1.3 Free,
  OpenCode Zen). Pass `model="provider/model"` to select another model. Do not
  silently replace the default with its paid counterpart if it is unavailable.
- The folder must already exist within `sandbox_root` (default `/sandbox/job`).
  Configure another sandbox root explicitly when the worker uses `/workspace`.
- Generation and editing use OpenCode's `build` agent. Review uses `plan` with
  edits, shell commands, and delegation denied; it returns findings as text.
  Applying review fixes requires a separate edit request.
- OpenCode runs with JSON events and external plugins disabled. The adapter
  bounds runtime and captured output, terminates the process group on failure,
  and treats JSON error events as failures even when OpenCode exits zero.

## Runtime requirements

Provide Python 3.11+ and OpenCode 1.18.33+ inside the sandbox image. If required by
the chosen provider, supply credentials through OpenShell providers or narrowly
scoped environment injection. Never copy host authentication directories into
payloads. The default provider uses `opencode.ai:443`; the blueprint must allow
the model API and any separately needed discovery endpoints. Review the actual
image and network policy when changing providers.

Code generation and editing can modify files and execute commands within the
sandbox's permissions. OpenCode permissions complement OpenShell isolation;
they do not enforce a filesystem or network boundary on their own. Inspect the
resulting files and run task-appropriate checks before publishing them. Keep
domain prompts and workflow policies in the caller.
