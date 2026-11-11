# Friday and native Harness API compatibility

Current candidate audit (2026-11-11): see [Production readiness](PRODUCTION_READINESS.md).
The version numbers and live-test notes below are historical inventory evidence;
they do not replace the current candidate's separate release gates.

Audited 2026-11-10 against the installed Harness core packages
**0.2.1-rc.5**. Friday package and installed extension **0.4.23**.
This is a compatibility inventory, not a claim of complete live coverage.

Live follow-up: native TXT upload and response return, actual PowerShell calls,
manual Compact, post-compaction recall, automatic pressure-triggered compaction,
and native Goal/To-do continuation now pass. See VALIDATION.md for evidence and
the live-discovered shared-turn image-progress fix. Live batch generation remains
unproven: an incomplete batch was safely rejected and recovered sequentially.
All 178 local tests pass after the live-discovered fixes; the store's 13 tests,
two persisted demo purchases, database restart and actual generated PNG download
have also passed through Friday. Fenced tool JSON now protects literal command
characters from website Markdown/maths rendering. Older pending notes below describe the
initial 0.4.20 audit; the live follow-up above supersedes those specific checks.

## Architecture and scope

The native Harness UI talks to its authenticated Typert gateway, session and
agent services. The agent assembles instructions, context, tools and results,
then calls the LLM adapter. Friday translates that model request to a paired
website conversation and translates its visible response back to native stream
chunks. Harness continues to validate and execute tool requests with its normal
permissions. Website text does not directly invoke gateway methods.

Consequently, native File, Goal, Plan, Compact, Permission, Model and Export
controls do not need duplicate connector controls. New tools supplied by an
enabled Harness plugin can travel through the same schema-based adapter without
a separate Friday endpoint for each tool. Availability still depends on the
selected native preset, plugin, permissions and working execution environment.

Two-way chat uses the existing native agent input/cancel path and exact paired
conversation checks. It does not provide a general-purpose unauthenticated
gateway into the computer.

## Installed remote service inventory

A read-only static scan of 305 installed package manifests found **84 Remote
method declarations in 25 service files**. This counts declarations, including
overrides, rather than unique live endpoints. The generated inventory records
every discovered method, stream/unary mode, source package and namespace
candidates:

- [Installed API inventory](../../output/playwright/friday-installed-api-inventory.json)
- Regenerate: `node integrations/browser_harness/audit-harness-api.mjs <app.asar> <output.json>`

The scanner reads the ASAR without executing installed application code. It
recognizes the installed compiled decorator format; alternate compilation,
runtime registrations, HTTP routes and disabled plugins are not a live endpoint
enumeration. File-scoped namespace candidates can belong to multiple services.
The native gateway's runtime Typert registry and access checks are authoritative.

| Native area | Discovered API operations | Friday integration |
| --- | --- | --- |
| Sessions | list/search/create, selectModel/modelCatalog, rename/fork, prompt/attachment, updateQueue/cancel, page/follow/projections/control, workspace-path operations | Native UI and persistence retained; model-facing history goes through adapter. Full live session-operation coverage remains pending. |
| Workspaces | pick/list/createDirectory/create/initializeDefault/rename/delete, ordering, archive/unarchive, pin/unpin, follow | Remain native; no copied workspace manager or bypass endpoint. |
| Files | native upload and session attachment; workspace file-change stream | Native admitted files/images are projected through attachment services. The generic-file capture fix still requires restart and a new live round trip. |
| Jobs | list/follow/kill | Native job lifecycle and execution retained. Tool results feed back through the conversation; job output is not reimplemented in Friday. |
| Terminals | retain/attach | Native terminal streams stay in Harness. Terminal tools can be requested through their supplied schemas. |
| Goals | get/edit/pause/resume/complete/clear/create | Native goal controls retained; representative goal/plan schemas have local bridge tests. |
| Presets and permissions | preset list/read/select; permission catalog | Native preset selection and permission decisions retained. Connector does not approve tool execution. |
| Model discovery | discoverModels and session model catalog/selection | Browser website routes exposed through native adapter metadata; website model labels are not exact backend model IDs. |
| Subagents | prompt/interruptByParent | Native delegation remains a Harness capability. Concurrent website conversations and complex delegated workloads need separate live validation. |
| User questions | attachWait | Native question flow retained; answers enter subsequent model context. Live approval/question scenarios remain pending. |
| Scheduling | list/catalog/history/delete/update | Remains a native service; scheduled execution still requires an available browser, account and connector. Unattended reliability is unproven. |
| References | session-reference candidates, session file references and skills | Native context/source metadata preserved in website requests. |
| Feedback and analytics | message feedback list/put/delete, command feedback record, analytics watchPolicy | Remain native; do not become website model capabilities. |
| Account and remote access | account watch/watchExpiry; remote-access follow | Native access/account services remain separate from Friday. Browser access does not supply paid Harness API credits. |
| Speech and office | experimental speech follow; office-to-PDF generation | Native optional services, not browser adapter modalities. No claim of native speech/video model support. |
| Host/plugin tools | plugin list; Cordis inventory/invoke, client/host execution, inspector and guard reports | Remain behind native plugin and gateway policy. No general Friday proxy for host execution. |

## Model adapter contract

The interface reviewed includes `providerInfo`, `providerRetryPolicy`,
`imageRequestPricing`, `imageRequestTarget`, `listModels`, `resolveModel`,
`prepareCall` and `stream`.

| Contract feature | Implementation and status |
| --- | --- |
| System instructions and message roles | Forward system, user, assistant, tool and developer messages. Preserve message IDs, toolCallId, error results and public source metadata, including context forms/sections. Opaque provider replay state is excluded. Tested for full, incremental and multipart paths. |
| Tools and tool history | Forward exact active schemas. Resolve deferred additions and removals from native history; reject requests for inactive tools. Advertise native `in-history` tool updates. Tested locally. Harness owns argument-schema validation and execution. |
| Multiple tool calls | Accept one call or a bounded array of up to eight independent calls. Validate the entire response's protocol, offered names and argument-object shape before emitting indexed native tool blocks with unique IDs. Dependent calls must wait for results. Native execution need not be simultaneous or atomic. Tested locally. |
| Streaming | Emit indexed block-start, text/tool deltas, authoritative block-end and finish. Visible DOM snapshots are the source; text rewrites settle through the final block. Do not claim API token event timing. |
| Cancellation | Pass AbortSignal through submissions and transfers; prepared-call cancellation settles as native aborted finish. Local stop matching closes the current request generator. Extension cancellation follows the existing active-job protocol. New stop handling has local tests; live website cancellation still needs checking. |
| Errors | Prepared calls emit native error/aborted finish with stable codes. Context-limit failures map to CONTEXT_WINDOW_EXCEEDED. Incomplete tool JSON may receive one existing format-correction request before execution; truncated stop-sequence output is never retried that way. |
| Retry policy | Disable automatic provider retries (`maxRetries: 0`) to avoid replaying uncertain website submissions. Existing explicit, bounded format correction remains; native compaction recovery is a separate Harness policy. |
| Request purpose | Include purpose in context and checkpoint identity. Native compaction gets no tools and cannot take the direct image shortcut. Local title generation avoids competing with the interactive chat. |
| maxTokens | Validate and forward as an advisory text budget. Native compaction can plan against it, but the website exposes no exact generated-token cap. |
| Stop sequences | Up to 16 validated strings. Buffer partial marker suffixes, exclude the earliest full marker and finish locally. This is exact visible-string matching, not a server-side API stop parameter. |
| Temperature and reasoning effort | Explicit requests fail before submission with a clear unsupported-control error. No reasoning efforts are advertised. Website mode selection cannot guarantee an API sampling parameter. |
| Native attachments | Restore only admitted file references and read immutable bytes through native services. ChatGPT supports the implemented upload path; other website routes do not advertise image input. Files are bounded to eight per submission and 32 MB each; website limits can be lower. |
| Generated media and downloads | Persist real received images/files and return previews/download links. Only observed progress is reported; a percentage is absent when unavailable. File transfer support does not imply the website understands every allowed format. |
| Context pressure | Native Compact policy uses a 32,768-token local planning budget, not a measured website context window. Bounded, acknowledged multipart transport handles oversized envelopes without emitting transfer acknowledgements as task answers. Both additions require live validation after restart. |
| Usage, pricing and reasoning | No fabricated token/cost/cache usage, hidden reasoning deltas or opaque replay state. Website quotas cannot be inferred as API balances. |

The reviewed GenerateOptions fields are provider, model, reasoningEffort,
messages, system, tools, toolHistory, temperature, maxTokens, stop, signal,
sessionId and purpose. This installed interface does not define generic
responseFormat or toolChoice options. Provider-specific API extensions are not
automatically available through a website.

## Validation and activation

**170 local tests pass**, including ten new compatibility/audit tests. The log is
[friday-api-compatibility-tests.log](../../output/playwright/friday-api-compatibility-tests.log).
Tests cover transport events and simulated website replies; they do not prove
all native UI operations or all model websites live.

Restart the existing Harness server with `restart_harness.cmd` to activate backend
0.4.20 and the preceding native-file/context fixes. This update does not change
extension scripts or require an extension reload. Refresh the existing Harness
tab afterward; retain the paired ChatGPT conversation.

Next live checks: native file round trip; automatic/manual compaction on the
previous long session; removed/deferred tool catalog changes; independent calls;
permission denial and tool-error feedback; cancellation during generation;
refresh/reconnect; and native export of the resulting conversation. Other model
websites and unattended tasks remain unvalidated. No website files were changed
by this API compatibility work.

## Primary references

- [Official LLM streaming and adapter contract](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/llm-streaming.md)
- [Official LLM package](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/llm/llm)
- Installed `@deepseek-ai/dsh-llm`, `dsh-api-gateway`, `dsh-api-session-controller`,
  `dsh-api-job-controller`, attachment, compaction and native client packages.
  Installed source controls this audit when upstream master differs.
