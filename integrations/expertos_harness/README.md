# ExpertOS ↔ DeepSeek Harness (experimental)

A **real Cordis tool plugin**, loopback Python expert bridge, and conservative
Playwright browser executor for the private `fridayplatfrom/tiny-expert-system`
project. This does **not** replace DeepSeek's default agent loop, and does
**not** imply our existing neural experts can code or browse autonomously.

## What is implemented

- **Harness tool plugin** with 9 typed tools: `expertos_experts`, `expertos_route`,
  `expertos_plan`, `expertos_form_map`, `expertos_form_verify`,
  `expertos_propose_action`, `expertos_recover`, `expertos_read_source`,
  `expertos_browser_workflow`.
- **Python experts**: deterministic task router, bounded planner, accessible-label
  form mapper, post-write verifier, failure recovery. Optional existing book
  source retrieval (no model inferred answers).
- **Optional trainable neural browser policy**: a tiny PyTorch MLP to classify
  `navigate`, `extract`, `fill_form` or `abstain` from text/context. Its bundle
  verifies integrity and remains **experimental/disabled by default**. It
  merely proposes an action; it never executes one.
- **Browser runner**: uses a fresh isolated Playwright Chromium context,
  navigates to an explicitly allowlisted origin, extracts page text, or fills
  and verifies non-sensitive fields. It has **no submit operation**, no
  password/OTP/CAPTCHA handling, no cookie reuse and no arbitrary JavaScript.
- **Local API**: token-authenticated at `127.0.0.1`, bounded JSON requests, no
  CORS, no remote bind; dedicated endpoints for planning, mapping and review.

## Installation and running

See [Windows and Linux setup](docs/SETUP.md). The supported development path
is a local Harness plugin package added to a `cordis.patch.yml` profile.
Do not overwrite existing profile patches.

**Requirements:** Python 3.11+, Node 22+, existing DeepSeek Harness with its
`@deepseek-ai/dsh-tools` service, optional Playwright/Chromium; optional
PyTorch for neural policy training. No model weights ship with this plugin.

## Development tests

```sh
PYTHONPATH=python python -m pytest -q tests/test_bridge.py
node --test tests/tools.test.mjs
```

A local run passed 6 Python tests and 5 Node tests using a mocked Playwright
browser, and a 2-epoch experimental neural-policy train/save/reload test.
This **does not** test the actual DeepSeek Harness installation or Chromium.
Real browser smoke tests require installing Playwright and Chromium.

## Security and limitations

1. Host allowlist defaults to empty. The browser refuses every external site
   until `EXPERTOS_ALLOWED_HOSTS` lists exact hosts. CDN/subdomain requests not
   listed may fail. No arbitrary `http`, `file:`, private IP or localhost access
   in the installed production plugin. Localhost is accepted only by injected
   **tests**, never by `plugin/index.mjs`.
2. The browser uses an independent temporary context, **not** a DeepSeek Harness
   browser provider session. It does not inherit the user's logged-in tabs.
3. The entire page is untrusted data. Prompt injection in websites or documents
   must not alter agent permissions or become tool instructions.
4. Typing into a page can still trigger **auto-save** and onchange side effects.
   Use only controlled test sites before enabling a real domain.
5. Browser DNS resolution is not pinned to verified public IPs; this prototype
   is not a fully hardened SSRF boundary and is **not appropriate for untrusted
   hostile websites** or sensitive credentials. Harden network isolation first.
6. `values_json` and other arguments may be logged in Harness session history.
   **Never use passwords, OTPs, bank details, personal IDs, or sensitive forms**.
7. There is no unrestricted planning, automatic submits, payment, financial
   action, code generation, arbitrary browser clicking or multi-site navigation.
8. Input-field mapping is a **rule-based baseline**, not a learned neural
   model. The optional PyTorch action policy is untrained until explicitly
   trained on independent demonstrations; a demo is not a real benchmark.
9. Existing text/pathology/book experts require the original project's
   installed Python dependencies, data and compatible model bundles. The
   source-reading tool returns retrieved excerpts, not scientific verification.

## Source references

- Official tutorial: https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/index.md
- Official tool plugin reference: https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/tool.md
- Official browser provider docs: https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/browser-use.md

Do not distribute DeepSeek's brand assets or imply endorsement; this is a
third-party integration.

### Chromium smoke-test limitation

When invoked with `EXPERTOS_REAL_BROWSER_TEST=1`, an optional Python
Playwright test loads `examples/safe_form.html` using
`page.set_content`, fills text/email controls and confirms passwords remain
empty. The container blocked even localhost `page.goto` with
`ERR_BLOCKED_BY_ADMINISTRATOR`, so actual browser **navigation** and the Node
plugin's real Playwright integration remain unverified here.
