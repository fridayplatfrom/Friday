# Browser provider validation — 10 November 2026

## Current automated checks

### Same-task provider switching and website continuation

Latest connector regression run: **282 passing tests**, zero failures, in
`output/friday-model-switch-tests-2026-11-10.txt`. Native model selection now
retains independent acknowledged provider checkpoints. Handoffs contain recent
native execution receipts independently of model-generated compaction summaries.
Failed delivery leaves the confirmed provider/checkpoint unchanged; pending tool
results block handoff. Saved URLs/checkpoints, invalidation and restart recovery
are covered by `tests/handoff.test.mjs`. Existing Harness tools and permissions
remain authoritative. No automatic provider switch or tool replay was added.

Live session `session-da5ab260-80c8-4198-a7c2-ef8ddd0b643f` switched Kimi → Gemini
through the existing selector. Gemini continued in the same orbit-studio-kimi
directory through native read/write/pwsh tools. Both original provider URLs were
retained through backend restarts. Returning to Kimi reopened its saved chat, but
the provider capacity notice blocked completion; no tool ran on that attempt.
Gemini was selected again. Evidence: `output/friday-model-switch-live.json` and
the per-run `output/friday-orbit-*-web-*.json` records.

Native Compact completed but generated an inaccurate file-completion claim.
Operator inspection and committed tool receipts corrected it before continuation.
An oversized frontend pwsh command failed with ENAMETOOLONG; native write tools
then created real HTML/JS/CSS. Decorated tool markers are rejected and may receive
the existing bounded format-correction request, never executed as decorated text.

Website preview runs in native background job `pwsh-a59c23914544445b` on
127.0.0.1:8010. Native job_output confirmed startup. Fourteen independent real HTTP
checks pass against an isolated database, including CRUD, comments/checklists,
archive/restore, activity, restart persistence, invalid input and private-path
rejection: `output/friday-orbit-api-qa.json`. Native nested-child execution was
blocked with EPERM; these acceptance checks were run by the operator terminal
without widening Harness permissions. The generated project's test.mjs is not
counted as integration evidence.

Operator browser tests created a retained QA task, moved it to Done, added a
comment and checked a checklist item. Reload and search retained all changes.
Evidence: `output/friday-orbit-desktop.png`, `output/friday-orbit-current.png`.
Mobile inspection found toolbar overflow; this is an unfinished website issue,
not a passed mobile test (`output/friday-orbit-mobile.png`). Full keyboard focus
management and every original website requirement remain unverified.

After extension reload, Chrome reported 0.9.2. Subsequent tests exposed stale
tab IDs/message-channel loss, a Gemini page readiness failure and a Kimi editor
retention failure before submission. Therefore reconnect/return behavior is not
claimed flawless. Prepared extension 0.9.3 restores the established insertText
path for single-line Kimi wire requests while keeping multiline paste behavior;
regression tests pass, but this correction has not yet been live-verified.
The Kimi capacity handler offers waiting/manual model selection, describes paid
priority as optional and invents no retry deadline. Capacity detection is tested
against the observed modal structure; the latest live attempt failed earlier at
editor verification and did not exercise the popup handler end to end.

### Earlier rollout evidence

The Gemini/Kimi rollout now passes **274 tests**, with zero failures:
`output/friday-kimi-capacity-tests-2026-11-10.txt`. The backend is 0.9.2;
the prepared installed connector is 0.9.2, while Chrome last reported 0.9.1.

- Gemini completed an actual single native pwsh call and returned the full
  179-character report with both required markers. The real command output and
  report survived a Friday refresh and were visible in native tool controls.
  Evidence: `output/friday-provider-gemini-web-live-2026-11-10.json` and
  `output/friday-gemini-tool-success-2026-11-10.png`. The evidence retains the
  exact backend/extension versions used in that run; it is not a 0.9.2 claim.
- Kimi.ai executed six native initialization tools in the first ORBIT session,
  then exposed temporary-to-canonical chat URL pinning problems. A second
  session was explicitly paired to its saved canonical URL through Friday's
  existing pairing control. It executed a native pwsh workspace check, created
  the empty orbit-studio-kimi directory, checked Node v24.13.1 and confirmed
  port 8010 was free. Evidence: `output/friday-orbit-kimi-run-workspace-check.json`.
  This verifies a real native tool round trip, not a completed website.
- The oversized implementation response timed out without executing a tool.
  Subsequent small-step requests encountered Kimi's native function/tool
  behavior and then its visible capacity dialog. A clean page refresh and retry
  hit the same capacity notice. No backend or frontend files were created.
  Pending requests were stopped; no subscription purchase or provider switch
  was made. Evidence: `output/friday-kimi-capacity-block.png`.
- Prepared connector 0.9.2 recognizes the observed Kimi capacity dialog, tracks
  its `.send-button-container.stop` generation control, and permits provisional
  Kimi URLs to promote to canonical URLs while protecting established chats.
  Regression tests cover immediate capacity failure without stale completion
  or duplicate submission on both Kimi domains. These source fixes are tested
  and copied locally but are **not live-verified**: Chrome still reports 0.9.1.
- A complete-page DOM check found no new content-build marker after a website
  refresh, confirming that the corrected local source had not been injected.
  Update discovery now reads the installed manifest through authenticated
  loopback status. Setup publishes the manifest after copying scripts/config.
  Tests cover changing the installed version without restarting the server and
  the automatic updater seeing that version despite a cached Chrome manifest.
  A live automatic version-change test remains pending the bootstrap reload.
- Coverage also includes Gemini/Kimi submitted-message correlation, semantic
  generation status, literal tool JSON, multiline Lexical insertion, cancellation,
  confirmed/uncertain refresh recovery, Kimi URL compatibility and URL admission,
  default provider enabling and preservation of explicit disabled choices.

Historical provider milestone:

The current provider-framework run passed **245 tests** (zero failures), using
`npm test` with two concurrent test files. Evidence is in
`output/friday-provider-tests-2026-11-10.txt`. The backend is 0.8.7 and the
installed connector is 0.8.8. The results below retain their historical versions.

Live Chrome acceptance on 10 November:

- ChatGPT: controlled disconnected request failed before submission; re-enabling
  the connection completed one native print command and a full 603-character
  report. Evidence: `output/friday-provider-live-2026-11-10.json`.
- DeepSeek: after fixing its observed span-only `pre` rendering, code-toolbar
  extraction and generation detection, one native print command completed and
  the full 490-character report returned through native Harness. Earlier rejected
  malformed replies executed nothing. Evidence:
  `output/friday-provider-deepseek-web-live-2026-11-10.json` and
  `output/friday-deepseek-provider-success-2026-11-10.png`.
- Connector 0.8.8 activated automatically without a manual reload. DeepSeek's
  paired page then answered the health probe and passed the tool round trip.
  A subsequent version-only 0.8.9 activation probe was conservatively deferred;
  not every paired page confirmed idle readiness. That probe was withdrawn,
  leaving the tested 0.8.8 installed. Do not interpret this as proof that every
  browser or stale-listener condition can recover unattended.
- Automated updater cases cover restored tab IDs, closed tabs, drafts, active
  generation, unresponsive listeners, unrelated chats, incognito and an agent
  starting during inspection. No task replay or automatic provider switch occurs.
- The native answer controls retained Copy and Branch and no longer displayed
  like/dislike buttons. Native permissions, questions, compaction, files and AG-UI
  regression suites remain in the passing run.

DeepSeek remains an experimental text/tool backup. Image/file/two-way parity is
not claimed. Existing native features remain authoritative; capability metadata
rejects unsupported website transfers before submission.

The earlier v0.4.14 automated run passed **143 tests** and is recorded in
`output/playwright/connector-v0414-tests.log` from the repository root. Earlier
live results below describe the version under test at that time.

## v0.4.0 reliability and attachment upgrade

Implemented and covered by controlled tests:

- Original-byte transfer for the declared image, text/data, source, PDF, Office,
  ZIP, audio and video extensions, without execution or automatic extraction.
- Persistent chunk ordering, duplicate chunk acknowledgements, conflicting chunk
  rejection, SHA-256 verification, size limits, path validation, cross-session
  isolation, interrupted transfer resume, and verified readable local copies.
- Authenticated owner download/diagnostic routes; HTML/SVG remain downloads rather
  than executable previews. Extension file reads are scoped to active jobs/pairs.
- Website upload reconstruction, input assignment, visible processing confirmation,
  and failure before prompt submission for missing/rejected/unconfirmed uploads.
- Website-selected file capture, generated download links, native reply attachments,
  and persistent manual fallback notices for inaccessible/unrecognized outputs.
- Native Harness image resolution through its attachment service; model prompts
  contain image references, not raw image base64 or fictitious filename-only uploads.
- Append-only full-context/reply journal, interrupted-write tail recovery, final-event
  receipts surviving restart, same-job recovery dispatch, and restored response
  capture without typing/submitting a second prompt. An uncertain submission stops
  for review; no completed tool operation is automatically replayed.
- Confirmed incremental context; catalog/history changes reset to full snapshots.
  Reduction preserves human instructions and tool-call/result identities, with
  explicit excerpt notices and the original context in the local journal.

The installed native Harness runtime starts with the upgrade and exposes its local
bridge. Live browser testing was attempted, but this Codex session's browser-control
tool failed to initialize with a missing kernel-assets path, including after reset.
No alternate browser-control mechanism was used. Consequently real signed-in upload,
download, screenshot picker, refreshed-page recovery and provider-specific file
analysis still need live verification of v0.4.0. Existing text/tool workflows remain
covered by regression tests and the earlier live evidence below. Other providers'
attachment automation and live voice conversation are not implemented.
After the user's extension reload, the live bridge reported `extensionVersion:
0.4.0`, `connected: true`, ChatGPT enabled, and zero pending jobs. This confirms
activation/connectivity; it does not establish real website attachment compatibility.

Coverage includes bridge authentication/Origin/Host fences, native Models owner
access, streaming adapter output, tool encoding and feedback, input bounds,
cancellation, website failures, paired-tab draft replacement, session pairing, startup
preferences, signed-out editor detection, response identity, delayed Send controls,
and completion only after visible response actions. Controlled DOM fixtures do
not establish live provider compatibility.

## Two-way ChatGPT mode (v0.3.0)

Controlled checks cover authenticated admission from the exact enabled paired tab,
trusted native submissions, no echo from programmatic Harness sends, durable message
receipts, interruption ordering, stale cancellation, scoped response capture by native
turn identity, missing capture without resubmission, native agent error status, and
rejection of a switch to a model API route. Incomplete tool prefixes or malformed
tool JSON receive at most one format correction before any tool call is emitted;
unknown tools, website failures, and already-streamed ordinary text are not retried.

The live extension reported v0.3.0. A new Harness conversation received the v2
introduction acknowledgement and exact `TWO_WAY_SETUP_OK` response in the same
paired ChatGPT tab. Enabling the native Harness button displayed the two-way status
panel in ChatGPT. A request submitted directly in ChatGPT appeared once in Harness,
without a duplicate human prompt being posted back to ChatGPT. Its first reply was
only `HARNESS_TOOL_CALL`, with no JSON, so no local action was executed. This led to
the bounded format-correction path above.

The subsequent live native ChatGPT request completed in 20 seconds: its prefix-only
reply automatically received one correction request, which produced a complete
`write` call. Harness created `two-way-check.txt` in the default workspace and sent
the actual tool result back to the same ChatGPT conversation. The final confirmation
appeared in both ChatGPT and Harness. Independent filesystem inspection found the
requested text `Two-way chat works.` (with the writer's final newline). Harness
recorded one write and one final response for this successful turn. Two-way mode
remained enabled and the website panel returned to its ready status. Screenshots:
`state/browser-harness/review/two-way-chatgpt.png` and `two-way-harness.png`.

The older GOODBOY conversation exceeded the 80,000-character request limit on a
setup request, before dispatch. It was preserved; this test uses a fresh conversation.
Long-session compaction remains a limitation.

## Refresh and offline recovery (v0.3.1)

Inspecting the original Harness tab found a blank native UI, with console evidence
`uiConversation.binding: unknown session` during reconnect. Reloading restored the
same saved replies, paired URL and enabled two-way setting. Expanding **Completed
in 20s → Wrote files** also restored the visible native write details; those tool
events were saved and collapsed, not deleted. The native persisted test session
remained on disk as `session.v4.jsonl.zstd` (33,320 bytes at inspection).

New controlled checks cover a separate page-health guard, offline/restarted backend
states, recovery of a blank native view without reloading an open editor, extension
offline status broadcasts, one website notice per offline/restored transition, and
preserving unsent drafts. The paired-tab notice uses a programmatic send so it never
becomes an inbound human Harness task. Automatic replay of completed tool calls is
not part of recovery. Live extension offline notices need v0.3.1 to be loaded.

Further live inspection found two newer website user turns (the TikTok-game request
and the website's generated Build action) absent from Harness. This is a separate
admission gap, not deletion of already persisted history. Version 0.3.2 observes
the current `data-user-message-bubble` layout and new native user turns following
human interaction, including interactive website buttons. Explicit outbound prompt
suppression prevents tool feedback and connection notices from echoing. Controlled
checks also reject replay of older virtualized history loaded by scrolling. Existing
missed turns are not silently re-executed after an extension refresh.

Live shutdown/restart verification subsequently succeeded: the native Harness view
showed its offline banner while retaining history, and after restart a blank native
view recovered automatically. The paired ChatGPT tab received the offline notice,
answered that it would wait and that no file changes were confirmed, then received
the restored notice and answered that it was ready. Its panel returned to ready.
A fresh native ChatGPT message requesting `REFRESH_SYNC_OK` entered Harness once
and completed in seven seconds after recovery. No notices appeared as native human
tasks. Screenshot: `C:/Users/ankus/Pictures/Screenshots/chatgpt-harness-offline.png`.

Another live refresh exposed website hydration removing the injected status panel.
Version 0.3.3 reattaches a removed panel on the next heartbeat, covered by a DOM test.
On loading v0.3.3, the panel was visible but showed a lost heartbeat while the bridge
still reported connected and returned an enabled ready listener for the exact pair.
Version 0.3.4 adds a page-requested status heartbeat as a fallback to background push
delivery. Its handler validates sender tab identity, conversation URL and enabled
settings, and bounds readiness by the last successful bridge heartbeat. Controlled
checks cover offline/online pull responses, rejection of other tabs, and applying
pulled state when push delivery is missing.

The live bridge subsequently reported v0.3.4. Refreshing the exact paired ChatGPT
tab restored the visible ready panel after the page finished loading, without
toggling two-way mode or creating a new conversation.

## Observed live in the built-in browser

- Settings → Models shows website rows and icons using native Harness slots,
  buttons, colors, and authenticated session. The separate Connections UI is gone.
- Harness startup opens the saved website and enables the editable signed-out
  ChatGPT composer without requiring login. Disconnect persists an opt-out.
- The signed-out layout uses mobile-composer-prompt, Send message, and assistant
  DIL content regions inside UUID list items. These are now supported.
- The exact reply “Signed-out Harness reply received.” returned into Harness and
  completed in five seconds.
- A longer gravity answer appeared incrementally while generation remained active
  and completed in eight seconds.
- The local form task executed native browser navigate, snapshot, and fill tools.
  A complete click request submitted it once. Independent /result verification
  returned all five expected fictitious fields. Native tool output returned to
  ChatGPT and its subsequent explanation appeared in Harness.
- Explicit protocol reminders were needed: the website model initially declined
  tool use and later emitted only HARNESS_TOOL_CALL without JSON. Incomplete
  requests were rejected without execution. A retry with complete JSON worked.
- Conversation rollover continued the tool loop in the existing managed tab.
  A later attempt exposed delayed Send rendering; the worker now waits for an
  enabled Send button instead of treating its immediate absence as final failure.

Earlier signed-out timeouts were incorrectly interpreted as missing website
replies. Direct inspection showed that ChatGPT had replied; the connector was
missing its new response layout. That diagnosis is corrected above. The source
of the later prefix-only failure was the model's actual incomplete reply, not a
split-block extraction bug.

The form server stores data in memory; restarting Harness resets the fixture.

## Earlier extension transport

The user loaded the extension and a signed-in ChatGPT account completed a normal
chat and a native PowerShell calculation with tool feedback: 12345 + 6789 = 19134.
The current web profile now uses this normal Chrome extension transport.

## Chrome image and session pairing update

- Extension v0.2.2 treats the current assistant's standalone response-load placeholder
  as a waiting status, never answer text. It observes the same reply without automatic
  regeneration or resubmission, pauses the local response timeout while waiting,
  resumes on real content, and still supports cancellation. Bridge status reaches the
  existing native composer. Controlled tests cover recovery after the normal timeout,
  loading after partial text, indefinite waiting with cancellation, and the managed
  worker equivalent. A live naturally occurring recovery remains to be tested after
  reloading the extension and refreshing the paired website tab.

- First coding/task request now sends a separate protocol introduction and waits
  for `HARNESS_READY`. Controlled bridge tests verify order, reuse on follow-ups,
  cancellation and acknowledgement failure without task submission, independent
  sessions, and image-only bypass. Store tests verify persistence and conversation
  URL reset. The introduction was subsequently acknowledged in the live GOODBOY
  landing-page session documented below.

## Live GOODBOY landing-page result

- Session `session-f454b7cb-46f5-440d-9353-9bf29273e3f8` records a greeting followed
  by one build prompt: "create a landing page for the dog food". The persisted
  introduction acknowledgement and all subsequent requests used the same paired
  ChatGPT conversation.
- The build took approximately 5m29s and made eight tool calls: two globs, one write,
  one read, one browser navigation, two PowerShell calls and one job-output read.
  Seven tool calls reported success; browser navigation was blocked. The model
  subsequently checked the server, found it stopped, and started the existing
  `portfolio-demo/serve.mjs` worker. This is one successful build run, not a claim
  of universal unattended reliability.
- The write created the 16,693-byte GOODBOY HTML/CSS/JavaScript landing page at
  `C:/Users/ankus/Documents/deepseek-harness/default-workspace/portfolio-demo/index.html`.
  Independent HTTP verification returned 200 at `http://127.0.0.1:8008/`.
- Browser review confirmed all five remote images loaded, empty-cart feedback,
  product addition and cart feedback. At 390px the page had no horizontal overflow.
- Remaining defects: CSS overrides the mobile navigation's hidden attribute, leaving
  duplicate navigation visible; the final captured assistant response is literally
  "This response couldn't load", yet the turn is marked completed. That response-load
  failure needs explicit connector handling. The cart is a local demo, and checkout
  is explicitly unconnected.
- Evidence: `state/browser-harness/review/goodboy-desktop.png`, `goodboy-mobile.png`
  and `dogfood-session-events.json`. Reviewing the result did not edit the website.

- Image-only routing now sends exactly the real human image prompt with no Harness
  system/tool/history wrapper. It uses message source metadata to skip runtime,
  skill and time snapshots. Bridge tests verify the dispatched prompt even when
  agent context exceeds the normal serialized-prompt limit, and verify that image
  replies cannot execute Harness tools. This validates routing, not a successful
  live image-generation round trip.

- Installed v0.2.0; the bridge confirms that version is connected.
- A real Harness image request opened its dedicated ChatGPT tab and saved its
  conversation URL. Retrying in the same Harness session reused exactly the same
  tab ID and conversation URL.
- Native image percentages 16% and 20% reached local session state in successive
  attempts. Harness visibly displayed 20%, a progress bar, progress history, and
  paired-chat/Copy URL controls in its native composer.
- First attempt ended with a connector timeout. The retry returned the website's
  explanation that its image-generation tool failed. No image or 100% completion
  was invented. Successful live image transfer remains pending.
- Controlled tests cover image-only completion, chunk order and bounds, raster
  signatures, native image Markdown, persisted previews, owner-only media access,
  progress history, owned-draft replacement, concurrent tab-acquisition deduplication,
  and per-session isolation.

## Chrome retest — 10 November 2026

- Playwright CLI attached to normal Chrome through the Microsoft Playwright
  extension, opened the existing local Harness, read its UI, created a separate
  session, and submitted a synthetic text-only prompt.
- The delivery journal identified a concurrent `dsh-session-title-llm` metadata
  call eight milliseconds after the agent request. Both used the website bridge;
  the title call failed busy and overwrote the active conversation's status.
- Session-title metadata now produces a bounded local title without touching the
  website, pairing, journal, or running task status. A regression test exercises
  naming while a real bridge request owns the slot. All 116 tests pass.
- The main live request separately failed to locate a usable ChatGPT editor.
  Subsequent user retries included a closed website tab. These do not establish
  a successful v0.4.0 text/file/image round trip.
- Activating the title fix requires a backend restart. Two automatic restart
  attempts were rejected by approval review as blocked by policy. The source fix
  is tested, but activation and the next live test remain pending manual restart.

## Codex browser retest and v0.4.2

- Harness was launched after the device restart and opened in the Codex browser.
  A live text request completed in 27 seconds: `HARNESS_RESTART_OK_4827` appeared
  both on the paired ChatGPT page and in Harness. Refreshing Harness preserved
  that answer and its exact paired conversation URL.
- ChatGPT initially remained on its startup logo, then opened Work mode. After
  the page loaded and Chat mode was selected, the existing text connector worked.
  Login was not forced or a security restriction bypassed.
- A synthetic text attachment reached ChatGPT, but upload confirmation looked at
  a retained hidden home-page form. v0.4.1 scopes file selection to the visible
  editor's form, with a regression fixture containing both hidden and visible
  composers. The stalled upload was cancelled through Harness and showed Stopped.
- The v0.4.1 live retry did not reach upload: website readiness failed, and Chrome
  inspection also became unresponsive. No successful file/image round trip is
  claimed from that run. The file remained staged.
- v0.4.2 bounds each read-only readiness probe, accepts an interactive page with
  a usable editor even while assets remain loading, reserves a job before tab
  acquisition, ignores duplicate dispatches of that job, and prevents a frozen
  status listener from blocking dispatch/cancellation polling. Tests cover these
  failure modes and cancellation during delayed acquisition. All 120 tests pass;
  see `output/playwright/connector-v042-tests.log` from the repository root.

## v0.4.3–v0.4.5 live findings

- v0.4.2 dispatched from a new session without a title-call collision, but the
  initial website send encountered ChatGPT's account-change error. A subsequent
  task send repeated the introduction on the website despite the bridge journal
  containing the correct task prompt.
- v0.4.3 waits for the observed account-loading control to settle, reacquires the
  visible editor after upload, checks retained prompt text before sending, scopes
  Send to its form, and checks the new submitted user bubble before acknowledging
  delivery. Live exact-text verification returned `CONNECTOR_043_READY` to Harness
  in 12 seconds. A refresh while an upload was processing retained the running task.
- ChatGPT renamed the 188-byte text upload to `connector-fixture(1).txt`. v0.4.4
  accepts the observed numeric duplicate suffix and requires a distinct reported
  filename for each input. Its live upload was read correctly by ChatGPT, which
  returned `HARNESS_FILE_TEST_4827 Amber, Cobalt, Jade`, but Harness rejected the
  submitted-message verification: the parent bubble appended the decorative
  ellipsis and Show more control text.
- v0.4.5 reads the observed `[data-search-result-target]` message-content element
  within the user bubble, excluding these display controls, and waits for its
  rendered text before acknowledging delivery. All 125 tests pass, including
  contenteditable draft reversion, wrong-message rejection without resubmission,
  account-loading waits, renamed multi-file confirmation, and overflow controls.
  See `output/playwright/connector-v045-tests.log` from the repository root.

## v0.4.6 turn identity

- The next live retry showed the exact expected prompt in ChatGPT and its correct
  file-reading answer, but verification could select an older remounted user turn.
  v0.4.6 searches newly observed keys for the latest exact message-content match,
  then restricts response and asset capture to that verified key. Unrelated later
  turns and remounted older messages cannot provide that request's response.
- All 126 tests pass, including an older turn remounting before the actual new
  turn and a later unrelated response. The installed extension was reloaded by the
  user and the same saved synthetic text file was queued for a live retest.

## v0.4.7–v0.4.14 live verification

- A 188-byte text upload was read by ChatGPT and returned its hidden verification
  token and three names correctly to Harness (26 seconds).
- A synthetic 96×96 image uploaded through the native Harness composer returned
  `COLOR=red; SHAPE=square; BACKGROUND=white` (21 seconds).
- A message typed directly in the paired ChatGPT website returned
  `TWO_WAY_049_OK` in both interfaces without a duplicate submission (5 seconds).
- Idle development updates automatically activated versions 0.4.9 through 0.4.13.
  Drafts and active requests are excluded from automatic tab refresh.
- After the user granted optional Downloads permission, native website generation
  of `connector-output-v4.csv` reached Harness as a downloadable attachment (20
  seconds). Its stored bytes were read independently: `item,quantity`, `Amber,3`,
  and `Cobalt,5` on separate lines. The streaming decoder accepted ordinary text
  revisions without resubmitting the request; tool-prefix changes remain strict.
- A generated blue origami sailboat arrived as a 1254×1254 PNG and loaded in the
  native Harness assistant message (47 seconds). Earlier relative image Markdown
  failed; the adapter now supplies the saved absolute local asset path.
- This run exposed a new native image progress label, “Making the first draft.”
  v0.4.12 recognizes it; the percentage regression test starts with that label.
- A local tool test recovered from an incomplete prefix, successfully searched
  and wrote its synthetic file, then stopped before a read because native
  “Thinking” status was mistaken for ordinary answer text. v0.4.13 excludes that
  placeholder for ordinary agent turns as well as image requests, preserving
  strict rejection of actual text-to-tool mode changes. The retry reads only;
  it does not repeat the completed write.
- v0.4.14 verifies the current composer text and Send control after a native
  editor remount. Its live read-only retry completed in 1 minute 45 seconds:
  Harness's `read` tool returned `20413`; an independent filesystem read confirmed
  the same five bytes in the default workspace's `connector-qa/roundtrip.txt`.
  Earlier successful writes were not replayed.
- Final native generation of a green origami turtle completed in 37 seconds.
  Harness visibly displayed `Sketching it out · 48%`, a progress bar, and retained
  the observed sequence 34% through 48% after completion. The finished image
  appeared inline. No unobserved 100% or intermediate percentages were invented.
- Refreshing Harness retained the completed replies, generated image, attachment
  list, two-way setting, exact paired ChatGPT URL, and 34%–48% progress history.
  The initial workspace placeholder disappeared after normal UI hydration.
  Screenshot: `output/playwright/harness-v0414-final.jpg`.

## Local application image-job checks

The additional backend image-job interface passes the full **148-test** suite
(`output/playwright/connector-image-jobs-tests.log`). Tests cover owner-token and
Origin fences, input validation, an active Harness task, hourly limits, actual
saved raster bytes, job/image ownership, persisted receipts, no replay after
restart, and explicit errors for website failures or image-free replies. Live
store integration still requires activation and an end-to-end browser test.

## v0.4.15 native Harness controls

The full suite passes **152 tests** (`output/playwright/connector-native-controls-tests.log`).
Native file blocks now resolve through Harness's verified `readFileStream`
service, with bounded reads and explicit size/integrity/cancellation failures.
Tests cover exact bytes, delivered-reference deduplication, native goal/planning
tool schemas and returned calls, and native compaction-summary round trips.

The refreshed live UI no longer has the separate uploader, screenshot-capture,
attachment manager, duplicate image gallery or diagnostic export control. Its
native menu visibly contains File, Goal, Plan, Feedback, Compact, Permission,
Model and Export. Screenshot: `output/playwright/harness-native-controls.jpg`.
Stored connector files and diagnostics were retained. Backend activation and a
live native document transfer still require a Harness restart; these automated
tests are not proof that every native feature was exercised live.

## Friday naming (v0.4.16)

The connector's public name is Friday in Models settings, its connection status,
Chrome extension manifest/popup, two-way website panel and documentation. Existing
package/provider IDs, storage keys, routes and protocol discriminators stay stable
so saved pairs and conversations need no migration. All **152 tests** pass
(`output/playwright/friday-rename-tests.log`). The updated unpacked extension was
published to the existing installation using its idle development updater.

## v0.4.17 native file projection correction

The first live generic-file test reached ChatGPT but no file bytes were uploaded:
Harness's LLM core converts file blocks to read-only path handles before adapter
dispatch. Friday now captures admitted references in the native `llm/stream` hook,
then restores them only when the exact host-produced placeholder and native
message/session identity match. Arbitrary path text is never interpreted as a
file upload. Reference memory is bounded. Native image handling is unchanged.

All **153 tests** pass (`output/playwright/friday-native-core-tests.log`), including
a test of the actual before/after core projection, wrong-session/message/modified
placeholder rejection, byte transfer and existing integrity/cancellation checks.
Backend restart and live verification of this final pipeline correction remain
pending. The initial live attempt is explicitly a failure, not a file-upload pass.

GOODBOWL runtime verification is separately blocked by available disk capacity:
MongoDB reports `No space left on device` with about 30 MB free on C:. The user
will free space later. Cleanup of the newly created failed test databases was
rejected by automatic approval review and was not performed.

## v0.4.18 long-context transport

The full suite passes **158 tests** (`output/playwright/friday-context-transfer-tests.log`).
When a normal request cannot fit the 80,000-character per-message bound, Friday
stages the exact original serialized request across acknowledged context-only
messages, then sends an explicit task commit. Tests verify lossless reconstruction
of Unicode, escapes, tool schemas and human instructions; bounded message sizes;
only one final tool call reaching Harness; incremental follow-up; and no commit
or checkpoint advancement after bad acknowledgements, tool-prefix replies during
staging, or cancellation. Aggregate size and part count remain bounded.

A replay using the recorded store context plus a continuation assembled 160,276
source characters into three messages of 71,468, 70,022 and 29,783 characters, plus
a 762-character commit. This is a local protocol replay, not a live website pass.
The backend update requires a restart and live validation before claiming the
browser handoff is proven. Native Harness Compact remains the long-term history
management control; this fallback is only transport, not a replacement summarizer.

## v0.4.19 native compaction configuration

Inspection of the installed native `command-compact` and `compaction-basic`
implementations confirmed `/compact`, automatic pre-step compaction and an
incompatible default headroom of 65,536 versus Friday's former 16,000-token budget.
Friday now declares a 32,768-token planning budget. The native current-preset
configuration was backed up, configured for the ChatGPT website route, and parsed
successfully with the official Harness CLI. All original preset plugin identities
and ordering were checked before/after; the native compaction implementation and
permission controls were not replaced.

All **160 tests** pass (`output/playwright/friday-native-compaction-tests.log`).
New checks cover compatible pressure/output/retention budgets and policy generation
that preserves existing plugins, refuses custom config replacement, and handles
blank lines without duplicate YAML keys. One formatting error was caught during
CLI validation and rolled back before the corrected profile was applied.

Native automatic compaction and the multipart fallback still need backend restart
and live validation. The 32k budget and token estimates are local scheduling
settings, not measured website token usage or an asserted website context window.

## v0.4.20 native API compatibility audit

The installed core packages are 0.2.1-rc.5. A read-only static ASAR inventory
found 84 Remote method declarations in 25 service files across 305 package
manifests. This includes overrides and disabled services; it is not a live
gateway endpoint count. See API_COMPATIBILITY.md and
output/playwright/friday-installed-api-inventory.json for scope and details.

All **170 tests pass** (output/playwright/friday-api-compatibility-tests.log).
New coverage verifies source/id preservation without opaque replay leakage,
active/deferred/removed tool schemas, indexed independent tool-call batches,
whole-response protocol rejection, split stop markers and cancellation cleanup,
no retry of stopped partial tool JSON, native prepared-call error/abort finishes,
unsupported sampling-control errors, advisory token budgets, and compaction
isolation from task tools/image shortcuts. The inventory parser is also tested.

The live status endpoint reports the extension connected, version 0.4.16, with
zero pending requests. This proves heartbeat connectivity only. Backend 0.4.20
and the preceding native-file/context changes require a Harness restart and
live validation. No extension script change or reload is needed for this update.
No dog-food website files were edited during this audit.

## 2026-11-10 native Harness live checks after restart

Session: `session-a58e398c-f490-4663-8914-b85c6e72f26c`.
Paired website conversation: `6af2a6c6-0bf8-83ec-80a0-222f9db5c1b3`.

- Native File menu attached the synthetic 147-byte TXT fixture. The file appeared
  in ChatGPT's upload UI, was read without local tools, and the reply returned to
  Harness with `FRIDAY_NATIVE_7612` and Salmon, Pumpkin, Oats. This verifies the
  admitted-file capture/restore fix live for TXT, not every allowed format.
- Native tool execution returned actual PowerShell results `437` and `303`.
  The requested independent batch initially produced only an incomplete prefix
  and opening bracket on the website. Friday emitted no calls from that reply;
  bounded correction recovered with valid sequential calls. Batch decoding passes
  local tests, but successful live batch generation is NOT established.
- Native Compact completed: UI reported **10 history items (~884 tokens)**.
  Its auxiliary request had no offered tools. A subsequent request correctly
  recalled the verification value, ingredients and both arithmetic results,
  without another file upload or tool execution. This verifies manual compaction
  and post-compaction continuation. Automatic pressure-triggered compaction then
  ran during the website task (15 history items, ~5188 tokens), and Friday
  continued reading the backend. Multipart transfer still needs a live check.
- The existing GOODBOWL project continuation was submitted through Harness in
  the same paired conversation. Website development and testing remain delegated
  to Friday, rather than direct edits by the supervising agent.

Evidence: `output/playwright/friday-native-file-live.jpg` and
`output/playwright/friday-native-compact-live.jpg`.

## v0.4.21 live-discovered image-status correction

The website task exposed a completed normal tool reply stuck behind a false
image-generation status. The current ChatGPT DOM wraps user and assistant text
in the same turn; image words quoted in supplied backend source were being read
as native generation progress. The detector now ignores completed turns, scopes
phase text to the assistant renderer, excludes user-contained progress bars,
and ignores HARNESS_TOOL_CALL responses. A regression test reproduces the shared
turn layout, and all **171 tests pass**
(`output/playwright/friday-image-progress-fix-tests.log`).

The pending turn was cancelled without executing its unconfirmed tool request.
The installed development updater automatically loaded extension **0.4.21**;
the authenticated status endpoint confirmed that version with zero pending jobs.
The paired chat was refreshed, then the native Resume Goal button resumed the
saved GOODBOWL task. No backend restart was needed for this content-script fix.

## 2026-11-10 GOODBOWL work performed through Friday

Friday resumed the existing project with native Goal and To-do tools, read the
existing backend/frontend/tests, and executed all website changes and probes
through Harness. Its first sandboxed npm test failed at child-process piped
stdio (`spawn EPERM`). The native exact-command retry completed in the Full
access mode shown in Harness: **13/13 tests passed**. No website test was counted
as passing from that initial denied run.

The persistent MongoDB startup then failed because its saved replica-set member
used port 60265 while the launcher picked a new random port. Friday inspected
logs and verified port availability, edited db.js through Harness, and restarted
the existing database on the saved port. It left the unrelated Chefpin database
process alone and preserved existing database files/journaling. HTTP health,
catalog and root each returned 200; health identified MongoDB.

Friday created two synthetic orders (HTTP 201), verified exact inventory
decrements and independently queried MongoDB for both persisted receipts:
`GB-7DC4DCF626` (499, apple-bites 89→88) and `GB-DD98C668FE` (2499,
chicken-crunch 42→41). An earlier probe had a PowerShell parse error and another
invalid probe failed; neither was reported as successful. Native browser
navigation to the store failed with ERR_BLOCKED_BY_CLIENT, so this run does not
establish desktop/mobile/cart UI coverage.

The real studio image job `5c562e36-9197-42d7-887d-dc3b9cd6290d`
completed with a saved 2,580,329-byte PNG, identity
`6c089ba3-a97c-4309-b2dc-071364198cc7.png`. The supervising agent viewed that
actual generated raster. No percentage was available in the terminal receipt;
no fabricated percentage was supplied. Store download verification was still
pending when the following connector issues were exposed.

## v0.4.22–0.4.23 image handoff and literal tool transport

- A website tool can accept an asynchronous image job before the shared browser
  becomes idle. The next native model call previously failed busy. It now waits
  for that owned image job, with cancellation and shutdown cleanup. Other native
  collisions still reject; no general parallel model capability is claimed.
- The website rendered PowerShell dollars in plain tool JSON as KaTeX maths.
  This was confirmed in the visible response DOM (`data-math-source` and KaTeX
  nodes); the corrupted reply was rejected before execution. Tool requests now
  request literal fenced JSON. The content script reads the one visible code
  block, excluding its JSON language heading, while retaining/rejecting outside
  prose rather than manufacturing a valid call by dropping text.
- Short response placeholders are buffered (up to the initial 256 characters).
  Uncommitted tool JSON may settle before validation; once ordinary prose has
  streamed it still cannot switch into tool execution. Longer text continues
  streaming incrementally, and block-end remains authoritative.
- Reply-format changes invalidate old incremental checkpoints, so an existing
  conversation receives the updated full instructions after backend activation.

All **178 tests pass** (`output/playwright/friday-literal-tool-tests.log`). New
regressions cover accepted-image waiting, cancellation without cancelling the
accepted image, shutdown without replacement submission, fenced literal command
characters, brief placeholders, uncommitted tool rewrites, streamed-prose guards,
visible code-block language headings and outside-text rejection. The real
bridge streaming test checks both initial buffering and subsequent live deltas.

The prepared restart helper succeeded this time and activated the backend; no
manual restart was required. The development updater then automatically loaded
extension **0.4.23**, confirmed by the authenticated heartbeat. The paired chat
was refreshed and the saved native goal resumed for download verification.

## v0.4.23 activated live follow-up

The literal fenced tool call reached native PowerShell intact after the update.
Its first download failed because the Harness restart had stopped the managed
store job, rather than because of corrupted command text. Friday listed native
jobs, inspected the relevant ports, restarted the store through Harness, and
verified both demo orders and stock survived the genuine database restart.

Friday then downloaded the existing studio image through the store's HTTP proxy:
2,580,329 bytes, image/png, signature `89 50 4E 47 0D 0A 1A 0A`, ValidPNG True.
No duplicate generation was requested. It wrote the website's QA.md itself with
the actual results and outstanding browser UI limitation. Evidence is saved in
`output/playwright/friday-image-download-live.jpg`; the actual generated image
also remains in the project's artifacts directory.

This establishes the fenced literal-command transport live. The shared image
waiting fix is activated and covered by local integration tests; a second live
overlapping image generation was not performed solely to recheck its waiting
state. Source package/extension are 0.4.23; 178 local connector tests pass.

## v0.4.26 hardening and existing-Harness-browser acceptance

User scope is explicitly the existing Harness browser only. The native browser
plugin retained its executable, isolated mode, identity and permission model.
The demo-only origin restriction was replaced with explicit task/asset origins
through a backed-up, CLI-validated profile patch. Native browser navigation then
opened GOODBOWL with its real title and snapshot; the previous
ERR_BLOCKED_BY_CLIENT failure did not recur. Font-host additions are prepared
for the final activation/recheck.

The current Friday instruction forbids alternate Chrome/CDP launches and the
older standalone browser QA scripts. Actual task interaction uses the offered
`mcp__browser__` tools. Native queueing and steering successfully delivered a
latency-reduction instruction: grouped checks operate on the existing native
page/context through browser_run_code_unsafe, without another browser instance.

Observed native results include cart quantity 2/subtotal 998; persistence across
reload; invalid-email validation; synthetic confirmation GB-DD8EBDE122 for 499
and a cleared bag; desktop 1440×900 with scroll width 1425; mobile 390×844 with
scroll width 375 and hidden desktop navigation. Native screenshots were saved as
goodbowl-native-desktop-2026-11-10.png and goodbowl-native-mobile-2026-11-10.png.
Full-page screenshots need sections visited to trigger their normal reveal
animations; they are not proof that every offscreen section was visually checked.

Native studio submission accepted one portrait request. The main model call
waited with `Image studio is generating — waiting for the browser connection`
instead of failing busy. The same job completed, and the existing native browser
reported its preview fully loaded at 1122×1402. The actual page download returned
suggestedFilename goodbowl-studio.png and failure null. Job identity:
50de3b95-437c-4bdf-bbfa-924e04ccec31, image identity:
f68206a6-08d0-4fc4-bd27-8b0de2bc5b79.png. No percentage was supplied by the
website; none was fabricated. Refreshing Harness during this task restored its
history, paired URL and continuing stream (128 steps at observation), with no
duplicate image submission.

All **189 local tests pass** (output/playwright/friday-hardening-tests.log).
New coverage includes origin validation/plugin preservation; sanitized failure
guidance and local attempt metrics; native Models controls with disabled-provider
polling and unknown-site rejection; bounded journal memory with complete saved
history; monotonic restart sequences; UTF-8 boundary/missing-delimiter recovery;
and rejection of math-corrupted tool JSON even if its visible text could parse.

The extension automatically loaded 0.4.26 while idle. Backend origin access and
diagnostics began live on 0.4.24; backend 0.4.26 was subsequently activated during
an explicit pause of the stalled model request. This activates bounded audit
memory, Models provider controls and remaining UI diagnostics. Full trace metadata
confirms six completed multi-call
tool replies and native multi-call assistant contexts; this supersedes the older
statement that successful live batches were not established.

Final backend activation completed on 2026-11-10. Both backend and extension now
report 0.4.26. Native Settings → Models successfully disabled and reenabled the
ChatGPT connector while idle, opening no new browser tab. The diagnostics display
transport attempts and latency with their limitations and a 2,000-record /
10.2 MiB serialized recent cache. Saved conversation history and the paired URL
survived restart. Screenshot: output/playwright/friday-models-v26-live.jpg.

The final form stage exposed an unavailable editor in the long ChatGPT website
conversation. Friday waited instead of replaying the request. It was explicitly
cancelled for the backend update; a scoped continuation was submitted afterwards.
The saved native form result was subsequently expanded and independently checked:
submitted:true, Demo request saved, Submission 1 accepted locally, with echoed
synthetic values. The route /submit accepts the POST; later GET /submit returned
404, which is not evidence that the earlier submission failed. It was not repeated.

The resumed native task received the real connection-refused browser error and
the MongoDB 10-second startup failure as native tool results. Friday inspected
the database setup, increased its launch timeout, and restarted the existing
persistent store as managed job pwsh-1c7bb535e41c4d3d. The independent read-only
health endpoint returned {"ok":true,"database":"mongodb"} afterwards. All
website changes and recovery commands were performed by Friday through Harness.

Post-activation native browser_run_code_unsafe scrolled normal sections, captured
desktop/mobile screenshots, and restored 1440×900. Both layouts again reported
no horizontal overflow and six products. Google font CSS was present and DM Sans
faces loaded; not every optional font face is used/loaded. Actual native output
files: goodbowl-native-desktop-post-0426-2026-11-10.png and
goodbowl-native-mobile-post-0426-2026-11-10.png. Desktop screenshot was visually
inspected, including previously offscreen revealed sections.

Friday reran the store suite after its timeout edit: 13 passed, zero failures,
12,718.663 ms. Its read-only MongoDB driver query confirmed reference
GB-DD8EBDE122 and total 499 survived the restart without another purchase. Friday
appended a detailed native-browser acceptance section to goodbowl-store/QA.md,
clearly separating historical standalone browser checks. Native font network
results also reported HTTP 200 for the Google stylesheet and three WOFF2 assets.

Native More actions → Download session log completed after backend activation.
The downloaded session ZIP is 1,344,121 bytes and opened successfully as a ZIP
with three entries. No private session payload was printed or sent elsewhere.

Friday concluded the native-only acceptance task at 13:13 local time, with
GOODBOWL left running as pwsh-1c7bb535e41c4d3d, health OK, MongoDB listening on
60265, and desktop viewport restored to 1440×900. No further demo purchase,
image generation or form submission was made during the follow-up. This
completes the scoped ChatGPT/native-browser acceptance, not universal provider,
file-format, long-context or unattended reliability certification.

## Remaining platform limits (latest)

Gemini, DeepSeek, and Kimi remain unvalidated live. Desktop control, unattended
reliability, full rich-content fidelity, and reliable autonomous planning have not
been established. Live file compatibility currently covers synthetic TXT, CSV,
and PNG examples, not every declared extension. Rendered mathematics becomes plain
visible text and can lose formatting. Streaming uses DOM snapshots, not native
token events. No token usage is fabricated. Google may block automated sign-in;
no restriction bypass was attempted. Signed-out ChatGPT worked without login.

No model API key or direct model API request is used by this adapter. Independent
bundled Harness account services can still make account/status requests.

## Structured activity and full report acceptance — 10 November 2026

Backend and installed Chrome extension: 0.6.3. Regression suite: 205 passed,
zero failures (output/friday-milestone-tests-2026-11-10.txt).

The real ChatGPT Chrome conversation completed the synthetic native Harness
workflow: one 15-second PowerShell command, browser navigation, accessibility
snapshot, name-field input, and screenshot. The command returned
FRIDAY_TOOL_START and FRIDAY_TOOL_RESULT=42. The screenshot visually confirms
Friday Live Test in Name, with other inputs unchanged and no form submission.

Live-discovered fixes included Markdown-safe introduction/context markers,
rejecting a misplaced tool prefix instead of reporting a false final answer,
enabling native browser image responses, and re-reading the response after
asynchronous download collection. The last fix is now verified live: ChatGPT's
complete final report and the persisted transport completion both contained
2,009 characters and the same content checksum (2164138095). Its final status
and all intermediate sections appeared in Friday, followed by the download.
The report-only verification executed no further tools: five completed tool
cards remained, with the original call identities retained.

The actual screenshot download initiated from Friday was 21,655 bytes. Its
SHA-256 matched the native screenshot preview and both website-returned copies.
The screenshot preview loaded at 1036 x 889. Refresh restored the complete
report, working download reference, preview and five completed tool cards.
Completed activity also survived the intervening backend restarts without
replaying the PowerShell command or browser actions.

Evidence: output/friday-milestone-live-2026-11-10.json and
output/friday-live-form-2026-11-10.png. Only synthetic test data is included.

Chrome tab control remained intermittent. The paired model ran in Chrome;
Friday UI checks used the embedded browser when Chrome tab control timed out.
After the extension update, the paired document needed a refresh to restore
its stale listener; the rejected readiness attempt submitted no prompt. The
embedded browser's download-event waiter timed out, but the actual file was
present in Downloads and verified by byte count and SHA-256. This scoped
acceptance is not a claim of universal browser or provider reliability.

## AG-UI adapter and aimock — 2026-11-10

Backend 0.7.0 adds the authenticated AG-UI 1.0 HTTP/SSE adapter using the
pinned official 1.0.4 schema, encoder and development HttpAgent client.
The existing Chrome extension remains 0.6.3. Harness remains responsible for
execution and permissions; no native controls or conversation store were replaced.

The complete Node suite passes 214 tests. Nine adapter tests include real
local aimock 1.47.0 HTTP fixtures, official SDK consumption, delayed native
tool results, full message snapshots, errors/EOF, disconnect/replay, restart,
fresh installation, multi-turn history/state, auth/input rejection,
cancellation, output limits and blocked/interrupted native outcomes.

The live owner-authenticated SDK request used the existing Chrome-paired
ChatGPT session and native pwsh tool. It returned 28 valid events, exactly
one tool result containing FRIDAY_AGUI_TOOL_OK_42, and a full 524-character
report with both requested boundary markers. A fresh SDK replay of the same
runId/input produced the identical report with no second execution. One
retained native screenshot preview returned authenticated HTTP 200 image/png.
The report was also visibly present after reloading Friday's interface.

Live evidence: output/friday-agui-live-2026-11-10.json and
output/friday-agui-live-events-2026-11-10.json. Test output:
output/friday-agui-tests-2026-11-10.txt. Acceptance input was synthetic;
credentials were kept in memory and are absent from these evidence files.

The first live admission found a fresh-journal ENOENT before any task was
admitted. The fix and a fresh-install SDK regression test are included.
After restart the saved native session needed reopening before SDK admission;
this precondition returns an explicit error without submitting work.
Chrome UI-control requests timed out; the actual model/extension transport
ran in Chrome, while visible Friday refresh checks used the embedded browser.
This verifies the supported adapter subset, not all optional AG-UI features
or universal reliability of third-party model websites. AG-UI client tools,
state writes and approval/resume injection remain deliberately unsupported.

## Native dock AG-UI streaming and recovery — 2026-11-10

Backend 0.7.1 connects the existing Friday task dock to the AG-UI GET stream.
Its browser observer retains the last complete SSE cursor during reconnect,
replays the latest saved run after refresh, and only aborts its own HTTP
observation when unmounted. It cannot submit work or cancel the native agent.
The existing saved-activity route remains available for pre-adapter sessions.
Full chat text and native attachments still use the existing Harness renderer.

All 219 tests pass. New coverage exercises split UTF-8/SSE frames, heartbeat
comments, interrupted stream recovery, duplicate events, exact tool/result
identity, screenshot state, observer cleanup, owner-authenticated module
loading, and an actual HTTP adapter run refreshed during execution with one
admission and zero cancellations.

Live acceptance used ChatGPT through the existing Chrome extension. The
first attempt coincided with a reconnect-notice generation and was rejected
before submission; no tool ran. After observing the paired ChatGPT editor idle,
a confirmed retry ran exactly one native pwsh command. Friday was refreshed
while the task was active, restored its running card, received both actual
output lines, and showed a completed tool card with exact arguments/results.
The complete final reply was 571 characters with both requested markers.
The saved AG-UI trace has 28 events, one tool call and one matching result.
The retained screenshot preview was still available in the expanded dock.

Evidence: output/friday-agui-ui-live-2026-11-10.json and
output/friday-agui-ui-tests-2026-11-10.txt. UI actions used the embedded
Friday tab; the paired ChatGPT page was also inspected successfully in Chrome.
This does not eliminate website busy states or other provider-side failures.
No extension update, permission change or replacement execution loop is needed.

## Native approvals and inline question records — 2026-11-10

Backend 0.7.2 retains the installed Harness approval and user-question action
cards. Friday adds read-only native chat definitions and AG-UI CUSTOM
friday.native-interaction records, correlated to approval audit IDs and tool
call IDs. No new grant/answer route, permission default, model-controlled
approval, or replacement pending-interaction registry was introduced.

All 224 Node tests pass. Interaction coverage verifies native audit identity,
matching outcomes, options/multi-select projection, timed pending versus
answered, late-reply mapping, cancellation/interruption display, conversation
node replay, and idempotent native question configuration. The final helper
regression also preserves explicit configurations separated by comments.

Four live synthetic tasks ran through ChatGPT in the existing Chrome
extension, with native Friday controls inspected in the embedded browser:
- A native question returned Blue, updating its read-only inline record and
  final ChatGPT report through the actual native tool result.
- Refresh initially exposed legacy question mode losing an unsent choice.
  Otherwise-unconfigured ask-user instances now use native mode timed with
  timeout -1. This preserves indefinite blocking and supplies native stable
  call IDs. Three installed instances were migrated with a profile backup;
  explicit settings and approval policies remain unchanged.
- The stable question test selected Green, refreshed while unanswered,
  retained Green under the same native call ID, and submitted successfully.
  ChatGPT returned FRIDAY_STABLE_QUESTION_RESULT Green.
- The native rejection card displayed the exact print-only command and wider
  access reason. Reject produced a real error result and a Rejected record.
  FRIDAY_REJECT_MUST_NOT_RUN was absent from tool output; no retry ran.
- The separate Allow once card survived refresh while pending. After the
  user's explicit per-action confirmation, the native button granted that
  single print-only command. Its one native result was exactly
  FRIDAY_NATIVE_ALLOWED_ONCE. ChatGPT returned the complete success report.
  Another refresh preserved the Allowed once chat record. The composer still
  showed Workspace Write; no standing permission default was changed.

Each of these four tasks has exactly one native tool call/result. Evidence:
output/friday-interactions-live-2026-11-10.json and
output/friday-interactions-tests-2026-11-10.txt. All evidence is synthetic test
data. Chrome tab control remained intermittent; actual model transport used
Chrome while native UI actions used the embedded Friday tab. Optional native
question timeouts, plan reviews and approval cancellation remain owned by
upstream Harness; they were not all separately exercised in this live check.
No extension update is needed.
