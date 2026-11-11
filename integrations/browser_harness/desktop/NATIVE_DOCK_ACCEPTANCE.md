# Native dock integration — 2026-11-11

The duplicate Electron provider toolbar, tab strip, splitter and screenshot-only
browser preview have been removed. Harness fills the desktop window and owns
the original dock, file previews, browser controls and layout.

Four icon-only shortcuts open provider tab kinds through the public native
sidebarRight API. Opening an existing provider focuses its tab. Close handlers
protect only those four kinds. Native provider-title close buttons are hidden;
the existing index.html file tab retains its close button. No upstream installed
Harness files or native layout storage keys were rewritten.

Provider WebContentsViews follow the native tab body bounds. Their isolated
profiles, connector worker, saved URL bindings and submission receipts are
preserved. Native session and geometry IPC are restricted to the local Harness
top frame, known providers, current session and in-window bounds. Refreshing
Harness hides stale provider overlays until the restored native body reports.

Validation: all 366 automated tests passed (zero failures); see
../../../output/friday-native-dock-regression.log. New tests cover reuse of native
tabs, provider-only close protection and rejection of invalid dock IPC geometry.

Live Computer Use checks:
- ChatGPT opened the saved Harness Ready Response chat inside a native dock tab.
- Gemini opened its saved signed-in website in that same dock.
- DeepSeek and Kimi opened their existing login pages as protected native tabs.
  Neither was signed in during this test.
- Switching to index.html restored the original live HTML document preview.
- A normal desktop close/relaunch restored all five native tabs, including the
  original file tab and four provider tabs. No test prompt, form or tool action
  was submitted or replayed during these UI checks.

This validates the dock integration, not a new complete provider/tool acceptance
run. Website login expiry and provider restrictions remain website-controlled.
