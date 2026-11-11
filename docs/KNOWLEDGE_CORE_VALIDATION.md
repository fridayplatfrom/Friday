# Knowledge Core validation — implementation v0.1

## Scope and source identity

Base repository: `fridayplatfrom/tiny-expert-system` at
`44fc6528aa0dbf7470314a2b4951bdff2f5917b3`.
Implementation branch: `feature/knowledge-core-v1`.

The new core and its acceptance tests were executed from an additive local working
copy. Published Git blob hashes were compared with local source bytes. This was
not a fresh full checkout/run of every historical application regression test.

## Observed acceptance result

```text
python -m pytest -q tests/regression/test_knowledge_core.py
80 passed in 16.19s
```

Environment: Python 3.13.5, pytest 9.0.2, Pillow 12.3.0, SQLite 3.46.1, Linux.
System FFmpeg was available. The existing `expertos_bridge` Python package was
loaded from the previously supplied plugin ZIP solely as an integration-test
dependency; it is not copied into this implementation.

All new Python modules and the test module also passed `compileall`.

Coverage includes:

- Stable concept IDs, aliases, rename conflicts, polyhierarchy and cycle rejection.
- Ambiguous word senses, contextual translation proposals and observed vocabulary.
- Original/extracted hashes, exact Unicode offsets, repeated imports, restarts,
  multiple subject links, shared editions, changed revisions and corrupted assets.
- Source permissions, derivative ancestry, tenant isolation and concurrent writes.
- Reviewed immutable training releases, source/case/hash/derivation leakage,
  held-out partition separation and classification/QA/pretraining exports.
- Model/evaluation records, explicit promotion gates, source-impact propagation,
  runtime availability, one-use approvals, bounded workflows and leased jobs.
- Static HTML extraction, products versus offers, image regions, timed transcript
  alignment, and real FFmpeg extraction of two frames from a synthetic clip.
- Authenticated HTTP directory/source calls, host/origin/token/JSON rejection,
  and actual installed browser-rule routing, form mapping and readback validation.
- Backup/restore, unknown-schema refusal, withdrawal, shared-asset-aware purge,
  and removal of structured source-derived payloads and segment notes.

The model-governance tests deliberately use synthetic artifact bytes and reported
fixture metrics. They do not train a neural model or establish its accuracy.

## End-to-end demonstration

The local CLI demonstration imported a synthetic thermodynamics document, linked
it to physics and thermodynamics, retrieved its exact passage, checked the source
hash/offset, and dispatched a registered deterministic calculator. Inputs 600 K
and 300 K produced an ideal reversible efficiency of 0.5. The language directory
returned an ambiguous result for biological versus spreadsheet `cell`.

This is an execution/integrity test, not an authenticated textbook experiment.

## Legacy collection migration exercise

A separate test migrated source files from the original uploaded ZIP plus the
expanded standalone 97-entry atlas. It observed:

- 12 bibliographic records, seven websites and six imported dictionary concepts.
- 42 lexical senses and 36 proposed translation alignments.
- 32 source-note documents and eight other catalog/feed record files.
- 73 additional atlas entries preserved as declarations or supporting entities.
- A second migration produced no duplicate records; zero capabilities were
  executable without an explicit runtime binding.

This fixture is not the complete current `main` checkout. In particular its book
catalog differs from the pinned repository catalog. Metadata and scientific
claims were not independently verified, and training rights were not granted.

## Not established by these tests

- Full historical application regression success on the new exact GitHub commit.
- Windows installation or actual DeepSeek Harness runtime compatibility.
- Successful live external-source downloads or real website automation.
- Learned translation, speech recognition, semantic retrieval or new neural accuracy.
- Correctness of every source, inferred relationship, review or permission claim.
- Production security, distributed operation or large-corpus throughput.

The separate CI workflow runs this core suite on Python 3.11/3.12/3.13 when hosted
runners are available. Optional FFmpeg/plugin tests skip if those dependencies
are absent. Prior hosted-run failures must not be counted as passing tests.
