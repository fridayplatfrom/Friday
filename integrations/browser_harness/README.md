# Friday — browser connector for Harness

## Two concurrent browser requests (v0.10.0)

Chrome extension mode allows two active model requests across independent Friday
conversations, including two ChatGPT conversations or different providers.
Further requests wait in an in-memory queue with a visible position instead of
failing as busy. Each conversation has one active model request; changing models
within that conversation still uses the existing ordered handoff. Eligible queued
conversations are admitted in arrival order, skipping a conversation whose own
request is still running. The generation timeout starts after admission.

Cancellation removes only the owning request. Queued cancellations send no
website prompt. On restart, queued/interrupted work is shown for review and is
never automatically replayed. Status exposes `activeRequests`, `queuedRequests`,
`maxConcurrentRequests` and total `pending` (including queued work). Native tools,
permissions, approvals, goals, compaction and transcripts still belong to Harness.
Its existing workspace-browser execution lease remains in place. Concurrent model
requests do not make simultaneous edits to the same files logically conflict-free;
use separate task folders/workspaces for independent builds.

Tab ownership and event acknowledgments remain request-scoped. Generated Chrome
downloads from the same provider origin take turns before clicking Download,
because Chrome does not expose a reliable source-tab ID in download events.
Different-origin transfers remain independent. Old extension versions and the
single-page built-in/shared browser transports conservatively retain one slot.
Automatic development updates defer while any active or queued request exists.

v0.10.1 adds an owned, read-only page heartbeat: it resumes editor/stream waits
whose minimum delay has elapsed even if Chrome throttles the background page's
timers. It never clicks Send, reloads the page, approves a tool, or retries a
submission. Cancellation wakes and ends only the matching request's wait.

v0.10.2 also handles lost/rejected start-message acknowledgments without resending
the prompt and keeps failed durable setup out of the dispatch queue. An owned
terminal event or backend cancellation releases the worker even if the original
Chrome start-message port never resolves.

## Automatic saved-session recovery

Friday restores an existing saved browser-model conversation through Harness's
native `sessionController.inspect` and `resolveAgent` services. Opening its task
dock, submitting an owner-authenticated AG-UI request, or sending a new message
from its enabled paired ChatGPT chat can activate the saved native session.
The provider's existing tab manager reuses its saved chat URL on the next request.
There is no need to select a special acceptance conversation manually.

Recovery preserves the native model choice, workspace, preset and permission
controls. It does not submit a prompt, approve a tool, replay an interrupted task,
switch providers, or create a replacement native conversation. Unknown IDs,
subagent-owned sessions, non-Friday models and writer conflicts are rejected.
Simultaneous recoveries share one operation; duplicate inbound message receipts
remain authoritative after restoration. A website can still require sign-in or
verification. If the native owner cookie has expired, `open_friday.cmd` opens the
current legitimate owner sign-in link; authentication is not disabled.

## Switching models in the same task

Use Harness's existing model selector while the task is idle. The next native
request sends a handoff to the selected website without creating another Harness
conversation or changing its workspace, permissions, goals, tools or attachments.
Each provider retains its own saved chat URL and acknowledged context checkpoint.
Returning providers receive new native history; compaction or edited history sends
a fresh snapshot. The existing tab manager reuses/reopens the saved provider chat.
The task activity dock shows handoff status and saved-model-chat controls.

Handoffs include recent native execution receipts independently of model-generated
compaction summaries. Failed delivery never advances the target's checkpoint or
automatically retries tools. Resolve pending tool results before switching. Website
capacity/login failures can still block a model; choose another model manually.
Provider attachment/image capabilities remain unchanged and explicit. There is no
automatic fallback, concurrent turns within one conversation, new permission grant
or alternate tool loop. Independent-conversation concurrency is described above.

## Structured task activity

Backend 0.6.2 adds an owner-authenticated, cursor-based activity projection to
the existing conversation dock. It observes committed Harness turn/tool events
and Friday transport states; it never executes or approves tools. Expand the
status line for recent activity, tool arguments/results, and raster previews
received through native attachment references. Full tool results stay in the
native transcript; the activity view is a bounded preview.

Backend 0.9.2 also provides a schema-validated AG-UI 1.0 HTTP/SSE adapter,
tested using the official HttpAgent client and aimock. See [AG_UI.md](AG_UI.md)
for supported operations, authentication and recovery. The existing dock observes
AG-UI through an authenticated GET stream, resumes from its cursor after a
disconnect, and replays saved events after refresh. Sessions predating AG-UI
retain the original saved-activity display. Harness remains authoritative for history, Compact, Goal, Plan, files,
permissions, cancellation and export. Refresh reads saved activity; a backend
restart marks pending activity interrupted and never automatically replays it.

Native approval and question cards remain the only decision/answer controls.
Friday adds durable read-only approval/question records to chat and AG-UI,
including rejection, one-time grants, pending questions and actual answers.
Otherwise-unconfigured ask-user plugins use Harness's stable-call mode with
an indefinite wait, so native question drafts survive refresh. Explicit native
question settings and permission policies are preserved.

Native browser screenshot image responses must be enabled (`--image-responses
allow`). The installed browser tool returns a native image when its screenshot
request omits `filename`; explicit filenames can return only a saved-file link.
The activity projection reads admitted image references only, not arbitrary
URLs or local paths embedded in model text.

Connector 0.6.1 adds unique submission markers to introduction/context turns.
Backend 0.6.2 rejects tool-request prefixes preceded by prose instead of silently
completing the turn. It permits the existing single format-correction attempt
only before any text/action has been emitted.

Connector/backend 0.6.3 rechecks the exact response turn after collecting
downloads. If the visible response changed during transfer, it sends the newer
snapshot and waits for it to settle before committing completion. Downloads are
collected once per request to avoid repeating the same transfer during that wait.

The Friday web profile disables the built-in DeepSeek account/API model entries,
account Settings screen, official whale/wordmark and official session-log upload
UI/backend. DeepSeek is available again as an experimental website backup;
this does not restore the built-in DeepSeek account or API integration. The
browser models are ChatGPT, DeepSeek, Gemini and Kimi. Sidebar branding, welcome logo, page title,
favicon and product descriptions in Settings use Friday. Native package IDs,
upstream license files, owner authentication and saved conversations are retained.
Run `configure_friday_brand.ps1` to apply the backed-up, CLI-validated profile
switches on an existing installation.

Verified on 10 November 2026 with backend and extension 0.5.3: native model
selection contains only the Friday group with ChatGPT, Gemini and Kimi; Settings
has no Account section, DeepSeek provider rows or official-model session-log
upload preference. The page title is Friday and the whale is replaced. Chrome
heartbeat is connected with zero pending requests. All 198 tests pass; proof is
saved in output/playwright/friday-browser-only-models.jpg and
output/playwright/friday-settings-no-deepseek.jpg. This check covers branding,
configuration and existing regressions, not a new end-to-end model task.

The active installation uses the normal Chrome extension. The shared-browser
prototype is inactive following the Google sign-in rejection and signed-out
submission mismatch. It is not a validated replacement for the extension.

The welcome screen uses the supplied Friday logo through Harness's hero-brand
slot. Native model labels show only the provider icon and short name. Two-way
ChatGPT relay enables automatically after the paired conversation acknowledges
its introduction; moving to a different conversation still requires a fresh
acknowledgement. The composer shows active progress and file warnings without
duplicating native errors, chat URLs or connection toggles. Diagnostics remain
available in native Settings → Models.

Verified 10 November 2026 on backend 0.5.1: extension heartbeat connected,
no pending requests, welcome logo visible with the old headline/badge removed,
and four short icon/name entries visible in the native model picker. All 198
local tests pass, including pairing-introduction gating for automatic two-way
relay. This UI update did not rerun a complete ChatGPT tool/file/image task;
the shared-browser signed-out failure remains recorded as an experiment, not
an extension regression. Proof: output/playwright/friday-logo-model-picker.jpg.

A Harness provider with text, ChatGPT attachment transfers and generated-image output. Model API keys
and the Tiny Expert backend are not used. Website limits and service rules apply.

## Setup on Windows

1. Install Harness and Chrome, then run `npm install` in this directory.
2. Run `powershell -File integrations/browser_harness/setup.ps1` from the repo.
   The default reuses the Chrome Friday connector. On a fresh installation,
   load the printed extension folder once; existing installations retain it.
3. Start `integrations/browser_harness/start_harness.cmd` and open the local URL
   printed by Harness.
4. In **Settings → Models → Friday**, enable the desired existing Chrome
   connection. Sending a task pairs its website conversation automatically.
   **Show paired chat** opens that conversation for review. Enabled status means
   the connector is reporting in, not that a model reply has been verified.
   Sign in on the website only when it requires it.
5. Choose that website in the Harness chat model picker.

Connection controls use the native Models extension slot, Harness buttons and
colors, and its authenticated owner session. There is no separate Connections
page. The local pairing token is never sent to the Models UI.

Setup backs up the web profile and preserves unrelated entries. Tiny Expert
replacement profiles must be removed before setup. Other profiles are unchanged.
`-WithBrowserTools` adds the local MCP browser test tools and fictitious demo form.
The older `-BrowserMode builtin` model-website prototype remains an explicit
opt-in; it is not used by this installation. Task browser automation uses the
existing Harness browser MCP tools in either transport mode. For an existing
browser installation, use `configure_browser.ps1` to adjust origins while
preserving its current backend configuration.

## Normal Chrome extension (current web profile)

The installed web profile uses `browserMode: extension`, with your existing Chrome
sign-in. Reload **Friday** in Chrome Extensions after updating
its files. Refresh already open paired website tabs to load changed content scripts;
new tabs load them automatically. Refresh Harness after backend/client updates.

- Each Harness session/provider keeps its own tab and latest conversation URL.
  Follow-ups, errors, long chats and extension worker restarts reuse that tab.
  A different session gets another tab. Closing a tab reopens its saved URL on the
  next request. Navigating it to another website produces a recovery message.
- The native composer shows **Show paired chat**, which focuses that existing tab,
  and **Copy URL**. Sending requests does not repeatedly steal focus from Harness.
- Before the first ChatGPT coding/task request, Harness sends a separate introduction
  explaining the extension bridge, one-tool-at-a-time JSON protocol, real tool-result
  feedback, and requested/completed/verified/failed outcomes. It waits for the exact
  `HARNESS_READY` acknowledgement before submitting the actual task. Acknowledgement
  confirms the text protocol, not verified computer access. It persists across
  backend restarts and is renewed when a different conversation URL is reported.
  Image-only prompts skip initialization; the next coding request still initializes.
- Drafts in paired tabs are replaced before submission, as requested. Unrelated
  browser tabs are never adopted or overwritten.
- ChatGPT image requests beginning with create/generate/draw/make (including polite
  forms such as "Can you please create a dog image") send only the actual human
  prompt. Harness system instructions, tools, history and runtime snapshots are
  omitted. Image descriptions retain all user-provided detail. This route does
  not execute Harness tools; normal coding requests retain the agent protocol.
- Visible ChatGPT image progress appears in the composer with a progress bar and
  history of observed percentages. Missing percentages remain indeterminate;
  completion never fabricates 100%. A DOM observer captures visible updates.
- If the current reply says "This response couldn’t load", Harness shows
  **Response couldn’t load — waiting to load** and keeps observing that same reply.
  This waiting time does not consume the normal response timeout. When the reply
  loads, streaming resumes. The connector does not regenerate, resubmit the prompt,
  or repeat tools. Cancel remains available. This requires extension v0.2.2;
  refresh existing paired website tabs after reloading the updated extension.
- Generated PNG/JPEG/WebP images transfer in bounded chunks and appear in the native
  reply and preview gallery with Download links. Local session metadata and images
  persist under `.dsh/browser-connector/sessions`. Images require Harness owner
  authentication. Limits: eight images per request, 16 MB per image.

The optional built-in worker does not support attachment transfers or image
generation. Website generation failures remain visible as website replies;
transport failures do not become successful empty responses.

## Two-way ChatGPT chat (extension v0.3.0)

1. Send a short request from Harness to initialize the updated protocol and tool catalog.
2. Click **Enable two-way chat** in that Harness conversation's paired-website area.
3. Open its existing paired ChatGPT tab and wait for the **Friday · Two-way chat** panel.
4. Every new text message you submit there is also admitted into the same Harness
   agent. The connector captures ChatGPT's existing reply without posting your prompt
   again. Valid tool requests use Harness's normal validation and permissions; tool
   results return to the same ChatGPT conversation for the next step.

The panel shows Harness status and has **Stop Harness**. A new submitted message
interrupts the preceding turn before being admitted. Untrusted/programmatic send
events are ignored, preventing Harness's own tool-feedback prompts from echoing as
new human requests. Message receipts prevent duplicate admission, including after
backend restarts; uncertain submission outcomes require review rather than replay.
Reply capture stays within the matching native ChatGPT turn, so a later reply cannot
be mistaken for an earlier task. Incomplete tool prefixes or malformed JSON trigger
one format-correction request before anything is executed. A second malformed reply
stops with an error; completed operations are never replayed by this correction.
The correction includes the exact connector error and confirms that nothing ran
from the rejected reply. ChatGPT can correct the call or choose another available
tool or approach for the same task.

Two-way mode applies to the explicitly enabled paired conversation. Navigating to a
different conversation disables it until that conversation is initialized again.
The paired Harness agent must be loaded; the panel explains when to reopen its
Harness conversation. Refreshing/reloading the website during an active capture
can interrupt that capture; a missing capture fails without resubmitting the prompt.
Attachment handling is described in the v0.4.0 section below. Voice chat submission
is not supported; audio files may be transferred as attachments.
Website-origin tasks require the ChatGPT browser route; the model stream guard rejects
an API route before dispatch. This remains DOM-based integration, not native MCP
registration in the ChatGPT website, and website outages can still interrupt work.

### Refresh and offline recovery (extension v0.3.1)

Saved native Harness conversations and the connector's pairing metadata remain on
disk. Tool activity can be collapsed under **Completed → Wrote files** after reload.
An independent page health guard reports an unavailable backend even if the native
UI's reconnect lifecycle fails. After a backend restart it reloads a blank crashed
view; an open editor instead gets a **Reconnect Harness** button without draft loss.

The paired ChatGPT panel shows **Harness is offline — waiting to reconnect** when
polling fails, and automatically receives fresh status when the backend returns.
A missing content-script heartbeat also marks the connection lost after 15 seconds.
For enabled two-way chats, the extension posts one offline notice to ChatGPT when
its editor is empty and idle, then one restored notice when connectivity returns.
It never overwrites a draft or interrupts generation for a notice. These notices
do not create Harness tasks. No earlier tool operation is replayed on reconnect.
An interrupted active task may still require explicit review and continuation.

Version 0.3.2 also detects newly submitted user bubbles after ChatGPT interactive
buttons, which may bypass the composer Send event. Harness's own outbound prompts
are explicitly suppressed. Initial/older virtualized history is never replayed as
new work; a previously missed request needs a new explicit continuation request.
Version 0.3.3 restores the connection panel if ChatGPT's page hydration removes it
during reload.
Version 0.3.4 also requests connection status from the page every few seconds, so
missed background pushes do not leave it showing an old connection state.

## Reliability and attachments (v0.4.0)

This release adds the transport and recovery implementation. Its new website upload,
download and screenshot paths have automated coverage but still require a live
compatibility check with your signed-in ChatGPT page. A supported file extension
means the connector can move its bytes, not that every website model can analyse it.

### File workflows

Use Harness's existing File, Goal, Plan, Compact, Permission, Model and Export
controls. The connector supplies the model transport and website pairing/status;
it does not replace Harness's agent loop, approval system or session commands.
Goals and plans use the tools supplied by Harness; compaction summaries use the
same model adapter. Native export remains owned by Harness. The connector has
no separate uploader, capture button, attachment manager or export button.
Restart Harness after this backend update to activate native generic-file reads;
no Chrome extension reload is needed for this change.

- In the existing Harness conversation, use its native **Add files or run commands**
  control, paste, or supported drag-and-drop. The original bytes are resolved through
  Harness's durable attachment service, and the next message uploads them
  to the paired ChatGPT file input before submitting the prompt. The connector waits
  for visible filename chips and for processing to finish. Failure leaves a clear
  error; files remain in the local attachment store.
- Native Harness image and file blocks, including tool screenshots and documents,
  use the same attachment service. The connector has no separate file picker or
  screenshot-capture button. A workspace file reference stays a normal Harness
  reference and can be read with its supplied tools; an actual attachment transfers
  its bytes, not a fictitious filename-only upload.
- Files selected, pasted or dropped directly into the paired ChatGPT page are
  transferred to local storage while two-way mode is enabled. The subsequent human
  request in Harness includes file identities and readable local paths. Files are
  not automatically executed, extracted or written over workspace files.
- Visible website-provided download links with supported filenames are retrieved
  when the corresponding assistant reply completes. Saved results appear as native
  reply download links. Inaccessible/cross-origin downloads
  and unrecognized filenames produce a persistent manual-download notice. The
  connector does not guess private file endpoints or scrape unrelated conversations.
- Raster previews are supported for PNG, JPEG and WebP; other files download as
  attachments. HTML and SVG are never served as executable previews.

Supported transfer extensions:

| Group | Extensions |
| --- | --- |
| Images/screenshots | png, jpg, jpeg, webp |
| Text/data | txt, md, csv, json, yaml, yml, xml |
| Documents | pdf, docx, xlsx, pptx |
| Source/assets | html, css, js, mjs, ts, tsx, jsx, py, svg |
| Archives | zip |
| Audio/video files | mp3, wav, m4a, mp4, webm |

Limits: eight files per outbound request, 32 MB per file, 100 saved files and 256 MB
of original file bytes per session. Website limits may be smaller. Transfers are
split into 384 KB chunks, indexed and verified by SHA-256. Native references retain
their identity across refresh/restart; delivered files are not uploaded again merely
because they remain in conversation history. Source files stay in
your control; the connector never silently substitutes a filename for missing bytes.

### Durable delivery and recovery

`sessions/files` stores file metadata, chunks and verified readable copies. The
append-only `sessions/delivery.jsonl` records full request context, submission,
reply snapshots, final results, failures and event acknowledgements. This is local
connector debugging data, not a replacement conversation export interface. Use
Harness's native export controls for conversations. The journal contains task
content and should be shared deliberately.

Duplicate chunk/event acknowledgements are idempotent, including after restart.
Confirmed native turn identities are saved in the paired page's session storage.
When an extension worker loses its job, the bridge offers the same job for capture
recovery. The page watches the saved response without resending the prompt. An
unconfirmed submission stops for review. Backend restart marks active tasks
interrupted; it does not replay potentially completed tool operations.

Successful request checkpoints allow continuation prompts containing only newly
appended messages. A changed tool catalog or rewritten history triggers a full
snapshot. When necessary, older assistant/tool payloads use marked excerpts; every
human instruction and tool-call/result identity is retained. Original context is
in the journal. If that single-message envelope still exceeds 80,000 characters,
Friday transfers the full original request JSON in bounded context-only parts.
Each part requires an exact transfer-specific acknowledgement. Only after all
parts acknowledge does Friday send the task-commit message and accept a tool call
for Harness to validate. Part acknowledgements never become assistant answers or
authorize local tools. Cancellation or a bad acknowledgement stops before commit
and does not advance the checkpoint. The next confirmed continuation returns to
the normal incremental path.

This transport fallback preserves native Harness controls and requires no separate
UI. Very large transfers are bounded to one million source characters and 32 parts;
beyond that, use Harness's native **Compact** command or a fresh session with a
handoff. Long-term model recall still depends on the website's context window;
acknowledgement confirms the transfer protocol, not perfect model understanding.
Restart Harness to activate backend updates; no extension reload is needed.

### Native Compact and automatic compaction

Use **+ → Compact** or submit `/compact` without arguments while the Harness
agent is idle. This runs Harness's own compaction engine: it creates a structured
checkpoint for earlier conversation and continues from that summary. The native
session log records the operation. A pending task must finish or stop first.

Friday v0.4.19 uses a 32,768-token local planning budget. This is scheduling
metadata, not an authoritative statement about the website's hidden capacity.
`configure_compaction.ps1` configures the existing native compactor for the
`browser-web/chatgpt-web` route in Standard, PTC, Minimal and Cordis presets, with
automatic compaction, 4,096 tokens of headroom, a 0.6 threshold ratio, 2,048 retained
tokens and a 2,048-token summary budget. With the normal 4,096-token response
reservation, native compaction starts around 19,660 estimated tokens. Website
token usage is not invented or reported as known.

The previous native 65,536-token default headroom did not fit Friday's former
16,000-token advertised budget. The helper validates the composed Harness profile,
preserves every existing preset plugin and saves a private backup. It refuses
to overwrite an existing custom compaction configuration. A profile validation
failure restores the original. Rerun the helper after updating native preset
definitions to refresh the preserved preset snapshot. Restart Harness to apply.

Native compaction is the history-management mechanism; context-part transfer is
only a fallback when a normal or summarization request cannot fit one message.

Settings, paired tabs, native tool execution and native permission checks remain
owned by Harness. General file transfers currently target ChatGPT via the extension;
other providers and the optional built-in worker use explicit manual fallback.

## Optional built-in mode

Connection preferences persist in `.dsh/browser-connector/preferences.json`.
The built-in worker owns a separate persistent Chrome profile and reuses one
chat tab. It starts a new conversation in that tab when the Harness session
changes, after six requests, or after 160,000 submitted characters. These limits
bound growth; they are not actual RAM measurements. Existing unsent drafts are
preserved. Login cookies are not copied from your regular browser profile.

Visible response snapshots become incremental Harness text deltas. Hidden
reasoning, authoritative token usage, and native token-level streaming are not
available. Tool replies are validated and passed to Harness's existing tool
execution and permission flow. The existing bounded independent-call batches remain
supported. Browser requests use the concurrency rules above. Cancelling generation
does not undo completed tool actions.

Google may reject sign-in from the managed browser. This integration does not
bypass that restriction. Use another sign-in method offered by the provider, or
signed-out chat when available. A visible editor is required for Connect; its
presence alone does not guarantee that the website will accept a message.

## Limitations and verification

Website selectors are experimental and can change. Signed-out ChatGPT now returns
replies into Harness, including incremental text during longer answers. The earlier
extension transport also completed a PowerShell tool feedback loop. Other providers
remain unvalidated live. Rendered mathematics can lose formatting during visible
text extraction. Live voice chat, simultaneous requests, and automatic
model selection are not supported. Website model names do not guarantee a
particular model version. Other providers' image output has not been validated.

Run `node --test integrations/browser_harness/tests/*.test.mjs`.
See [validation notes](VALIDATION.md) for observed results.

The bridge binds to loopback and authenticates local clients. Native Models
routes require Harness owner authentication and its same-origin Settings header.
No cookie extraction, private model inference APIs, CAPTCHA solver, or security bypass is
included.

## Local development updates

`restart_harness.cmd` restarts only the verified local web-profile server on port
3030, and refuses to stop it while a website request is active. It preserves chat
and connector storage. Use it after changing backend provider code.

For unpacked local development, `setup.ps1 -BrowserMode extension -AutoReloadDevelopment`
enables automatic detection of installed manifest version changes. Bootstrap the
updater with one Chrome extension reload. Subsequent local version changes use
Chrome's [runtime reload](https://developer.chrome.com/docs/extensions/reference/api/runtime#method-reload)
while the bridge is idle. No new extension permission is requested. Paired tabs
reported idle and draft-free are refreshed in place; draft or unavailable tabs
are preserved for manual refresh, and active website generation defers updating.
The option is off for installations that do not explicitly enable it.

Button-only generated downloads can optionally use Chrome's Downloads permission,
enabled explicitly in the connector popup. That Chrome permission can expose
download metadata; this implementation listens only while a paired job requests
a file, queries only newly created candidate IDs, and imports completed supported
files from the configured Downloads directory (by default the current user's
Downloads folder). The bridge rejects old files, foreign origins, paths outside
that root, unsupported formats and oversized files. No file is opened, executed
or extracted. Without the permission, readable download links still transfer and
button-only failures show a manual-download warning.

## Local application image jobs

Local backends can use the existing browser image transport without a model API
key. The bridge must be restarted after installing this backend addition.
All routes require the existing pairing Bearer token, a loopback Host, and no
website Origin. Read the token server-side from the connection file; never put
it in frontend code or return it in application responses.

- `POST /image-jobs` with `{ "prompt": "A watercolor dog portrait" }` returns
  HTTP 202 with `{ "id": "...", "status": "queued" }`.
- `GET /image-jobs/:id` returns status, message, observed percent or null, and
  generated image identities. Status is queued, running, complete, or error.
- `GET /image-jobs/:id/images/:imageId` returns only that job's saved raster.

One dedicated paired browser conversation is reused for this studio. An active
Harness task causes HTTP 409 rather than stealing its browser slot. Prompts are
bounded to 1500 characters; at most 20 new requests per hour are accepted. The
newest 100 receipts persist locally. Interrupted jobs become explicit errors on
restart and are never replayed. Website limits still apply; successful text with
no transferable image is reported as an error. No local tools are exposed by
these image routes. Applications must provide their own user validation, request
limits, same-origin checks and authorization before invoking the bridge.

## Native Harness API compatibility

The task browser is the existing Harness `browser` MCP plugin. Its former
demo-only origin setting is fixed by `configure_browser.ps1`, which backs up and
validates the existing profile without replacing its browser executable, mode,
plugins or permissions. Defaults include GOODBOWL, the local demo form, its image
host and font hosts. Additional explicitly intended websites can be supplied
with `-Origins`; inputs must be complete HTTP(S) origins, without paths,
credentials, queries or wildcards. `setup.ps1 -BrowserAllowedOrigins` uses the
same validation. Restart Harness after changing the native browser policy.

The native Models panel reports the Chrome connector's heartbeat and enabled
providers separately from successful model replies. Enable/disable controls use
the already installed extension and refuse changes during an active website
request. They do not launch a second task browser. Connection diagnostics and
version reporting stay in the existing UI. Other model websites are explicitly
experimental until separately validated.

The local audit retains full disk history while bounding recent in-memory
payloads and event receipts. Startup streams saved UTF-8 records, preserves
crash tails byte-for-byte, and maintains sequence identity across restarts.
Local metrics describe transport attempts and observed durations, not exact
tokens, billing or complete-task success. See [ACCEPTANCE_MATRIX.md](ACCEPTANCE_MATRIX.md)
for the requested improvement list and the distinction between local and live
test coverage.

See [API_COMPATIBILITY.md](API_COMPATIBILITY.md) for the installed API inventory,
native feature ownership, tested adapter support and browser limitations.
Backend v0.4.20 adds tool-history filtering, independent tool-call batches,
native error finishes, explicit request controls and local stop sequences.
It requires a Harness restart; extension scripts are unchanged.

Backend v0.4.22 makes a native continuation wait for an already accepted image
studio job to release the shared browser connection. Cancellation stops only the
waiting continuation, and shutdown cannot dispatch a replacement request. Other
overlapping native tasks reported busy in v0.4.21. This historical restriction is
superseded by the v0.10.0 scheduler above; the dedicated image studio still retains
its existing admission rules.

## Rollback procedure

Stop Harness, restore the desired `.dsh/browser-connector/cordis-before-browser-*.yml`
backup to `.dsh/profiles/web/cordis.patch.yml`, then restart. If the optional older
extension is installed, it can be disabled separately. Existing chats are retained.
