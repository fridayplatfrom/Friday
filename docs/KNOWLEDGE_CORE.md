# ExpertOS Knowledge Core — implemented local foundation

This is an additive, opt-in implementation of the Knowledge Core blueprint.
It is not a production security certification, a new set of trained neural
experts, a full-web search engine, or proof that source claims are true.

## Architecture and actual implementation

`tiny_experts.knowledge_core.KnowledgeCore` joins eight logical directories over
one transactional SQLite database and a content-addressed, tenant-scoped local
asset store. Stable IDs never depend on a renamed browse path. General associations
are distinct from hierarchical and execution dependencies.

| Directory | Implemented behavior |
|---|---|
| Concepts | 163 seed concepts, polyhierarchy, typed relationships, cycle checks, multilingual labels, aliases, optimistic rename conflicts. The seed is illustrative, not a complete ontology. |
| Language | Observed terms with source locations; distinct lexical entries/senses; ambiguous lookup; proposed sense/segment/edition alignments. No automatic dictionary truth or translation engine. |
| Sources | Work → edition → artifact → immutable revision → segments. Many concepts share one original. Full originals and extracted text have separate hashes. Incremental FTS5 indexing, source-scoped search, stale-revision rejection. |
| Evidence | Text offsets/quotes, image regions, timed audio/video selectors, structured tables/equations/code records, claims and review records. Byte integrity never means semantic entailment. |
| Capabilities | Existing 24 core expert aliases, registry discovery, explicit callable bindings, actual current-process availability, model integrity and permission gates. Declared/planned does not mean loaded. |
| Training/models | Reviewed immutable dataset manifests, source-family/case/hash/derivation split gates, partitioned JSONL and original-text exports, observed training runs, artifact checksums, evaluation and explicit promotion records. No upload triggers training. |
| Entities/websites | People/organizations/software/general entities, websites and pages, static page snapshots, separate products/merchants/time-bounded offers. No arbitrary crawling or automatic product identity claims. |
| Governance/workflows | Separate store/retrieve/train/redistribute permissions, tenant filtering, local curator decisions, audit trail, source invalidation, content purge, backup, bounded DAG execution, one-use action approvals and leased jobs. |

## Install and commands

Use the repository's supported Python environment. Core metadata/text operations
use the standard library. Images require Pillow; the optional frame worker needs
FFmpeg. Existing PDF/DOCX/EPUB importers and neural experts retain their own
optional dependencies. No external LLM is called by this package.

```bash
python -m tiny_experts.knowledge_core --root ./state/knowledge init
python -m tiny_experts.knowledge_core --root ./state/knowledge status
python -m tiny_experts.knowledge_core --root ./state/knowledge migrate .
python -m tiny_experts.knowledge_core --root ./state/knowledge coverage
python -m tiny_experts.knowledge_core --root ./state/knowledge dashboard --output ./knowledge-map.html
```

`migrate` reads existing files without rewriting them. It preserves unreviewed
catalogue metadata, the existing expert atlas, dictionary translations as
proposals, website records, actual note files, and other legacy catalog/feed
records. A referenced book or video is not reported acquired. Rule modules do
not become neural models. Repeated imports are idempotent. Malformed inputs fail
and roll back the database transaction; original files stay unchanged.

```bash
python -m tiny_experts.knowledge_core --root ./state/knowledge import-file ./thermo.txt \
  --title "Actual source title" --source-key "my-local-source" \
  --concept concept.thermodynamics --concept concept.physics \
  --license-note "Record actual permissions and source"
python -m tiny_experts.knowledge_core --root ./state/knowledge search "heat engine" --concept concept.thermodynamics
python -m tiny_experts.knowledge_core --root ./state/knowledge evidence SEGMENT_ID --quote "exact source words"
```

Training and redistribution rights default to false. `--allow-training` records
operator-supplied permission; it does not verify that permission or approve the
source/labels. `--curator` is a **trusted local operator context**, not public-web
authentication. Never let a model or request body choose it or choose a tenant.

## Compatibility with existing experts

The old `TinyExpertOrchestrator.process()` is deliberately not silently rewritten.
The new facade is registry-driven and explicit about operation/scope:

```python
from tiny_experts.knowledge_core import KnowledgeCore, CoreExpertSystem

with KnowledgeCore("./state/knowledge", actor="operator", curator=True) as core:
    system = CoreExpertSystem.from_repository(core, ".", load_legacy=True)
    result = system.process(
        "hot=600 K cold=300 K", concept_ids=["concept.thermodynamics"],
        capability_id="expert.thermodynamics", permissions=("local_compute",),
    )
```

The adapter replaces the legacy instance's book engines and librarian/catalogue
view with core-backed retrieval; closes the displaced book index; and binds the
installed `evaluate` functions. Vision without a loaded leaf model stays unbound.
The old experts' internal limitations and unreviewed reference text remain;
this change does not certify their scientific accuracy. Some legacy support
components retain their bounded local logic; migration preserves their records,
not an invented complete rewrite of every domain algorithm.

A newly declared capability cannot execute. An operator may register an installed
implementation with `mark_implemented`, then explicitly `bind` its callable.
The binding is local to the running process and is not recovered from an old
"ready" flag after restart. Python import paths in catalog metadata are never
executed dynamically by the core.

## DeepSeek Harness integration

An in-process `HarnessCoreAdapter` exposes directory, evidence, lookup and search
operations. The authenticated loopback bridge also preserves the existing
plugin's `/health`, `/v1/experts` and `/v1/source/read` routes:

```bash
# Set a long random token through your shell/secret manager; do not commit it.
python -m tiny_experts.knowledge_core.bridge --root ./state/knowledge --port 8765
```

Set the same `EXPERTOS_BRIDGE_TOKEN` used by the existing plugin. To install the
optional existing Python browser rule package, follow PR #4's setup instructions.
After installing it, add `--enable-browser-rules` to the bridge command. This
explicitly registers and binds five deterministic specialists. Their route,
plan, map, verify and recover calls go through the shared capability registry.
No browser executor, terminal, form submission, neural policy or LLM is enabled
by this flag. `/v1/action/propose` remains unavailable until a separately validated
policy adapter is installed.

New HTTP endpoints `/v1/core/directory`, `/v1/core/search`, `/v1/core/lookup` and
`/v1/core/evidence` use the same bearer token and fixed server context. The old
Node transport does not yet expose these extra paths in its allowlist; its
existing expert/source calls work without that extension. Actual DeepSeek
application installation is a separate integration test, not completed here.

The bridge rejects foreign origins/hosts, invalid framing, duplicate JSON keys,
NaN, caller-supplied tenant/permissions, excessive inputs, and unauthenticated
requests. It exposes no review, training, purge, approval or arbitrary execution
endpoint. It is not a hardened internet-facing or large-concurrency server.

## Source revisions, withdrawal and deletion

One new revision supersedes the previous artifact revision. Old passages disappear
from ordinary search. Derived sources, claims, annotations, datasets, evaluations,
models and deployments are marked affected through explicit lineage links.

- `set_rights(revision, rights, reason=...)` reevaluates dependent releases.
- `withdraw_source(revision, reason=...)` removes it from usable knowledge.
- `purge_source(revision, reason=...)` additionally removes unshared original and
  derived source bytes and sensitive derived payloads from this store.
- IDs and hashes remain for accountability. Exported copies and external backups
  cannot be recalled by this API. Affected model weights are not magically unlearned.
- `backup_to(destination)` uses SQLite backup and copies immutable assets under a
  writer lock. It requires an empty destination outside the core and refuses a
  tenant-scoped backup of a shared multitenant database. Test restoring before
  relying on a backup for an operational migration.

Original legacy files are untouched. Rollback of an opt-in deployment means stop
using the new facade/bridge and restore a tested core snapshot; no destructive
schema downgrade is attempted. Unknown database versions are rejected before DDL.

## Language and multimodal data

`add_sense` preserves distinct meanings of the same form, such as biology versus
spreadsheet "cell". `align_translation` creates a proposed, directional alignment;
no word substitution is treated as a verified sentence translation. The observed
term index is not a model tokenizer and does not change checkpoint vocabularies.

Images are decoded with a pixel budget; region bounds are checked. Recordings
retain original bytes and caller-declared duration. Provided transcripts have
timestamped anchors and original-source lineage. The optional FFmpeg worker
extracts selected frames with bounded commands and links requested seek times
back to the parent recording. Seek times are not asserted to be exact decoded
presentation timestamps. No speech-recognition model or general video-understanding
model is bundled. `add_structure` preserves supplied tables, equations and code
representations; it is not an automatic semantic parser.

## Data and model lifecycle

The `annotate` API records task-specific inputs/targets plus evidence. Classification
and extractive-QA targets have strict task checks; other task families preserve
bounded structured annotations and still require task-specific trainer validation.
Review is a distinct explicit operation. Use `freeze_dataset` only after checking
source rights, scientific/content correctness, independent cases and split families.
The core cannot independently authenticate a human reviewer's identity or rights.

All releases need train/validation/test partitions. Production-mode releases reject
unreviewed data and shared source families, exact original/extracted-content hashes,
case IDs and duplicate input/evidence pairs across splits. Demo mode is explicit
and never sufficient for model promotion. Near-duplicate editions still require
human grouping. This is a source-disjoint protocol, not every possible QA benchmark.

```bash
python -m tiny_experts.knowledge_core --root ./state/knowledge --curator review RECORD_ID accepted --note "Actual review scope"
python -m tiny_experts.knowledge_core --root ./state/knowledge --curator freeze RELEASE_NAME ./assignments.json
python -m tiny_experts.knowledge_core --root ./state/knowledge export DATASET_ID --partition train --output ./train.jsonl
python -m tiny_experts.knowledge_core --root ./state/knowledge export DATASET_ID --partition train --pretraining --output ./corpus.jsonl
```

Exports default to the training partition, not the whole dataset. Classification
exports include the existing trainer's `text`, `labels`, `reviewed`, `reviewer`,
source/family/revision and case fields; QA exports contain question, passage,
answer and exact start offset. Explicitly export validation/test for the evaluator.
Do not combine test labels into an LLM pretraining corpus. A cross-project holdout
registry and near-duplicate detection are still separate work.

`record_training_run`, `register_model` and `record_evaluation` capture **actual
externally executed observations** supplied by the operator. They do not execute
training or fabricate measurements. A model needs a non-demo data lineage,
matching held-out report, explicit sample minimum, metric bounds, checksum and
operator approval before nonexperimental runtime binding. Evaluation reports are
operator-supplied; meeting a numeric threshold is not scientific certification.

## Limits and known incomplete portions

- This is a local modular foundation, not all eventual applications in the blueprint.
- 163 concepts and 24 core aliases are seed coverage, not 163 mastered subjects.
- The new facade is opt-in; all existing CLI/UI workflows have not been globally
  switched to it. The full legacy regression suite needs a fresh exact-tree run.
- Core handler bindings attest an available callable; framework/model loading must
  be checked by each model adapter. Some tests use explicitly synthetic dummy
  model bytes to exercise governance, not claim trained models.
- Synchronous execution bounds calls and payloads but does not kill blocking Python
  functions. Untrusted code and browser actions need sandboxed executors with
  network, CPU, memory, timeout, cancellation and approval controls.
- The queued-job API has leases/retry limits, not a continuously running worker.
- Static HTML snapshots and inherited allowlisted text fetching do not implement a
  public crawler, whole-web search, ranker, robots scheduler or live price service.
- Limits are 20 MiB per asset, 8 MiB extracted text, 5,000 annotations per release,
  32 workflow steps and 100 search hits. Large-corpus streaming/object storage is
  intentionally future infrastructure; no unlimited scalability claim is made.
- The HTML dashboard is a safe offline snapshot (up to 1,000 records per kind),
  not a live multiuser training studio. Paginated APIs cover larger directories.
- Source review and permissions remain data requiring responsible human validation.

## Validation

Run `python -m pytest -q tests/regression/test_knowledge_core.py` on the exact tree.
The optional installed browser-rule test skips when PR #4's Python package is not
installed. A local run with that exact package and system FFmpeg also tests real
HTTP requests, deterministic browser-rule composition and actual frame extraction.
Neither constitutes real-site automation or an installed DeepSeek runtime test.
See `KNOWLEDGE_CORE_VALIDATION.md` for measured results and environment.
