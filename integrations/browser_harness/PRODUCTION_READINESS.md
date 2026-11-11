# Friday production-readiness audit

Audit date: 2026-11-11 (Asia/Kolkata). Current candidate: **0.10.3**.
Upstream Harness remains **0.2.1-rc.5**; it was not upgraded in this audit.

**Status: automated hardening passed; production acceptance is incomplete.**
Passing tests and an online extension do not establish that all provider websites,
accounts, native UI controls or unattended tasks work. The live checks below are
separate release gates.

## Latest concurrency acceptance (0.10.2)

Full current regression: **348 passed, zero failed** (production-hardening-final.log).
Five fresh native print-only tool round trips passed independent AG-UI verification:
two ChatGPT chats concurrently, ChatGPT plus Gemini concurrently, and a third
request queued behind the two active slots. Exact arguments, actual results,
complete committed reports and distinct saved chat ownership were checked.
Final pending count: zero. Evidence: ../../output/friday-parallel-live-report.json
and PARALLEL_REQUESTS_AUDIT.md. Earlier failed attempts remain recorded.

Common provider instructions now distinguish the active human task from unrelated
historical failed requests, while preserving earlier constraints, explicitly
continued goals and dependent tool steps. A reproduced Gemini scope failure was
rejected; both subsequent Gemini probes passed exact-command checks.

This concurrency gate is passed. Broader production acceptance remains incomplete:
long-running file tasks, invalidated page listeners after manual extension reload,
account quotas, packaged updates and conflicting edits need their own acceptance.
The historical audit below retains its original version-specific results.

## Results and fixes

- Full regression: **326 passed, 0 failed**. Output: `production-audit-tests.log`.
- Added a deterministic variation matrix: 2,112 tool-reply splits, 267 UTF-8 SSE
  byte boundaries, 133 file chunk boundaries, 16 provider/tab restoration cases,
  6 successful context-budget round trips, and all 12 directed provider switches
  with returns. These are variations inside the test suite, not thousands of
  real website tasks. Evidence: `tests/variation-matrix.test.mjs` and
  `variation-matrix-tests.log`.
- The matrix reproduced and fixed a CRLF-split tool discriminator leaking into
  chat text, a terminal SSE event waiting indefinitely for socket closure, and
  observer cancellation waiting for the next server byte.
- File metadata now rejects malformed durable indexes without replacing them;
  failed saves roll back begin/chunk/finish/status changes. Cross-session status
  batches cannot partially mutate valid attachments, and the decoded chunk limit
  is enforced exactly. All twelve existing saved file records validated before
  activation; the later native screenshot transfer also completed successfully.
- A missing saved Chrome tab ID is labelled `needs-reconnect`, not proof that the
  saved chat URL is closed. Actual tasks retain the existing exact-URL recovery;
  health checks do not silently open, refresh or rebind tabs.
- Production dependencies: `npm audit --omit=dev --json` reported **0 known
  vulnerabilities**. This is an advisory scan, not a complete security review.
- Backend and extension both report **0.9.6** at runtime. All eleven installed
  extension assets match their source hashes. The final backend recovery changes
  were activated by a successful guarded restart; no permission change was needed.
- Encoded logout, OAuth callback and logout-file routes cannot enter automatic
  workspace-tab restoration. Malformed receipt records and duplicate IDs fail
  closed without overwriting the saved file.
- The private workspace-control HTTP server now checks the exact loopback Host,
  authentication, Origin, method, content type, route and a 16 KiB byte limit.
  Its header/request lifetimes are bounded. Tests cover chunked oversized input,
  forbidden origins/hosts, bad JSON and lifecycle operations during execution.
- A failed or timed-out Chrome tab lookup no longer means “tab closed.” It
  preserves the pairing and does not create a duplicate tab. Confirmed missing
  tabs still recover through their saved URL.
- Health diagnostics bound Chrome metadata lookups and report timeout explicitly
  instead of remaining unchecked or falsely reporting a closed tab.
- Native session diagnostics expose the currently loaded model to the owner.
  The operator runner refuses to send a test through a different selected model,
  a running native task. Existing cold conversations now restore automatically
  through Harness's native Session controller before admission.
- Fresh native restoration passed for all four saved provider conversations:
  each changed from unloaded to idle with the correct model, unchanged provider
  URLs and unchanged AG-UI run history. No task was created by restoration.
  Evidence: `../../output/friday-native-session-recovery-audit.json`.
  Recovery is also wired into the current task dock and enabled paired ChatGPT
  inbound admission. It neither approves tools nor repeats previous messages.
  Unit tests cover concurrent restoration, native failures, other-provider and
  child-session rejection, and exactly one inbound admission after recovery.
- A website message-channel closure is now classified as a connection/listener
  failure. If the website already accepted the request, diagnostics retain that
  fact and explicitly prohibit an automatic resend.
- `open_friday.cmd` reopens the current native owner sign-in link in Chrome.
  The helper checks the local host process and never prints the token. It does
  not bypass native authentication or change browser profiles. PowerShell syntax
  was checked without running the browser-launch action.

## Coverage matrix

| Area | Automated coverage | Fresh live acceptance in this audit |
| --- | --- | --- |
| ChatGPT/Gemini/DeepSeek/Kimi selectors and protocol | Response parsing, schemas, literal tool JSON, completion, busy/capacity states | Pending; probes do not establish tool success |
| Streaming and AG-UI | Deltas, final rewrite, run/message/tool events, bounded output, replay cursors; terminal and cancellation stalls | ChatGPT: two runs finished, seven native calls/results, both complete final reports returned. Gemini acceptance still incomplete |
| Native files and images | Verified chunks, filename changes, rejected uploads, immutable bytes, safe previews, failed saves | Native screenshot uploaded to ChatGPT and delivered with the exact original SHA-256 and 20,748 bytes; standalone document picker still pending |
| Generated images/downloads | Progress, unreadable media, active-task ownership, download correlation and retained final text | Pending real generation/download |
| Two-way chat | Trusted input, own-message suppression, interactive buttons, history virtualization, reconnect | Pending both directions |
| Saved chats/model handoff | Per-provider URLs, Kimi provisional routes, ChatGPT draft routes, return handoff | Pending all four providers |
| Workspace profiles/restart | Separate paths, tab sanitation, close/reopen, read-only recovery, crash receipts, owner review | ChatGPT form filled, snapshotted, cleared and independently verified empty. Receipts acknowledged, zero pending actions, zero form submissions. One earlier checkpoint timed out; subsequent guarded restarts succeeded |
| Duplicate-action prevention | Duplicate IDs, crash after commit, unacknowledged completion, disk-write failure | Prior restart retained three receipts and added exactly one read-only call |
| Permissions/questions | Native carrier and decision identity, denial/cancellation, answers and timeout configuration | Pending current allow/deny and question UI checks |
| Native Goal/Plan/Compact | Schema/role preservation, native context-pressure handling and acknowledged transport | Pending current native UI checks |
| Cancellation | Abort propagation, no late submission, transfer cancellation and queue release | Pending current live cancellation |
| Authentication | Owner/guest admission, CSRF headers, loopback Host/Origin and private control channel | Current owner-link recovery opened in Codex; Chrome confirmation pending |
| Native export, scheduling, subagents | Compatibility inventory and native ownership retained | Full live coverage not established |

Existing evidence is retained, not relabelled as this candidate's new tests:

- [v0.9.5 ChatGPT tool round trip](../../output/friday-chatgpt-round-trip-report.json)
- [Friday restart/same-chat continuation](../../output/friday-restart-reconnect-report.json)
- [Current provider readiness probes](../../output/friday-provider-health-audit.json)
- [Current native-session restoration](../../output/friday-native-session-recovery-audit.json)
- [Current Gemini attempt, incomplete](../../output/friday-orbit-gemini-web-a2ffa473-2551-448a-8bcb-5f97e8076a4f.json)
- [Current DeepSeek attempt, no tools executed](../../output/friday-orbit-deepseek-web-30a3f56d-343e-4a98-b00f-fbd1aa1ff78e.json)
- [Current Kimi attempt, accepted then disconnected](../../output/friday-orbit-kimi-web-dc8627d5-980d-4e13-9609-29484e5907bb.json)
- [Current ChatGPT form and screenshot verification](../../output/friday-form-variation-live-report.json)
- [Current ChatGPT reversible form run](../../output/friday-orbit-chatgpt-web-3f1974fb-200c-4ae0-b50c-070ba42cc5b3.json)
- [Current ChatGPT restored-value/screenshot run](../../output/friday-orbit-chatgpt-web-f30dc076-20cd-4d74-b9c2-8acdbc2c43d1.json)

Initial scoped probes: ChatGPT's saved tab had no responding listener; DeepSeek
and Kimi saved tab IDs are reported missing; Gemini's listener responds but the
website still reports generation active. DeepSeek's attempted read-only task
failed on a Chrome tab-lookup timeout without creating a replacement tab or
executing a tool. Gemini completed one navigation, then its next website reply
timed out without executing the proposed snapshot. The form was not filled or
submitted. These are not passing end-to-end results.
Kimi subsequently reopened its saved chat and accepted the read-only brief, but
its asynchronous page-message channel closed before an answer returned. It ran
no tool. The accepted request was not retried.

Subsequent variation-audit follow-up: the ChatGPT listener displayed an obsolete
page-context notice. Its empty, idle paired tab was refreshed, preserving the
same chat URL and login. Two real native runs then passed: five reversible form
operations followed by two read-only verification/screenshot operations. Both
complete reports returned. The screenshot was saved in Friday and uploaded to
ChatGPT with the exact original bytes and SHA-256. The local form server recorded
zero submissions and the receipt store had no pending actions. DeepSeek's fresh
post-restart read-only attempt again failed its Chrome metadata lookup before
any prompt/tool dispatch:
`../../output/friday-orbit-deepseek-web-ba810bfc-e0ac-426e-9623-e4a803c6f41c.json`.
Kimi's fresh follow-up restored its native conversation and attempted its saved
website tab, but the page listener did not become ready. No prompt or tool was
submitted. Evidence:
`../../output/friday-orbit-kimi-web-7d0c8eed-72fb-4697-9efb-0b5000206502.json`.
These provider failures remain open release gates. Repeating the same submission
while the website state is uncertain is not a valid way to obtain a passing test.
Final scoped probes after this pass: ChatGPT listener ready; DeepSeek and Gemini
saved IDs need reconnection; Kimi's current saved tab has no responding listener.
Backend and extension remain connected on v0.9.6. The current machine's browser
inspection was intermittent, including detached browser targets and an unusable
native-window geometry result, so cross-provider UI repair was not verified.

## Remaining release gates

1. Runtime/source version and installed-extension parity: passed for v0.9.6.
2. Complete a real native tool round trip for every advertised provider and
   switch back to a saved chat without copying an unexecuted claim into a result.
3. Complete a reversible browser write, native result acknowledgement, restart,
   and review/duplicate-rejection check without publishing or submitting a form.
4. Verify native TXT/image upload, generated image/download return, two-way chat,
   cancel, owner approval/rejection, questions, Compact, Goal and native export.
5. Run clean-install/upgrade/rollback and multi-workspace tests on another
   machine, including low disk, browser crash, unavailable provider and expired
   login. Check state-file backup/recovery before distributing a release.
6. Define supported browser/native Harness versions, packaged extension updates,
   storage retention and support/diagnostic procedures. Unpacked development
   auto-update is not a production distribution mechanism.

Browser automation initially timed out in this Codex runtime; it later recovered
enough to inspect the live Gemini reply, while attempts to bind the Friday Chrome
tabs still timed out. This limits fresh UI verification; it is not evidence that
Friday's provider tests passed. No personal Chrome extensions, unrelated
applications, real accounts or real social-media posts were modified by the audit.

Website sessions can expire and website interfaces/quotas can change. The durable
receipt fence prevents automatic replay of uncertain native browser actions; it
does not provide exactly-once publishing across arbitrary websites or shell tools.

## Repeatable commands

From `integrations/browser_harness`:

```text
npm test
npm run test:matrix
npm audit --omit=dev --json
node tasks/provider-health-audit.mjs
```

Live operator tasks require an existing saved native conversation whose model
selection matches the requested provider; cold sessions restore automatically. Native
permissions remain authoritative; a test must stop on denial or an uncertain
outcome rather than rerunning an action to obtain a passing report.

## Saved-chat file task and restart acceptance (0.10.2)

A fresh ChatGPT task completed two dependent native pwsh operations inside its
existing permitted workspace: create an isolated nonce-bearing JSON file, then
read and hash it. The audit checked exact tool commands, call/result IDs,
execution order, real file contents, hash and the full committed report.
Creation run: b12afa0e-405d-4e30-ba02-3163e0861966.

Friday was restarted only after the task completed. An explicit read-only
continuation used the same saved ChatGPT URL and tab without another login,
recalled the prior nonce, and confirmed identical file bytes and creationCount=1.
Continuation run: 9f19d830-eba3-44df-bc57-8ab10585b16c. It made exactly one read
call; neither creation nor the earlier verification was replayed. The complete
pre-restart AG-UI transcript retained the same digest. Cursor-based reconnects
returned exactly the saved event suffix without executing a new action.

Evidence: ../../output/friday-file-recovery-audit.json. Read-only recheck:

    node tasks/file-recovery-audit.mjs final

Two earlier attempts were blocked by the native Workspace Write restriction
before file creation. The initial requested path was outside the native workspace;
a test-brief path replacement mistake left the second attempt outside as well.
These are retained failures, not passing attempts (0b5b1d8f-d8b7-4d2d-a1fa-2b260b0058a0
and 22d850b2-3ab8-4f83-8154-89d81c84db1f). Both stopped without escalating
permissions or issuing the dependent read. The corrected brief passed a command-path
preflight and used the workspace returned by a separate read-only native probe.

No production code or extension permissions changed during this acceptance.
The existing 348-test production regression result remains current. This gate
covers local file tools and a completed-task server restart; it does not cover
mid-write crashes, generated website downloads, browser restarts, or general
exactly-once execution across arbitrary tools. Final pending requests: zero.

## Native TXT upload, generated download and refresh acceptance (0.10.2)

Passed via Friday's existing native Add files menu and composer, with ChatGPT in
its paired Chrome tab. The synthetic TXT contained a random nonce absent from
the task prompt. ChatGPT returned the exact nonce and Test ID, generated its own
159-byte text download, and Friday imported it as a real from-website attachment.
The owner-authenticated download route returned the expected exact bytes (original
139-byte content followed by RETURN_VERIFIED=yes and newline), with matching SHA256.
No local Harness tools were requested or executed by this website-native task.

Native run: aebdab1f-4981-4c61-b96e-f4e3900c3c29. One to-website record was delivered; exactly one
from-website file was saved. After refreshing the idle Friday page, both records,
the paired chat URL/tab, full committed reply and native event digest remained
unchanged. Cursor reconnect returned precisely the remaining saved events. No
prompt, upload or generated-file action was replayed. Final pending count: zero.

Evidence: ../../output/friday-native-transfer-audit.json and
../../output/friday-native-transfer-recovered.jpg. Read-only recheck:

    node tasks/native-transfer-audit.mjs recovery

No production code, extension version or permission settings changed. The current
348-test regression result remains applicable. This gate verifies TXT with this
ChatGPT account; it does not establish equivalent upload/download capabilities for
all provider websites, every advertised extension, large files or interrupted
uploads. Those remain separate acceptance cases.

## Mixed native attachments and stream cancellation (0.10.2)

Passed a real native-composer message with a PNG and TXT together. The document's
random token appeared only in the attachment. ChatGPT returned it and calculated
17 × 3 = 51, then correctly described the image's left red circle and right blue
square. Both delivered file records matched the exact original fixture bytes and
SHA256 values; native image transport used its normal screenshot-style filename.
No local tools ran for the analysis. Run: b4e4e158-fff2-4739-adcf-736d14deaaf4.

A separate deliberately long text response was cancelled after 374 native
streamed characters. Native outcome was cancelled, the ChatGPT Stop control
cleared, and the bridge returned to zero pending requests. Exactly one browser
request and one confirmed submission were recorded. No tools or file operations
ran during cancellation. Cancelled run: 84953004-9b34-4b19-9592-5e643d9dba0a.

A fresh task then executed exactly one native pwsh print command and returned its
complete result in the same saved chat. Run: 235beebc-553d-4295-99a8-2da1feb47040. A repeated
cancel of the old completed run returned alreadyFinished=true; it did not cancel
new work. The cancelled transcript stayed unchanged. PNG/TXT attachments and the
earlier generated download retained identical identities, metadata and hashes;
no duplicate transfer was added. Final native task status idle, pending zero.

Read-only evidence checks (no tasks are resubmitted):

    node tasks/after-cancel-audit.mjs
    node tasks/mixed-transfer-audit.mjs --recheck
    node tasks/native-transfer-audit.mjs recovery

Evidence: ../../output/friday-mixed-transfer-audit.json,
../../output/friday-cancel-stream-audit.json,
../../output/friday-after-cancel-audit.json and
../../output/friday-after-cancel-recovered.jpg.

The older transfer-audit operator now pins its saved runId during recovery checks,
so a later unrelated task cannot be mistaken for the upload task. Only operator
helpers and this audit changed; production connector code, extension permissions
and native approval controls are unchanged. The last full automated regression
remains 348 passed. These tests cover small PNG/TXT files and stopping website
text generation; they do not claim cancellation of an executing shell action,
a crash during upload, large-file recovery, or all providers' attachment support.

## Multi-megabyte attachment with active Friday refresh (0.10.2)

Passed a 3,408,072-byte native TXT upload (nine 384 KiB bridge chunks). The fixture
contained 65,536 synthetic records and independent head/footer tokens absent from
the prompt. ChatGPT reported both tokens, the record count and the exact SHA256
of the full original file. The owner download route returned bytes identical to
the local fixture; there was one delivered file record and no local tool execution.
Run: 37d81ccb-47bd-4c3a-b7f2-e75f752a82a4.

Friday's page was refreshed while its task activity explicitly showed uploading,
at 2026-11-11T04:07:55.198Z. The existing website request began at 2026-11-11T04:07:54.673Z and its
single confirmed submission occurred at 2026-11-11T04:08:19.862Z, after that refresh.
The same native task continued and committed its complete reply. The audit found
one attachment-bearing browser request, one submission and one delivered record;
its cursor reconnect returned exactly the remaining saved events. Pending zero.

Evidence: ../../output/friday-large-transfer-audit.json,
../../output/friday-large-refresh-before.json and
../../output/friday-large-upload-recovered.jpg. Read-only verification:

    node tasks/large-transfer-audit.mjs --recheck

This tests refreshing the Friday observer while the Chrome worker and paired
ChatGPT page stay running. It does not simulate a network outage, extension-worker
crash, refresh of the ChatGPT page, or maximum-size file. No production connector
code, permission controls or extension version changed during this acceptance.

## ChatGPT page reload recovery candidate (0.10.3)

Live testing reproduced a lost page listener after refreshing ChatGPT mid-stream.
The ordinary outbound-task recovery fix is installed and all 352 automated tests
pass, but its live post-update gate is pending Chrome activation. See
PAGE_REFRESH_RECOVERY_AUDIT.md for scope, retained failure evidence, artifact
replay guards and current activation state. This is not a production-release signoff.

## Activation confirmed; browser-control blocker

Both backend and Chrome extension now report 0.10.3. The first post-activation
probe failed a Chrome tab lookup before submitting anything (run
870a4b3c-fd4a-453d-8c22-9697c4e1ea9a). A subsequent targeted readiness probe
responded ready, and an independent text task completed normally (run
a1db9061-3a5d-4e45-87e2-98e95970a2b9): 26,891 reply characters committed,
one browser request, one submission, zero tools, final pending zero.

Codex's browser-control transport returned Debugger unattached for the attempted
live refresh. Reclaiming the same saved tab did not restore that operation. A
manual-refresh request was issued, then explicitly withdrawn when the response
finished before a refresh was confirmed. There was no post-text reconnect event;
the ordinary successful response is not counted as a page-reload acceptance.
Evidence: ../../output/friday-page-refresh-103-control-blocked.json.

The live verifier tasks/page-refresh-audit.mjs requires a real reconnect after
text begins, a complete bounded reply, one request/submission and correct native
history. It will reject this non-refreshed run. Current live refresh-recovery
status remains unverified; extension activation is complete and no further
extension reload is required for the installed candidate.
