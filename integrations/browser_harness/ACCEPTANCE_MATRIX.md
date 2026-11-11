# Friday hardening and acceptance matrix

Scope: the existing Harness UI, agent loop and browser MCP plugin. No additional
browser controller, engine or extension was installed. The Chrome Friday
extension remains the model-website transport, separate from task browser tools.

The 2026-11-10 setup had retained a demo-only `--allowed-origins` setting.
`browser-policy.mjs`, `configure_browser.ps1` and `setup.ps1` now use explicit
origins for the local store, demo form, Unsplash images and Google font assets.
Custom origins are preserved. Invalid origins and unexpected profile structures
fail closed. The native CLI validates changes, and backups precede every edit.
The original browser plugin identity, executable and isolated mode are retained.

## Requested improvements

| Area | Implementation | Verification |
| --- | --- | --- |
| Existing browser website access | Corrected explicit origin policy; no unrestricted wildcard | Native CLI parse and plugin-preservation checks; live Harness browser navigation to GOODBOWL succeeds |
| Browser acceptance | Only `mcp__browser__` task tools in the current run | Navigation, search/category, details, cart quantity/reload, validation, demo purchase and responsive screenshots passed; post-0.4.26 native recheck confirmed fonts/no overflow; saved form result says Submission 1 accepted locally; Friday wrote the native-only QA report |
| Image job handoff | Native continuation waits for an accepted studio job; cancellable without replay | Local real-bridge integration tests and live native-browser submission → waiting state → resumed continuation, without busy failure |
| Response completion | Verified turn anchoring; completion evidence; loading-placeholder waiting; short-text buffering | Regression tests and prior live file/tool/image flows |
| Literal tool payloads | Fenced JSON, visible code extraction, outside-prose rejection, validated native blocks | Regression tests and live PowerShell dollar/backslash preservation |
| Duplicate prevention | Stable request/turn IDs, receipts, verified submission; no blind provider retries | Duplicate, lost-worker, stale-event, uncertain-submission tests |
| Restart/reconnect | Durable pairing, native history and checkpoints; offline/reconnect guard; no automatic operation replay | Regression tests and repeated live backend restarts/context restoration |
| Conversation ownership | Session-to-tab binding and exact provider URL checks | Pairing/two-way/session isolation tests and live reused ChatGPT conversation |
| Cancellation | Abort propagation; pending-load cancellation; image-wait cancellation; shutdown guard | Local bridge/browser-content regression tests |
| Native compaction | Preserved native presets with compatible local planning budgets | Live manual Compact, recall and repeated automatic pressure compaction |
| Native session export | Existing Harness Download session log action retained | Live ZIP download completed; 1,344,121 bytes, three archive entries, archive opened successfully |
| Long context | Marked old-result excerpts; bounded acknowledged multipart transfer; checkpoint invalidation | Lossless reconstruction, bad-ACK/cancel/budget tests; full live multipart round trip remains pending |
| Files | Native admitted references; immutable verified streams; size/type/session/digest checks; staged delivery receipts | All declared extensions byte-preserved locally; live TXT/CSV/PNG examples; semantic reading of every format is not established |
| Generated media | Owned image receipts, bytes/previews/downloads; actual status/percentage only | Native browser studio preview loaded at 1122×1402; download event completed with failure null; real image/PNG bytes independently verified in preceding runs |
| Permission ownership | Native Harness execution and approvals retained; owner authentication and Host/Origin fences | Unauthorized request, foreign-origin, unknown-tool and foreign-file tests; no approval bypass added |
| Tool changes/batches | Active/deferred/removed schema filtering; bounded independent batches | Local contract tests; saved audit confirms six completed multi-call replies and corresponding native multi-call assistant messages; removed/deferred changes remain locally tested |
| Diagnostics | Failure component/category/action, including native tool errors; independent backend/extension versions; existing Models diagnostics | Sanitized guidance/metrics tests; live Models shows backend/connector 0.4.26, recent attempts and bounded audit cache |
| Repeatable regression | Node test suite, synthetic fixtures and real bridge tests | 189 local tests passing at hardening checkpoint; current live evidence recorded separately |
| Updates/rollback | Idle-only opt-in extension updater; profile backups and CLI rollback | Updater regressions and observed automatic 0.4.21/0.4.23 activation; no new permissions |
| Reliability/performance | Recent transport attempt counts and observed latency; streamed journal loading; bounded recent payload/receipt memory | Metrics redaction/deduplication, UTF-8/chunk boundary, missing-delimiter, restart sequence and old-history tests |
| Other model websites | Explicit experimental labels; no unsupported modalities or hidden API controls advertised | ChatGPT is the live reference; other providers require separate account/site validation |

The existing Models connection controls now work with the installed Chrome
transport instead of calling managed-browser-only actions. Provider changes are
owner-authenticated, bounded, restricted to supported sites, and refused while a
website request is active. An entirely disabled connector still polls its
authenticated local configuration channel so Models can reenable it. These
changes open no new tabs and install no additional browser controller.
Live activation verified ChatGPT disable and reenable through these native Models
controls. Both backend and extension report 0.4.26. The saved conversation and
paired URL survived restart; recent audit payloads show 2,000 records / 10.2 MiB.
The final form check encountered an absent ChatGPT editor in the long paired
conversation. The request waited without replay, was explicitly cancelled for
backend activation, and was resumed afterwards. The saved prior native result
confirmed the form had already succeeded, so it was not resubmitted. Long-chat
editor availability remains a reliability limitation despite the acceptance pass.

Friday recovered the existing MongoDB-backed store after an initial 10-second
startup timeout, increased its launch timeout to 60 seconds, and reran all 13
store tests successfully. A read-only query confirmed order GB-DD8EBDE122 (499)
survived restart. Store source/database recovery was performed through Harness;
no database/cache files were deleted. The final native report is in
`C:/Users/ankus/Documents/deepseek-harness/default-workspace/goodbowl-store/QA.md`.

## Audit storage and performance

The complete append-only disk audit is retained. Only its recent in-memory
payload window is bounded (2,000 records and a 16 MiB serialized-content target;
a single larger record is retained). JavaScript object overhead is additional,
so this is not an exact process-RAM cap. Historical session audit reads and
interrupted-request inspection stream the full saved file on explicit demand.
Sequence numbers remain monotonic across restarts. A partial final UTF-8 record
is preserved separately before recovery; invalid completed records fail rather
than silently clearing history. No lifetime audit files or user data are deleted.

Transport metrics describe recent attempts, not complete-task success, exact
token latency, usage or cost. They contain no prompts, URLs, file names, secrets
or user identifiers and stay on the local authenticated interface.

## Browser testing constraint

The preceding GOODBOWL task used standalone Chrome/CDP scripts after its native
browser was blocked. Those results remain historical evidence, but do not count
as a pass for this native-only-browser run. The new Friday instruction explicitly
forbids that fallback and the old standalone scripts. Native browser screenshots
and tool outputs must substantiate this run's eventual UI and form results.

## Limits

Finite regression tests cannot establish perfect reliability across arbitrary
websites, accounts, files and uninterrupted long-running tasks. Website DOM,
quota, authentication and verification behavior remain external dependencies.
The long native acceptance session showed roughly 50-second average transport
attempts at one checkpoint and frequent automatic compactions with the full tool
catalog. Those observations establish continuation, not acceptable interactive
latency or perfect long-session performance; further optimization is needed.
No exact model version, token usage, hidden reasoning, temperature setting or
strict generated-token cap is fabricated. Live checks still pending above must
not be described as completed merely because their local protocol tests pass.
