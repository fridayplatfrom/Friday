# DeepSeek Harness Native Integration

> Disabled in the active web profile. `start_harness.cmd` now starts the standard
> browser Harness without copying these integration patches. The adapter and
> patch files below are retained as experimental source, not active setup.
> The historical installation instructions below describe the optional adapter.

This package completely replaces DeepSeek's cloud API with **Tiny Expert OS** running locally on `http://127.0.0.1:8000`.

## Architecture & How It Works

1. **Cordis Service Layer (`index.mjs`)**:
   - Registers as an internal LLM provider `tiny-experts` under `@deepseek-ai/dsh-core`.
   - Overrides model selection to default to `tiny-expert-physics-v1`.
   - Completely disables DeepSeek API-key and account authenticators (`@deepseek-ai/dsh-llm-deepseek-api-key` and `@deepseek-ai/dsh-llm-deepseek-account`).
   - Translates chat prompts from DeepSeek Harness into Tiny Expert OS 2-stage neural routing, symbolic CAS reasoning, and 54-book KnowledgeCore FTS5 cryptographic verification.
   - Streams reasoning traces (thinking tokens) and markdown answers with full mathematical LaTeX notation and SHA-256 textbook citations.

2. **Cordis Configuration (`cordis.patch.yml`)**:
   - Deployed to `%USERPROFILE%\.dsh\profiles\web\cordis.patch.yml`.
   - Sets the default profile to connect to `tiny-experts-native-llm` targeting port 8000.

## Quick Start

### 1. Start Tiny Expert OS Daemon
```powershell
python web_app.py --port 8000
```

### 2. Launch DeepSeek Harness
Run the launcher script:
```cmd
integrations\deepseek_harness_native\start_harness.cmd
```
or run directly:
```powershell
& "$env:LOCALAPPDATA\Programs\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd" --profile web --port 3030 --host 127.0.0.1
```

### 3. Open in Browser
Visit `http://127.0.0.1:3030/` using the token displayed in the console output. Any prompt submitted in the harness will be answered by Tiny Expert OS with complete reasoning trace, symbolic solutions, and 54-book cryptographically verified citations.

## Streaming and physics validation

The native adapter consumes `/api/harness/stream` as incremental SSE, rather
than buffering `/api/harness/chat` and replaying it with artificial delays.
A status event is flushed before local computation begins, followed by the
completed execution report and answer chunks. This is bounded local tool
execution, not token-by-token generative inference. Cancellation disconnects
the transport; it does not interrupt an already-running symbolic calculation.
Transport failures and truncated streams fail explicitly. Prompt bodies are
no longer automatically appended to a hardcoded debug log.

Concept rules are identified separately from neural predictions. Source hashes
check passage integrity, not scientific truth or semantic support. Retrieved
excerpts can still be irrelevant. Experimental reader output is withheld by
default; `TINY_EXPERT_ALLOW_EXPERIMENTAL_READER=1` enables research output with
an explicit unvalidated label. This is not a validated general physics tutor.

Regression checks:

```powershell
python -m pytest -q tests/regression/test_harness_physics_streaming.py tests/regression/test_local_server.py
node --test integrations/deepseek_harness_native/stream.test.mjs
```

Restart both the Python daemon and Harness after changing provider code. Each
browser must open the token-bearing URL printed by Harness once; authenticating
Chrome does not authenticate the in-app browser.
