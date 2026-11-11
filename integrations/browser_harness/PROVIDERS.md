# Provider contracts and recovery

Friday 0.9.2 uses extension/provider-catalog.js as the declarative contract
for website names, URLs, capabilities, selectors and adapter revisions.
Backend model discovery, extension tab ownership, page selectors, popup
provider choices and native Models diagnostics share that contract. Setup
generates a matching standalone selector snapshot for content.js, so a stale
manifest that omits the new catalog preload does not break the page listener.
The optional legacy built-in browser worker remains a separate experimental
transport; this milestone targets the existing Chrome extension.

Fresh installations enable all catalog providers; saved disabled choices remain
disabled. Enabling a provider does not log in, open its page, send conversation
history or grant additional Chrome permissions until the corresponding action.
ChatGPT retains text, native image/file transfer and two-way support. DeepSeek
is an experimental backup for text and the Harness tool protocol.
Its file/image transfers and two-way chat are unverified and not advertised.
Unsupported native attachments fail explicitly before submission. Gemini and
Kimi also expose text and the tool protocol, with separate user-turn correlation,
sign-in and completion detection. Website names identify the
provider chat, not a guaranteed underlying model version or unlimited usage.

DeepSeek verifies the unique outgoing marker against its visible user message
and correlates responses by message order. It does not depend on ChatGPT turn
attributes. Completion requires visible completion controls or an observed
generation transition. A mismatched or uncertain submission never resends.
Existing tool-request validation and native permission controls still apply.

DeepSeek's observed Copy/Download code toolbar is excluded only when extracting
one literal native DOM code block with the required tool prefix. Unknown prose
or extra blocks remain invalid. Its unlabeled enabled generation control keeps
the stream open even if reply text is temporarily stable.

Gemini reads user-query text without its duplicated accessibility heading and
waits for the response markdown's explicit idle marker. Kimi uses the international
www.kimi.ai/en entry point, retaining known Kimi.com URL compatibility. Its
answer renderer excludes the separate reasoning panel, its Send container's
disabled/loading classes participate in readiness, and only the observed Copy
toolbar is removed from a single literal tool-code block. Existing chats keep
their original allowed origin and exact conversation URL. Foreign hosts, HTTP,
credentials and alternate ports are rejected.

Harness tools are an external visible-text protocol, rather than functions
installed in the provider website. Complete and incremental prompts explain
this distinction. The revised context fingerprint resends a complete snapshot
on the next new request; it does not replay an earlier action. Native Harness
continues to own validation, permission decisions and actual execution results.

## Existing chats and new chats

Submitting in an existing Friday conversation automatically uses its saved
provider conversation URL. An open matching chat is reused. A closed chat
reopens at the saved URL; a browser-restored tab with a different ID is matched
by the exact conversation URL instead of creating another tab. ChatGPT and
DeepSeek have verified conversation URL patterns for this lookup. A new Friday
conversation always gets a fresh provider chat; unrelated home pages are never
adopted. If the last Chrome window closed but its extension is still running,
the existing Chrome profile can open a normal window at the saved chat.

The native backend supplies its saved conversation URL even if extension
pairing metadata was cleared. Established conversation URLs stay pinned when
someone navigates a tab to another chat; the unrelated chat is left intact.
Different Friday sessions cannot take over each other's owned tabs. There is
also an explicit Pair active Chrome tab recovery action for a selected session
when its pairing is wrong or missing. It validates the provider origin and
rejects tabs owned by another Friday conversation. Login is retained by the
browser profile; an expired website session can still require manual sign-in.

## Diagnostics and recovery

Settings → Models offers Check health. A global check finds a live managed
tab, skipping closed conversations. Session-specific health and refresh
actions target the exact session/provider pair. Health distinguishes missing
tabs, missing page listeners, probe timeouts, busy generation, editor readiness
and unchecked adapters. It reports bounded operational facts, never page text,
prompts, URLs with secrets, filenames, passwords or cookies. Ready means an
editor was observed; it does not mean a task or tool executed successfully.

Transport failures save the latest 20 recovery records in the native-linked
session metadata. The existing activity dock exposes the last diagnostic:
category, submission certainty and next action. Confirmed submission overrides
an error claiming nothing was sent. Unknown outcomes require checking the
paired chat and native results. No retry or provider switch is automatic.

Refresh paired tab is explicit, restricted to the selected conversation, and
refuses an active website job. The extension also preserves a generating page,
an unsent draft, an unresponsive document or a tab navigated elsewhere. A
missing tab can be reopened through the existing paired-chat focus action;
the saved conversation URL remains authoritative. This never resubmits a task.

After an extension update, an invalidated two-way listener stops polling and
asks for a page refresh instead of throwing synchronously on every heartbeat.
Different saved conversations may have similar website titles; use Friday's
actual paired URL when refreshing a particular task.

The opt-in local development updater automatically refreshes idle paired tabs
after loading an update. It resolves restored Chrome tab IDs by the exact saved
conversation URL. Closed tabs stay closed and load current scripts when reopened.
A draft, active generation or unresponsive listener defers the whole update;
it does not invalidate a working page listener or send the request again.
Version discovery uses authenticated loopback status, which reads the installed
manifest afresh. Fetching Chrome extension resources cannot reliably discover
changed local code because Chrome can keep the registered resource bytes cached.
Setup copies the manifest last so an update is offered only after its scripts
and local configuration are ready. Older installations need one bootstrap reload
to load this corrected updater; a normal website refresh cannot replace cached
extension code by itself.
This updates locally installed code only, without new permissions, remote code
downloads or AI-generated patches. Manual browser/extension shutdowns and a page
that never answers its health probe can still require user attention.

To use the backup, enable DeepSeek in native Settings → Models, select its
icon/name in the native model picker and submit a new request. Review any
uncertain original work first. A fresh session avoids sharing unrelated
conversation history with the backup. This milestone does not implement AI
patch generation, unattended code installation, automatic cross-provider
history transfer, or parallel agents.
