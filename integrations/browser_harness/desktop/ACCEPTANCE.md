# Desktop prototype acceptance — 2026-11-11

Status: built and launched; authenticated live acceptance remains incomplete.

The native Friday UI and embedded ChatGPT were observed together in the Electron
window. Native workspace, model and permission controls were visible. A native
conversation was created through that UI. Reopening the app restored both saved
provider tab IDs (1 and 2) and the durable receipt of the uncertain first test.
The Electron profile is independent of Chrome and was still signed out. No
claim of a saved authenticated login surviving restart is made.

358 automated tests passed, zero failed:
../../../output/friday-desktop-regression-final.log. These include the existing
provider, native tool-loop, queue, file-transfer, approval and recovery suite,
plus desktop ownership, durable receipts, native submit admission and isolation
policies. They are not substitutes for live provider/tool acceptance.

The initial signed-out smoke test filled the initialization prompt but could
not verify website submission. It failed without automatic replay. An
Electron-specific one-attempt input adapter was then added, with a durable
admission ledger and no fallback click after uncertainty. It leaves the normal
Chrome extension click path unchanged. The subsequent live run
19e14210-db8e-4538-b874-140b691fb8c1 encountered the visible website error
"Chat stopped unexpectedly" and again failed submission verification. The
desktop ledger contains one input attempt for initialization job
9985f63c-7549-4c0a-a572-1dc012f18bb5; no tool call or result was recorded.
The actual task did not progress past initialization. This does not establish
whether the provider failure depends on sign-in or embedded-browser support.

Evidence:

- ../../../output/friday-desktop-prototype.jpg
- ../../../output/friday-orbit-chatgpt-web-19e14210-db8e-4538-b874-140b691fb8c1.json
- ../../../output/friday-desktop-live-ready.log

Final bridge status: desktop transport connected, pending requests zero. The
Chrome connector is parked while desktop owns dispatch. Closing the idle app
normally releases it. A sign-in request is pending with the user; no credential
entry, cookie import, security-warning override, Retry click, or tool execution
was performed. Startup sequencing and unavailable-backend handling were fixed
while testing; the final application was observed open afterward.

Remaining live gates: authenticated sign-in; account/chat retained after normal
restart; full streaming reply; reload during streaming followed by complete
same-turn capture; generated download with byte verification; native tool round
trip with one execution; cancellation and backend-restart recovery. None of
these uncompleted gates should be reported as passed.
