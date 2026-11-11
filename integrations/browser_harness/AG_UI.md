# Friday AG-UI adapter

Backend 0.9.2 exposes AG-UI 1.0 over HTTP/SSE using `@ag-ui/core` and
`@ag-ui/encoder` 1.0.4. Every event is schema validated. Harness retains its
agent loop, native tools, permission model, attachments, Compact, Goal, Plan,
history, cancellation and export. The prepared Chrome connector is 0.9.2.

## Interface

All routes use the existing native owner authentication and require
`X-Harness-Models: 1`. They do not accept the extension bridge token as owner
authentication. Keep credentials private and the server local.

| Route | Operation |
| --- | --- |
| POST `/browser-models/ag-ui` | Admit RunAgentInput, or replay the same runId/input, and stream SSE |
| GET `/browser-models/ag-ui/runs/:runId?threadId=...&after=...` | Observe persisted events without submitting work |
| GET `/browser-models/ag-ui/capabilities` | Inspect supported adapter capabilities |
| POST `/browser-models/ag-ui/cancel` | Explicit native cancellation with `{threadId, runId}` |

Use an existing, open browser-model session as threadId and UUIDs for runId
and the new user message id. The official `@ag-ui/client` 1.0.4 `HttpAgent`
works with this endpoint. Start with one new text user message and empty
tools, context, state and forwardedProps. A continuing client can echo its
exact saved AG-UI history and read-only state plus a new user message.
Client tools, replacement history, state writes, and AG-UI approval/resume
injection are rejected. Use native Harness controls for approvals and files.

The adapter emits run lifecycle, streaming text, authoritative message
snapshots, committed tool calls/arguments/results, steps, and read-only Friday
state with authenticated screenshot preview URLs. Message snapshots replace
temporary streamed drafts when the website changes its response. Reasoning
content is not exported. Existing native sessions retain their complete native
history; AG-UI observation starts when this adapter observes a run.

## Native human interactions

Friday uses the installed Harness approval and question composer cards for
all decisions and answers. Allow once, Reject, option selection, custom answers,
plan review, cancellation and one-shot settlement stay with native carriers.
There is no Friday approval/answer HTTP endpoint, automatic grant, AG-UI resume
grant, or model-authored permission decision.

Read-only native chat records show approval reasons/outcomes and question
options/answers beside the existing tool rows. AG-UI emits corresponding
`CUSTOM` events named `friday.native-interaction`, correlated to native audit
and tool-call IDs. The activity dock also retains these records. A question
timeout is labelled continued, not answered; an interrupted request is never
labelled approved. These records have no action buttons and are not proof of
current answerability; the live native card owns that state.

Setup configures otherwise-unconfigured native ask-user plugins to `mode:
timed, timeout: -1`. This uses the native stable call identity and persisted
drafts while continuing to wait indefinitely for an answer. Existing explicit
question configurations and all approval policies are preserved. A profile
backup is made before migration. Backend restart interrupts native work;
records do not resurrect approval grants or automatically replay tools.

## Recovery

The existing Friday task dock uses this stream for progress, exact tool
arguments/results and screenshot previews. It observes GET only: closing a
tab, changing sessions or refreshing never submits or cancels a task. A
temporary disconnect retains the displayed activity and reconnects at the
last complete SSE event. Refresh replays from zero to rebuild the latest run.
Pre-adapter sessions use their original saved activity. Native chat continues
to own the full conversation, files and tool transcript; no duplicate chat
renderer or task loop is introduced. The dock bounds tool previews and points
to the native transcript for longer output. Live progress is observational;
it does not invent completion percentages or approval decisions.

SSE ids are persistent journal cursors. `Last-Event-ID` or the GET `after`
cursor resumes delivery; clients resuming a suffix must retain their earlier
message state. A new client can replay from zero. Reposting the original
runId and identical message input reattaches without another native followup.
Changing that input or reusing its user message id under a new run is rejected.
Disconnecting the SSE observer does not cancel native execution.

A backend restart closes interrupted AG-UI runs with `HARNESS_RESTARTED`;
no native action is automatically repeated. Native errors, blocked/interrupted
turns and output limits are explicit errors rather than successful finishes.
Review native history before retrying uncertain work. Cancellation uses the
native agent cancel method and reports a cancelled outcome.

Limits: 8 SSE observers, 4,096 events or 8 MiB per run, and the latest 100 run
receipts per session. Exceeding the AG-UI budget closes the projection with
an error; native execution and native transcript remain available. Slow
observers disconnect after a 5-second blocked write. Journals are local;
automatic disk retention/rotation is not implemented.

## Verification

`npm run test:agui` uses the real official SDK and local
`@copilotkit/aimock` 1.47.0 HTTP fixtures. Coverage includes delayed tool
results, streamed draft replacement, provider errors, incomplete streams,
disconnect/replay, restart, fresh installation, multi-turn history/state,
authentication, input injection rejection, output limits, explicit cancellation,
and interrupted/blocked native outcomes. aimock and the SDK are development
dependencies; no hosted service or model API key is needed.

`live-agui-check.mjs` is a separate explicit acceptance runner for an existing
local session. It keeps current local owner credentials in memory, asks the
Chrome-paired model for one harmless native command, checks the full report,
and verifies replay and any retained screenshot preview. It never runs as
part of ordinary tests or server startup.
