# Friday parallel-request acceptance

Date: 2026-11-11 (Asia/Kolkata). Candidate: **0.10.2**.

## Implemented behavior

- Two active website model requests in Chrome extension mode. Additional
  requests wait with a visible queue position. A single Friday conversation
  remains ordered even when switching providers. Eligible waiting conversations
  are admitted in arrival order without blocking behind an already-active chat.
- One tab owner per request; streaming events, terminal acknowledgments, files,
  cancellation and native AG-UI transcripts retain their existing identities.
- Queued cancellation sends no website prompt. Cancelling/failing one active
  request frees its slot without cancelling another chat or replaying actions.
- Lost or rejected Chrome start ports cannot hold the worker after an owned
  terminal event. Ambiguous start delivery never causes a resend. A durable
  setup failure cannot leave a dispatchable orphan job; native consumers must
  still own every visible request.
- Background heartbeats wake elapsed editor/stream waits when page timers stall.
  Heartbeats cannot submit, reload, approve, retry or change a provider account.
- Same-origin Chrome download collection is serialized before the Download click
  because download events do not reliably identify the source tab. Independent
  origins can transfer separately.
- Restart marks interrupted work for review; the in-memory queue is never replayed.
  Old Chrome workers and built-in/shared-browser transports retain one slot.
- Native Harness tools, approval policy, goals, compaction, attachments, browser
  execution leases and model handoffs remain in place. Model concurrency does not
  provide logical conflict resolution for two agents editing the same files.

## Automated verification

Latest full suite: **348 passed, zero failed** (`production-hardening-final.log`).
Fault-injection checks also cover unresolved/rejected Chrome start ports and
state-persistence failure during admission (`production-fault-tests.log` and
`production-ack-tests.log`).

Coverage includes mixed providers, two ChatGPT conversations, eligible queue
ordering, one active request per conversation, cancellation before dispatch and
at slot admission, isolated failures, old-worker compatibility, cross-tab event
rejection, out-of-order reply routing, same-origin download isolation, and all
four providers completing with frozen page timers through owned heartbeats.

## Live evidence and unresolved gate

The v0.10.0 mixed-provider test completed real native `pwsh` calls and full
report return in the correct native conversations:

| Provider | Native AG-UI run | Tool calls/results |
|---|---|---|
| ChatGPT | `16f53eb2-26c9-47c8-9211-0b34e9e7c352` | 1 / 1 |
| Gemini | `2ff8ddc5-05aa-4f2b-ac88-6ddc09696d26` | 1 / 1 |

An older ChatGPT tab failed readiness before any prompt was submitted. The first
two-ChatGPT attempt then stalled before any native tool calls; both failure
records are retained (`fded6451-c16b-420b-8453-0aaeb2c8fe62` and
`579bf311-f8ec-44a4-8e02-c7a03ff30cf8`). A queued Gemini attempt also timed out
without a native call (`73b70924-d83f-4e06-ac36-82bafc224ecf`). These are failures,
not passed acceptances. The background-wait fix in v0.10.1 addresses the timing
path reproduced in frozen-timer tests.

An owner-authenticated read-only audit after restart revalidated both native
tool arguments, actual outputs, call/result identities, and complete committed
reports. Their browser requests overlapped for **16,801 milliseconds**. Saved
evidence: `../../output/friday-parallel-partial-report.json`. Its status is
explicitly `partial`; these v0.10.0 runs are not relabelled as v0.10.2 tests.

The initial live status recording contains 348 samples and observed a peak of
two active requests plus one queued request, never exceeding two active slots:
`../../output/friday-parallel-status-v010-initial-failed.json`.

## Final v0.10.2 native acceptance: passed

After activating the extension and refreshing its idle page listeners, five new
native tool round trips passed. The audit independently reconstructed exact pwsh
arguments and results, matched tool-call IDs, checked the committed native final
reports, rejected other chats' markers and verified distinct saved ChatGPT tabs
and URLs. Every run executed only its requested Write-Output command once.

| Cohort | Runs | Real browser-request overlap |
|---|---|---|
| Two ChatGPT chats | b2179fdc… / c9d50939… | 6,192 ms |
| ChatGPT + Gemini | 1cde5f12… / 111e0b6b… | 10,628 ms |
| Queued Gemini in the three-request cohort | 4a9310bf… | Completed after admission |

The three-request trace recorded 169 samples: peak two active and one queued,
never more than two active. All five tasks finished; final pending count was zero.
Full IDs, native transcripts, pair ownership and request intervals are recorded
in ../../output/friday-parallel-live-report.json. Reproduce its read-only audit:

    node tasks/verify-parallel-live.mjs tasks/parallel-final-spec.json

An earlier Gemini probe (35ebe3fa…) executed both an older test marker and the new
one. It was rejected as a failed acceptance despite its success report. Common
snapshot, incremental and multipart instructions now scope work to the latest
human task, preserve applicable earlier constraints and explicitly continued goals,
and prevent unrelated historical requests from becoming a backlog. Both later
Gemini probes executed only the newly requested marker. This is model guidance,
not a general exactly-once guarantee for arbitrary tools.

Three post-reload probes failed readiness before submission because their page
listeners were stale. Those failures remain saved (df7df73f…, d2203795…,
5f6b1258…). Refreshing the confirmed idle paired pages restored their listeners;
no uncertain prompt was resubmitted. Automatic recovery of every invalidated page
listener remains a limitation; unknown drafts and generation are preserved.

The backend-only task-scope change passed all 348 automated tests. No extension
permission defaults, native approval controls, account login or upstream Harness
features were changed. This gate covers print-only native concurrency, not all
possible websites, file-edit conflicts, long tasks or production distribution.
