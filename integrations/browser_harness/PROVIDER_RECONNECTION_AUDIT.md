# Friday provider reconnection repair

Date: 2026-11-11 (Asia/Kolkata). Prepared version: **0.9.7**.

Full regression: **333 passed, zero failed** (`provider-reconnection-tests.log`).
This is automated evidence; live provider acceptance is tracked separately.

## Repairs

- Find the exact saved provider URL before consulting its potentially stale tab
  ID. A positive same-URL result can recover the existing tab even when the ID
  API stalls. Queries and fallback reads remain bounded; ambiguous absence never
  authorizes opening a duplicate. Other conversations and ownership stay isolated.
- Health checks use that same read-only discovery instead of directly probing an
  obsolete ID. They do not create or refresh tabs.
- A responding extension listener at the expected document URL is readiness
  evidence without waiting for a separate Chrome metadata operation to finish.
- Start messages acknowledge immediately. Model streaming, errors and completion
  travel through the existing authenticated, job-scoped event transport. The
  background job stays reserved until the backend acknowledges a terminal event
  or cancellation removes its admission. A multi-minute response no longer
  depends on one long-lived Chrome response port.
- An expired verified latest Gemini/Kimi turn releases its own Stop control.
  Later human input is not eligible; incomplete text is never called complete.
  The response-loading placeholder continues to use the existing waiting policy.
- Future development updates also resolve restored tab IDs by exact saved URL
  and bound metadata reads. Drafts, unknown state and active replies still defer
  updates rather than triggering a destructive refresh.

No extension permissions or provider host access were expanded. Native tools,
approvals, attachments, compaction, goals, handoffs, durable execution receipts
and full transcript ownership remain with Harness.

## Live acceptance gate

The installed files contain 0.9.7. The running extension must report 0.9.7 before
any new test is counted against these repairs. Existing 0.9.6 tests and failures
are retained in `PRODUCTION_READINESS.md`; they are not relabelled as 0.9.7 results.

For each DeepSeek, Gemini and Kimi saved native session: confirm runtime and page
readiness, execute a read-only native browser snapshot, return its actual result
to the same provider chat, and receive a complete bounded final report in Friday.
Inspect the native call/result identities and terminal AG-UI event. Stop on
denial, sign-in, quota, uncertain submission or an unconfirmed reply. No form
submission, publishing, shell command or permission change is needed for this gate.
