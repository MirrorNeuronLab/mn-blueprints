# OpenShell Code Generation

This demo runs the **OpenCode Skill** inside OpenShell to generate a standalone
pizza ordering page. It uses **Muse Spark 1.3 Free — OpenCode Zen** by default:
`opencode/muse-spark-1.3-contributor-free`.

The OpenShell worker stages a project folder, launches OpenCode, checks the
generated HTML, and returns its content and hash. The standalone runner exports
the verified result to `~/Download/demo_openshell_code_generation/index.html`.

## Run the demo

Prerequisites: Python 3.11+, Docker, and an existing OpenShell gateway. OpenCode
1.18.33 is downloaded into the sandbox image during its first Docker build.
The image also caches the model catalog; runtime egress permits only the Zen
model endpoint and its model listing for the OpenCode binary. The default free
model is attempted without credentials; attach an existing Zen provider if your
account or model requires authentication. Never put credentials in this folder.

From this blueprint folder, when OpenShell is installed on the native host:

```bash
python3 scripts/run_demo.py
```

In the local MirrorNeuron Docker runtime, OpenShell is already installed inside
the core container. Reuse its configured gateway:

```bash
python3 scripts/run_demo.py --runtime-container mirror-neuron-core
```

This creates a new, uniquely named sandbox, uploads the worker and declared skill payloads,
runs the coding task, writes `~/Download/demo_openshell_code_generation/index.html` and `run.json`, and
deletes its sandbox after export. The Docker image remains available for reruns.
Use `--skip-build` after the initial build, or `--keep-sandbox` for inspection.

Select another model explicitly:

```bash
python3 scripts/run_demo.py --runtime-container mirror-neuron-core \
  --model opencode/muse-spark-1.3-contributor-free
```

For authenticated models, pass `--provider <existing-provider-name>` and update
the policy for that provider's exact endpoint before launching. A failed default
model never silently switches to a paid model.

## MirrorNeuron workflow

```bash
mn blueprint validate .
mn blueprint run --folder .
```

`execution.json` declares OpenShell generation and verification executors that
share a sandbox, followed by a terminal result sink. The
worker emits `opencode_completed` and `html_verified`, followed by a completion
payload containing immutable artifact references and hashes. The runtime copies verified files from shared output storage to the configured
host folder after completion. `scripts/run_demo.py` exports the same files for
standalone runs. This is a live integration; fake-LLM/offline flags do not
replace the separate OpenCode model call.

Configuration lives in `config/default.json`: `opencode.model`, `folder`,
`prompt_file`, `mode`, and `timeout_seconds`. Folder and prompt paths are
relative to the uploaded worker. The pizza prompt belongs to this blueprint;
the bundled reusable skill remains domain neutral. The skill lives under
`payloads/skills/opencode_skill`, declared as `skills/opencode_skill` relative
to `payloads/`. Both execution paths upload `worker/` and `skills/` as siblings.
The bundled snapshot has explicit version `0.0.0`; it does not depend on Git
metadata or an adjacent `mn-skills` checkout.

`mn blueprint run` also requires the OpenShell CLI on the submitting host,
matching the gateway version, in `~/.local/bin` or `PATH`. The standalone
runner can instead use the CLI in the Core container as shown above.

## Verify

Open `~/Download/demo_openshell_code_generation/index.html` directly, or serve the output directory locally:

```bash
python3 -m http.server 8080 --bind 127.0.0.1 --directory ~/Download/demo_openshell_code_generation
```

The worker's automated check verifies HTML structure, bounds, language, inline
assets, and a content hash. Browser verification should cover customization,
cart quantities/removal, totals, delivery/pickup, invalid checkout, confirmation,
and a narrow viewport. The page demonstrates ordering; it takes no payment and
submits no real restaurant order.

Tests run without a gateway or model:

```bash
python3 -m unittest discover -s tests -v
```

After a retained run, delete only the sandbox name printed by that run with
`openshell sandbox delete <sandbox-name>`. Stop the local HTTP server with
Ctrl-C. Remove the named demo image with
`docker image rm mirror-neuron/demo-openshell-code-generation:local` when it is
no longer needed.

OpenShell steps have separate invocation workspaces. Generated HTML and metadata
are handed off through Core-committed artifact references using `mn.artifact_handoff/v1`.
The shared sandbox is a disposable cache; each step uses its own workspace.
Core publishes verified bytes and a durable receipt before releasing the next step.
Successful workflow runs export those files to `outputs.folder_path`, defaulting
to `~/Download/demo_openshell_code_generation`. The standalone runner uses the
same default; `--output` overrides it.
