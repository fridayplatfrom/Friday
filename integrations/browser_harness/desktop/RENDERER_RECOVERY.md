# Blank-window recovery — 2026-11-11

Observed: Friday's main process and bridge remained alive, but the native Harness
and ChatGPT accessibility documents were blank. Other provider documents were
still present. The only old stderr diagnostic was a disposed-render-frame
warning; there was no recorded renderer exit reason or OS crash report. The
original root cause cannot be established from that evidence.

The active request was reconnecting. It had no desktop submission receipt or
native Send admission. It later ended through the existing website timeout; no
task was resubmitted or cleared by this repair. After pending requests reached
zero, Friday was closed normally and reopened. The native conversation, five
native tabs, saved ChatGPT URL, and login were restored.

Changes:
- Record renderer exit reasons/codes, child-process failures, native runtime and
  preload failures to the bounded local renderer-health.jsonl log.
- Automatically restore a crashed renderer at most twice per minute per view.
  Restore only the same validated local interface or saved provider page.
- Clear stale provider overlays while the native interface recovers.
- Show a Restore interface fallback if recovery fails instead of a blank window.
- A crashed provider's assigned request gets an explicit error, with outcome
  review required; recovery itself never dispatches a prompt or tool operation.
- Preserve all existing profile partitions, chat URL bindings and durable Send
  receipts. The existing submission ledger continues refusing duplicate input.

Validation: 368 automated tests pass, including recovery retry limits, validated
restore targets, protected dock tabs and durable duplicate-send refusal.
See ../../../output/friday-renderer-recovery-regression.log.
This incident was recovered by restart; an actual renderer crash was not
deliberately induced during live verification.
