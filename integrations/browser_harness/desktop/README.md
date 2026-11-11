# Friday desktop prototype

This is an experimental Electron host for the existing Friday/Harness UI and
ChatGPT website. It reuses extension/background.js, content.js, transfers.js,
two-way.js, the native tool loop, permission cards, files and AG-UI backend.
It does not use a model API or import Chrome cookies.

## Start

Start the existing Harness server with ../start_harness.cmd. Install this
folder's dependencies with `npm ci` (Electron 45.3.0), then double-click
start_friday_desktop.cmd. The desktop window claims the existing authenticated
bridge only when no request is active. Chrome extension polling parks while the
desktop owns dispatch. Closing the desktop releases ownership back to Chrome.
The icon-only shortcuts in the native conversation header open protected tabs
in Harness's existing dock. There is no second browser/tab strip or screenshot
preview panel. File previews, browser tabs, splits and resizing use the original
Harness controls and saved layout. Clicking an icon again focuses its existing
tab for this conversation. Provider tabs cannot be closed; select a different tab
to hide them. Connection/activity details are behind the header information icon.
Each provider has
its own persistent Electron session. ChatGPT keeps the original
persist:friday-chatgpt session, so this UI upgrade does not migrate or clear its
saved login. Existing Chrome logins are not imported into the desktop profile.
Provider navigation is distinct from choosing the model for a native task.

The navigation sidebar starts collapsed. The native dock owns workspace sizing
and tab persistence; existing saved layouts are preserved.

Provider tabs reuse the conversation's existing connector pairing and saved URL.
Native provider kinds are registered through sidebarRightTabs and rendered inside
the existing dock. The Electron provider view follows its tab body's bounds and
visibility. Selecting a file or browser tab hides that view without destroying
its login or listener. Close handlers protect only provider kinds. Ordinary tabs
retain their original controls. The native composer's model selector still
controls the task model; opening a provider tab does not switch the task model.
Native permissions, uncertain-action review and browser tool dispatch remain
owned by Harness.

Provider pages run behind the opaque native workspace with background throttling
disabled. Starting a task or reconnecting does not raise a provider or the app.
On startup even a restored provider tab stays concealed until the user clicks
its icon, title, Show button or Show paired chat. Selecting another native tab
covers the provider again without suspending its renderer. Send uses the same
visible DOM control as the extension, after a durable main-process admission;
it does not require a foreground mouse click. There is no second-click fallback.

## Persistence and boundaries

- The independent Electron profile is under ~/.dsh/friday-desktop/profile.
  The persist:friday-chatgpt partition retains cookies and website storage.
  Session expiry, logout, provider policy and Google embedded-login restrictions
  can still require sign-in. No promise of permanent login is made.
- Tabs, local connector settings and durable submission receipts are under
  ~/.dsh/friday-desktop/state.json. This file contains chat metadata and message
  capture data; keep it private. Do not commit or upload the profile.
- Receipt writes are synchronous and atomic before the existing content adapter
  clicks Send. On an uncertain submitted/submitting receipt the adapter refuses
  replay. Recovery reads the verified existing turn. A blocked/uncertain request
  is surfaced for review rather than executing an action again.
- Downloads use unique directories below ~/Downloads/FridayDesktop. Only
  completed, newly observed, paired-task downloads enter the existing file
  importer. Interrupted downloads are not automatically clicked again.
- Remote content has Node disabled, sandbox and context isolation enabled, and
  no main-world IPC bridge. The local preload limits message types and the main
  process verifies sender, top frame, provider origin and job ownership.
- Navigation is restricted to ChatGPT and listed authentication origins.
  Certificate/security errors are not overridden. Google login is never spoofed.
- Profile cookies are flushed on normal close. A crash keeps desktop ownership
  until the same desktop client reconnects or the bridge restarts; there is no
  automatic takeover that might repeat uncertain work.

## Acceptance gates

Automated checks cover exclusive dispatch, refusal of active-job takeover,
owner reconnect, durable/scoped receipts, navigation/IPC restrictions, and the
existing connector regression suite. Live gates must be recorded separately:
embedded sign-in, restart preserving account/chat, partial stream -> page
refresh -> full reply, a single acceptance-bearing submission, native tool
round trip without duplicate execution, and one generated download imported
with exact bytes. Passing unit tests does not establish those live gates.

This is a runnable prototype, not a signed installer or production release.
