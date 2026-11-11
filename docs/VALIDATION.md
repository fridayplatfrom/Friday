# Validation of the corrected baseline

Validation date: **2026-11-05**. These checks exercised the corrected working copy locally; GitHub Actions is configured separately in `.github/workflows/tests.yml`.

## Maintained regression gate

```text
python -m pytest -q
99 passed
```

The suite uses temporary source/index/memory stores. It includes:

- Whole-term routing, unsupported questions and neural registration failure.
- Actual arithmetic and unit conversion; division-by-zero and invalid physical inputs.
- Actual SymPy equation solving, calculus and matrix operations; code-like input rejection, bounded powers and timeout behavior.
- Missing weather, heuristic score labelling, crop-specific procedure filtering, scoped rule checks and factual execution logs.
- No random image prediction; text hints separated from image inference.
- Negated/healthy pathology input withheld even when a mock classifier supplies a high score.
- Upstream result/taxonomy handoff and session isolation/reset.
- Source metadata preservation; unknown shelf rejection; stale replacement/deletion/reload; no metadata-only search match.
- Live catalog refresh following HTTP ingestion.
- Local HTTP origin/host/size/JSON validation and absence of wildcard CORS.
- Native multi-head neural training/save/load, best-checkpoint restoration, train-only vocabulary, split leakage rejection, all-head metrics and zero-feature abstention.
- Incompatible/tampered model and vocabulary rejection; non-finite weights; trained router dimensions.
- Real BatchNorm running statistics, separate deterministic image validation transforms and identical-image leakage rejection.

The historical scripts under `tests/legacy` are excluded from this gate because many assert the behavior explicitly corrected here. No claim is made that those original assertions pass.

## Native training execution checks

| Model | Epochs | Train / validation / test | Parameters | Bundle status |
|---|---:|---:|---:|---|
| Pathology legacy fixture | 2 | 115 / 25 / 25 | 191,844 | experimental |
| Router through generic trainer | 1 | 50 / 10 / 10 | 73,873 | experimental |
| Leaf legacy fixture | 1 | 87 / 19 / 19 images | See saved manifest | experimental |

These are **training machinery checks, not evidence of clinical or field accuracy**. The leaf run used the original synthetic-heavy image fixtures only as an explicit demo. All resulting models remain outside the published source tree and are disabled in normal inference.

The newly trained leaf checkpoint was loaded by the actual `VisionExpert` runtime using explicit experimental opt-in. Architecture, preprocessing, ordered labels and checksum were compatible. An all-blank image did not pass the configured acceptance threshold.

## Representative corrected behavior

| Input / condition | Observed behavior |
|---|---|
| `12 + 8` | 20 |
| `12 / 0` | Explicit division-by-zero error; no fabricated 0 result |
| `mass=500 g acceleration=2` | 1 N |
| `r=100 c=1 f` | 100-second RC time constant; explicit farad unit respected |
| `solve x^2 - 4 = 0` | Roots -2 and 2, checked by substitution |
| `Research grammar.` | No unrelated marine/biology/toxicity fallback |
| `Explain CRISPR gene editing.` | CRISPR reference, not generic mutation template |
| Healthy/negated disease description | No accepted disease diagnosis or generated treatment |
| Unknown wild berries | Unknown safety, never default safe/non-toxic |
| Image without reviewed model bundle | Explicit model unavailable state |
| Reimport document with changed text | Old passages no longer retrieved, including after reload |

## Environment and additional checks

Native environment: Python 3.12, PyTorch 2.15.0+cpu, torchvision 0.29.2+cpu, NumPy 2.3.5, NetworkX 3.7, SymPy 1.14.0, pytest 9.2.0. Editable installation with `.[dev,documents]` succeeded.

All Python source files parsed, `git diff --check` passed, the browser JavaScript passed `node --check`, and the local demonstration script completed. A targeted credential-pattern scan found no matching credential/private-key patterns in the publication files; this is not an exhaustive secret-detection guarantee.

## What remains unverified

No independent scientific review of all legacy prose, external field benchmark, calibrated diagnostic probability, production-scale load test, multi-user security assessment, GPU training, or unrestricted book/grammar capability is claimed. See KNOWN_LIMITATIONS.md and ROADMAP.md for the next gates.
