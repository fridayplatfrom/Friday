# Hidden-provider execution — 2026-11-11

Friday keeps provider renderers behind the opaque native workspace rather than
suspending their views. Restored tabs are concealed until the user explicitly
selects a provider icon/title or Show button. Automatic acquisition and readiness
recovery do not reveal the provider or raise the app window.

Changes include focus-independent DOM Send after durable admission, no mouse or
second-click fallback, preserved job ownership/origin checks, runtime background
throttling configuration after page load, and the supported renderer-background
priority switch. Profile partitions, native dock controls, permissions, saved
chats and submission ledgers remain in place.

The first live test sent the introduction successfully, but its response could
not be correlated. A fallback now assigns stable logical turn keys when ChatGPT
provides separate user/assistant articles without native grouping. Native keys
are preserved, adjacent assistant messages share the verified preceding user key,
and duplicate human text retains distinct message identities. No uncertain Send
is retried by this fallback.

Live verification through native UI:
- Test B: ChatGPT stayed concealed throughout. The complete marker and integers
  1–40 returned to Friday; native completion took 25 seconds.
- Test C: Friday was minimized while the request ran. One get_goal tool call and
  its matching result were recorded, followed by the complete final marker and
  `No goal exists (goal: null)` in Friday. Native completion took 39 seconds.
- Restoring the app did not reveal ChatGPT automatically. Manual Show remains
  available for sign-in, inspection and account/verification requirements.
- Manual Show revealed the correct saved provider chat; collapsing the native
  dock concealed it again. A final close/relaunch retained the same session and
  saved URLs, with no new Send admission (friday-background-restart-check.json).
- Typing without opening the provider went to the native Friday composer. The
  temporary focus probe was removed without submission.

376 automated tests passed, including hidden rendering/z-order, explicit reveal
scope, durable single admission, rejection without fallback clicks, ordinary
provider acquisition, stable turn grouping and existing connector regressions.
Evidence: ../../../output/friday-background-regression.log and
../../../output/friday-background-live.json.

Relevant Electron references:
- https://www.electronjs.org/docs/latest/api/web-contents (mouse input requires
  a focused host window; background throttling controls)
- https://releases.electronjs.org/pr/55442 (runtime background-throttling call
  keeps an already-covered page drawing)

Website sign-in, usage limits, network outages and verification remain external
conditions; background execution does not bypass them.
