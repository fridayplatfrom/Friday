# Friday workspace layout acceptance — 2026-11-11

Historical record: this separate-shell layout was superseded by
NATIVE_DOCK_ACCEPTANCE.md at the user's request. Its preview and splitter have
been removed from the desktop runtime.

Implemented and activated in the desktop prototype. Final state: native sidebar
collapsed, conversation visible at 30%, Browser selected in the larger right
workspace. The application is left open.

366 automated tests passed with zero failures. Evidence:
../../../output/friday-workspace-layout-regression.log and
../../../output/friday-workspace-layout-audit.json.

Live checks performed through Computer Use:

- Friday opened with a collapsed navigation sidebar. The divider started at
  30%; dragging changed it to 37%, which survived desktop restart. Reset restored
  the requested 30/70 arrangement. Conversation collapse/restore was exercised.
- Provider toolbar buttons opened Gemini, DeepSeek and Kimi views. Repeated
  switching retained one view per newly opened provider. Four pre-existing
  ChatGPT views were preserved, for seven total views. This is navigation
  acceptance, not authenticated model/tool acceptance for the other providers.
- ChatGPT reopened the existing saved conversation and exposed its signed-in
  profile controls after restart. Its original persistent partition was retained.
- Looking at Gemini left the native task model set to ChatGPT. Connection
  details opened and returned to the website; they distinguish listener readiness
  from verified account sign-in.
- Browser listed the two existing saved task-browser tabs. Opening that browser
  restored them in its original profile. A live preview of its local form page
  appeared inside Friday. Selecting and focusing the second tab preserved both
  live page IDs and the total tab count of two; activeIndex became 1.
- The preview-fit test exposed an offscreen focus button. It was moved to the
  header and the image constrained to the available panel. Both browser-window
  actions are visible in the final screenshot.
- Old previews are cleared on native workspace changes and late responses from
  a different workspace are discarded. Regression tests cover this behaviour.

Browser remains a read-only preview of the existing task-browser process. Open
selected tab provides direct interaction in that same browser window; this
release does not embed a second copy of its pages or move its cookies. Native
browser tool scoping, approvals and uncertain-action receipts are unchanged.
One pre-existing browser action still requires outcome review; it was not
acknowledged, replayed or cleared by this UI work. No test prompt or form was
submitted during this layout validation. Final website pending count: zero.

Final screenshot: ../../../output/friday-workspace-layout-final.jpg.
