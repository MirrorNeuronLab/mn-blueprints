# OpenCode Skill

`mirrorneuron-opencode-skill` provides a reusable Python and command-line adapter
for OpenCode inside an OpenShell worker. It supports generation, editing, and
read-only review in a caller-selected sandbox folder. It has no Python runtime
dependencies; OpenCode and OpenShell are optional live dependencies.

Install the package in the worker image:

```bash
python3 -m pip install /path/to/opencode_skill
```

The default model is **Muse Spark 1.3 Free — OpenCode Zen**, whose CLI identifier
is `opencode/muse-spark-1.3-contributor-free`. The concatenated display label
`Muse Spark 1.3 FreeOpenCode Zen` is also accepted. Model availability is checked
by OpenCode at execution; there is no fallback to a paid model.

## Python

Run this code inside the sandbox after the caller has staged the source folder:

```python
from mn_opencode_skill import OpenCodeRequest, run_opencode

result = run_opencode(OpenCodeRequest(
    folder="/sandbox/job/project",
    prompt="Implement the requested feature and run its relevant checks.",
    mode="generate",
    # model="provider/model",  # optional override
    timeout_seconds=600,
))
print(result.text)
```

`mode="edit"` changes existing code. `mode="review"` returns findings without
allowing file edits, shell commands, web access, or subagent delegation. The
reviewer can read and search files; supply a diff in the prompt when needed.

## CLI

From an OpenShell worker, with an existing folder and a UTF-8 prompt file:

```bash
mn-opencode --folder /sandbox/job/project \
  --prompt-file /sandbox/job/prompt.md --mode generate \
  --result-file /sandbox/job/result.json

mn-opencode --folder /sandbox/job/project \
  --prompt "Review this code for bugs; include file locations and severity." \
  --mode review --model opencode/muse-spark-1.3-contributor-free
```

`python3 -m mn_opencode_skill` exposes the same CLI. The caller creates the
result-file parent directory. The result includes model, mode, folder, session
ID, text, JSON events, stderr, exit code, and elapsed time. Tool events may
contain source code; store results according to the caller's data policy.

## Limits and errors

`sandbox_root` defaults to `/sandbox/job`; the existing folder's resolved path
must be inside that root. Default runtime is 600 seconds (maximum 3,600).
Captured stdout and stderr are limited to 8 MiB combined (maximum 64 MiB).
Prompts are limited to 128 KiB. OpenCode is launched directly with an argument
list, with no shell interpolation or automatic retry. A missing binary, invalid
input, timeout, excess output, failed exit, malformed event stream, or model/tool
error raises `OpenCodeError` (invalid inputs raise `ValueError`). The CLI exits
nonzero and prints a concise error on stderr. Failed results are not success
artifacts.

OpenCode 1.18.33+ is required for `--pure`, `--dir`, and JSON output. The adapter
injects run-local OpenCode permissions and disables sharing and auto-updates;
it does not modify the project's OpenCode configuration files. The sandbox owns
the effective filesystem and network boundary. The default provider uses
`https://opencode.ai/zen/v1/responses`; model discovery may also use
`models.dev` unless the image includes a current model cache. Credentials, if
needed, remain caller supplied as `OPENCODE_API_KEY` or an OpenShell provider.

See [OpenCode Zen](https://opencode.ai/docs/zen/),
[CLI](https://opencode.ai/docs/cli/), and
[permissions](https://opencode.ai/docs/permissions/) for provider and tool setup.

## Validation

From the skill repository root:

```bash
python -m pytest opencode_skill/tests -q
python3 scripts/sync_agent_skills.py --check
```

Tests use a local fake executable and make no model or network calls. A live
run needs an OpenShell gateway, a compatible worker image, an allowed provider
endpoint, and credentials if the provider requires them. The workflow owns
exporting generated files to the native host.
