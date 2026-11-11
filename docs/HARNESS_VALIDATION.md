# Native Harness physics and streaming check

Local checks performed November 7–8, 2026, on Windows, using the repository's
Python environment and the installed DeepSeek Harness web profile.

## Reproduced and corrected

| Input | Expected behavior | Finding and correction |
|---|---|---|
| Mass 2 kg, kinetic energy 100 J; find speed | 10 m/s, positive square-root branch | The value was correct but the displayed formula used the negative branch. Formula and numerical branch now agree. |
| Mass 500 g, acceleration 2 m/s² | 1 N | Passed unit conversion and calculation. |
| Voltage 12 V, resistance 6 ohm | 2 A | Passed calculation. |
| Carnot hot 600 K, cold 300 K | 0.5 = 50% | Passed calculation. |
| Mass 2 kg, velocity 0 m/s | 0 J | Harness previously displayed `None J`; zero is now preserved. |
| Carnot hot 300 K, cold 600 K | Reject inconsistent reservoir roles | The solver previously sorted and swapped temperatures. Explicit labels are now preserved and rejected. |
| `solve 2+8` | 10 | Added bounded arithmetic dispatch instead of falling through to generic physics. |

The speed, zero-energy, invalid-reservoir, and arithmetic cases were exercised
in the actual browser UI. The six physics cases were additionally checked
through the live backend SSE endpoint, reconstructing the answer from deltas
and requiring a finish event. Details and measured timings are in the local
ignored `state/harness-validation/results.json` file. These are small execution
checks, not an independent scientific benchmark.

## Transport

The provider now forwards backend SSE events instead of waiting for complete
JSON and replaying chunks with timers. A flushed status event precedes
computation. The local execution report and formatted answer follow completion;
this does not provide intermediate symbolic-engine progress or generative
token inference. Tests cover split UTF-8/CRLF frames, truncation, errors,
cancellation and forwarding an event before the body finishes. Prompt bodies
are no longer appended to the provider's hardcoded debug file.

## Automated results

- Initial focused HTTP/physics regression run: 15 passed.
- Full suite during overlapping startup/test activity: 343 passed, 8 failed
  from symbolic-worker timeouts, plus 5 subtests passed.
- Subsequent complete reasoning-tool and new Harness regression groups:
  60 passed. This includes the eight cases that timed out in the full run.
- Final arithmetic presentation regression: 1 passed.
- Node streaming transport tests: 4 passed; provider syntax checks passed.

The full suite was not rerun after the targeted timeout retry. There remains
one FastAPI/Starlette dependency deprecation warning in the broad suite.

## Remaining limitations

Retrieval still selects some exercise fragments and unrelated excerpts. Source
hashes establish integrity, not answer support. Generic subdomain convention
notes and limited concept templates also need better task-specific selection.
Experimental reader fragments are withheld by default; explicit research
opt-in remains available. Rule overrides no longer fabricate neural scores,
and unrelated default oscillator/wave derivations are withheld. Cancellation
closes transport but does not interrupt a calculation already in progress.
