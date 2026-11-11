# Persistent workspace browsing

Friday keeps the existing Harness `browser` MCP plugin, tools, images, permission
controls and provider-selector behavior. Model chats continue through the Chrome
extension. Task websites use the existing Chrome/Playwright engine with a separate
on-disk profile for each canonical native workspace directory.

Open **Workspace browser · saved login and tabs** below the conversation, then
**Open workspace browser**. Sign in to your websites in that window once. A new
conversation in the same workspace uses that profile; a different workspace has
its own profile. Personal Chrome profiles and existing model tabs are not imported
or cleared.

Profiles are under `%USERPROFILE%\.dsh\browser-connector\workspaces\<workspace-hash>\profile`.
Cookies and browser storage stay there. Do not commit, share, copy into prompts or
delete that directory if you want to keep your logins. Keep using the same Windows
account and workspace directory. Websites can expire sessions, request MFA, or
reject an automated browser; persistence does not bypass those restrictions.
Session-only cookies are still subject to the website/browser session policy.

## Restart behavior

The restart helper checkpoints open workspace browsers before stopping Harness.
Saved tabs reopen lazily when the workspace browser is opened or a native browser
tool runs. Up to two workspace browsers stay open; older ones close with their
profiles retained. Only explicitly allowed HTTP(S) origins are restored. Queries,
fragments and login/logout/OAuth/intent routes are omitted, so some pages may need
their filters or selections reapplied. Draft forms, passwords in editors and POST
requests are never restored or replayed. Normal Chrome model-tab restoration is
still controlled by Chrome and the existing connector pairing, not this manifest.

The existing explicit website-origin policy stays unchanged. Configure intended
task websites through Harness before using additional social-media sites.

## Interrupted publishing

Before a potentially mutating native browser tool dispatch, Friday fsyncs a receipt
containing the native call ID, workspace, session, tool and argument digest. It does
not put typed text or passwords in this journal. A duplicate call ID is refused.
If execution or result delivery is interrupted, subsequent browser writes stop.
Read-only snapshots/screenshots remain available for inspection.

After restart, an action that started, or completed without a committed successful
native tool result, is marked uncertain. Inspect the actual website. In the native
conversation's workspace-browser panel select **I checked: action happened** or
**I checked: action did not happen**. Only the authenticated Harness owner can
use these controls, and a revision check rejects stale decisions. Recording a
decision never reruns the action or changes native permission defaults. Refresh
browser status after inspecting the site.

This prevents automatic restart replay; it is not an exactly-once publishing API.
A newly requested post with a new ID, a manual click, shell/network tools, or a
website's own behavior can still create a duplicate. For real posting workflows,
inspect the destination and save its post URL/ID before deciding to submit again;
use site-provided idempotency where available. Never treat a lost reply as proof
that posting failed.

## Validation

`npm test` includes native tool-schema discovery, execution scope/queue tests,
workspace separation, browser lifecycle/tab restoration, owner-only recovery,
disk-write failures and crash-after-commit cases. Live acceptance uses the
fictional loopback page `http://127.0.0.1:8767/_profile-test`; it uses no real
account and cannot publish externally. The first live check retained its login
and tab through browser closure and a Harness restart, with the fictional post
counter remaining exactly one. It does not prove that any particular social
website will retain a session indefinitely.
