# Install ExpertOS in DeepSeek Harness (local development)

The plugin's entrypoint is `plugin/index.mjs`. It registers tools through the
public `@deepseek-ai/dsh-tools` API. Current Harness may change its preview
interfaces; pin a known-working Harness version when doing real testing.

## Step 1 — start the Python bridge

Run the following commands **in the cloned repository root**. The repo needs
Python on `PATH`. Install the core `tiny-expert-system` project separately if
you want optional book retrieval. Training requires PyTorch.

Linux/macOS Bash:

```bash
export PYTHONPATH="$PWD/python${PYTHONPATH:+:$PYTHONPATH}"
export EXPERTOS_BRIDGE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"
python -m expertos_bridge --host 127.0.0.1 --port 8765
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\python;$env:PYTHONPATH"
$env:EXPERTOS_BRIDGE_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(36))"
py -m expertos_bridge --host 127.0.0.1 --port 8765
```

Keep the same randomly generated token in the Harness process environment.
Do not commit the token, put it in a URL, or use a token shorter than 32 chars.

## Step 2 — install local Harness plugin

From a running DeepSeek Harness installation with the Web profile:

```bash
# Replace /absolute/path/... with the path containing this README.
dsh plugin --profile web add link:/absolute/path/to/expertos-harness-plugin/plugin
```

The local package declares Playwright as a dependency. Chromium browser binaries
may need installation separately:

```bash
cd /absolute/path/to/expertos-harness-plugin/plugin
npx playwright install chromium
```

Do not overwrite an existing Harness profile file. Add the `- insert:` row
from `cordis.patch.yml` to the profile's existing `cordis.patch.yml`, or use
`dsh web --patch /absolute/path/to/expertos-harness-plugin/cordis.patch.yml`
when starting from the source checkout. The latter is the documented first-
plugin development approach; loading the local package by name is preferred
for profile installs.

Enable exact host allowlist (example **only**):

```bash
export EXPERTOS_ALLOWED_HOSTS="example.com,www.example.com"
export EXPERTOS_BRIDGE_URL="http://127.0.0.1:8765"
# EXPERTOS_BRIDGE_TOKEN must match the Python process.
dsh web
```

Use the DeepSeek desktop product's own plugin manager / restart facilities if
it is managing the Harness process. The desktop product may have a different
profile and environment setup from the CLI and was **not tested here**.

## Step 3 — smoke test

Ask Harness:

1. `Use expertos_experts to list my specialist capabilities.`
2. `Use expertos_plan to prepare an extract task for https://example.com.`
3. On a non-sensitive test page that is explicitly allowlisted, call
   `expertos_browser_workflow` with `kind: extract`.
4. For form testing, use a dedicated **non-production** form. The tool will
   populate ordinary fields and compare them against their final values, but
   never click a submit button.

The standard DeepSeek loop still requires a compatible model to decide which
plugin tools to call. Replacing its loop with our non-LLM orchestrator is a
**separate development milestone**. The Python bridge and browser executor
can already be called programmatically without a model.

## Troubleshooting

- `EXPERTOS_BRIDGE_TOKEN ... 32+`: token missing in the Harness process.
- `ECONNREFUSED`: Python bridge is not running on the configured port.
- `Blocked hostname`: add the **exact** external HTTPS hostname to
  `EXPERTOS_ALLOWED_HOSTS`. Do not add localhost/private IPs.
- `Cannot find package playwright`: install plugin dependencies in the active
  Harness profile and run `npx playwright install chromium`.
- `Browser failure`: the site may require login, blocked third-party content,
  unsupported shadow DOM, or a workflow beyond this prototype.
- No `expertos_*` tools in Harness: confirm the profile patch was loaded,
  the plugin registered correctly, and the profile was restarted.
