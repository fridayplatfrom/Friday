# Friday page-listener recovery candidate

Date: 2026-11-11. Candidate 0.10.3. Status: automated checks passed;
activation confirmed; live page-refresh recovery failed and remains unresolved.

The v0.10.2 ChatGPT page-refresh probe reproduced a lost-listener gap. The
website accepted one synthetic text-only request before the page was refreshed.
Friday retained partial text but its worker waited for the destroyed listener.
The isolated native run was stopped for review; no tool ran and no prompt was
resubmitted. Run: 787fd4eb-037b-44af-8fc0-bc3c67176a3d. Evidence:
../../output/friday-page-refresh-initial-failure.json.

Implemented:

- An owned worker pulse can detect a fresh ChatGPT page with a persisted
  submitted-turn receipt and reattach capture using resume=true. This path is
  restricted to an existing exact saved conversation URL and ordinary outbound
  tasks. It never opens a tab, clicks Send, fills an editor or uploads files.
- The page verifies the original user request in the current DOM, including the
  unique transport prefix for agent requests, before reading the response. It
  resolves a remounted turn key from that verified request. A mismatch, different
  conversation, ambiguity or unconfirmed submission stops without replay.
- Collected image identities and download completion stay in the receipt.
  Completed downloads are not clicked again. An interrupted download is skipped
  with an explicit warning; an uncertain image transfer requires review.
- Existing native permissions, tool ownership, two concurrent model slots,
  queues, native attachments and external function-call decoding are retained.
  Image-purpose and inbound two-way tasks are not automatically recovered by the
  new worker path; their existing handling remains in place.

Validation: all 352 tests passed (production-hardening-0103.log), including worker
ownership/resume guards, content mismatch refusal, uncertain receipts, no repeated
downloads, and the previous provider/parallel/file/permission regression tests.
Installed background/content/manifest hashes match the source. The backend was
restarted on 0.10.3 with no pending task. Last observed Chrome extension version
was still 0.10.2; no claim of a passing 0.10.3 live refresh test has been made.

The browser-control session disconnected during diagnosis; the replacement
Chrome session can list its tab, but page commands are timing out. The user was
asked to activate the installed extension and refresh the paired test page so
live acceptance can continue. Saved accounts and permission defaults were not
changed. General network outages and browser crashes remain separate gates.

## Activation confirmed; browser-control blocker

Both backend and Chrome extension now report 0.10.3. The first post-activation
probe failed a Chrome tab lookup before submitting anything (run
870a4b3c-fd4a-453d-8c22-9697c4e1ea9a). A subsequent targeted readiness probe
responded ready, and an independent text task completed normally (run
a1db9061-3a5d-4e45-87e2-98e95970a2b9): 26,891 reply characters committed,
one browser request, one submission, zero tools, final pending zero.

Codex's browser-control transport returned Debugger unattached for the attempted
live refresh. Reclaiming the same saved tab did not restore that operation. A
manual-refresh request was issued, then explicitly withdrawn when the response
finished before a refresh was confirmed. There was no post-text reconnect event;
the ordinary successful response is not counted as a page-reload acceptance.
Evidence: ../../output/friday-page-refresh-103-control-blocked.json.

The live verifier tasks/page-refresh-audit.mjs requires a real reconnect after
text begins, a complete bounded reply, one request/submission and correct native
history. It will reject this non-refreshed run. Current live refresh-recovery
status remains unverified; extension activation is complete and no further
extension reload is required for the installed candidate.

## Actual refresh exercised: incomplete reply

Run cab0e45e-27da-4535-accf-57333c315a07 exercised an actual tab-scoped
Page.reload after native text began. First text arrived at 07:03:30.693 UTC;
reload completed at 07:03:47.008; Friday recorded reconnecting at
07:03:51.540. The response then stopped advancing and the request timed out
at 07:07:43.323. Only 5,972 partial characters were recorded, with no
committed final report and no tool execution. This is a failed completeness
gate, not a passing recovery test. The acceptance-bearing task had one
submission; auxiliary native compaction requests are separate requests.

Evidence: ../../output/friday-page-refresh-103-before.json,
../../output/friday-page-refresh-103-executed.json, and
../../output/friday-orbit-chatgpt-web-cab0e45e-27da-4535-accf-57333c315a07.json.

Browser diagnosis restored control on a fresh local demo tab, while saved
ChatGPT tabs continued reporting an unattached debugger. A newly opened
copy of the saved ChatGPT URL initially exposed its loading UI, then timed
out on both DOM reads and screenshot capture. Reclaiming existing tabs did
not resolve it. No browser-wide restart, login reset or uncertain prompt
replay was performed. The isolated clean-session attempt separately reported
an account-changed refresh requirement. The renderer/control failure's cause
is not established; successful automated receipt tests do not prove live
reply recovery.

## Follow-up after user refresh

The user confirmed Chrome is responsive and the requested chat was refreshed.
A new owner-authenticated health probe still reported listener-missing for the
saved recovery session, with the bridge connected and zero pending requests.
No new task was submitted. Browser control timed out claiming the saved tab.
The native fallback returned Chrome accessibility content, but its screenshot
showed the Codex application instead; an accessibility click also failed because
coordinate geometry was unavailable. Input was stopped because target identity
could not be trusted. This is evidence of a control-surface mismatch, not proof
that Chrome itself is frozen or that Friday's recovery code has passed.
