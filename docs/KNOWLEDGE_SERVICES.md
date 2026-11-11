# ExpertOS source services v0.2

**Working implementation; optional model adapters; not a production certification.**
This extends `feature/knowledge-core-v1` and depends on PR #6. It does not replace
the old application's entry point or silently enable neural models or crawling.

## Six implemented areas and honest boundaries

1. **Speech recognition:** a local faster-whisper adapter, measured media duration,
   bounded 16 kHz mono audio chunks via FFmpeg, timed transcript publication,
   source ancestry, cancellation, and model provenance. There are no model weights
   in Git. This runner used a fake ASR provider to test the integration against
   real FFmpeg output; no transcription-accuracy result is claimed.
2. **Learned translation:** a local standard Transformers seq2seq adapter for an
   explicitly configured language pair, protected terminology/code/formula
   markers, numeric consistency checks, source/translation alignment, and
   unreviewed derived records. Special multilingual models needing custom code,
   target-token handling or task prompts require a dedicated adapter. This is not
   an automatically installed IndicTrans2 service or verified dictionary.
3. **Semantic retrieval:** local Sentence Transformers query/document embeddings,
   source-addressed token-window subdivision, persistent versioned vectors,
   resumable indexing, exact cosine scan, lexical FTS retrieval, reciprocal-rank
   fusion, optional CrossEncoder reranking, and final evidence verification.
   Rights, active revisions and tenant scope are checked before vector scoring.
   Ranking scores are not answer confidence or entailment.
4. **Crawling/indexing:** operator-approved same-site public HTTPS, pinned DNS and
   verified TLS, robots checks, noindex/nofollow, persistent frontier, per-site
   throttling, depth/page/byte quotas, conditional fetches, change detection,
   bounded retries, and source revisions. No authenticated sessions, anti-bot
   bypass, dynamic JavaScript execution or arbitrary browser automation.
5. **Larger corpus infrastructure:** streaming immutable assets, UTF-8 text chunks
   with global character and byte locations, incremental full-text indexing,
   preserved vocabulary observations, leased/idempotent worker operations,
   cancellation and retry, streaming pretraining export, backup/restore, and
   optional encrypted private S3-compatible blob replication.
6. **Deployment and evaluation:** model manifests and checksums, CLI diagnostics,
   authenticated loopback bridge, isolated worker process, task metrics, acceptance
   tests, GitHub Actions matrix, and a non-root read-only Linux container recipe.
   Docker, Windows, live remote endpoints, hosted CI, and real downloaded models
   must be validated separately on a connected installation.

## Architecture

`EnhancedCore` subclasses the existing `KnowledgeCore`. Existing source IDs,
review state, source ancestry and permission rules are reused. `CoreExpertSystem`,
`CoreBookView` and the existing bridge accept it without a second source directory.
Configured external models appear as `installed_external_model` entity records
when bound. They are not misrepresented as our own trained/approved model releases.

```python
from tiny_experts.knowledge_services import EnhancedCore
from tiny_experts.knowledge_core.system import CoreExpertSystem

with EnhancedCore('./state', curator=True) as core:
    core.bootstrap()
    core.bind_services()  # retrieval available; absent neural models remain unbound
    app = CoreExpertSystem(core)
    print(core.service_health())
    print(app.process('heat engine', concept_ids=['concept.thermodynamics']))
```

## Minimal start (no neural downloads)

Run from the repository root, Python 3.11 or newer:

```bash
python -m tiny_experts.knowledge_services --root ./state doctor
python -m tiny_experts.knowledge_services --root ./state import ./book.txt \
  --key book-v1 --title "Actual title" --license-note "Actual source permission"
python -m tiny_experts.knowledge_services --root ./state search "heat engine"
```

The import defaults to storage/retrieval only, **not training or redistribution**.
Binary PDF/EPUB extraction still uses the existing bounded document extractor.
Streaming TXT/Markdown/CSV/code text is supported directly; this release does not
pretend to implement an arbitrary-size PDF layout/OCR service.

The old `ingest(bytes)` and `read_asset()` retain their small in-memory limits.
The new streaming path defaults to a **2 GiB original asset ceiling** and a
**256 MiB normalized-text ceiling**, processes bounded chunks, and preserves the
whole normalized-text hash. These are configured ceilings, not tested maximum
sizes or throughput promises. The acceptance suite actually crosses both previous
limits with a >20 MiB asset and >8 MiB text ingestion.

## Install model providers explicitly

Install FFmpeg/FFprobe using the operating system's package manager. Optional
neural packages are listed in `deploy/knowledge-services/requirements-neural.txt`.
These dependency ranges need a resolved lock after real-model compatibility testing.

Download a compatible model from its official source in a connected environment,
review its model card, permissions and provenance, and copy the complete model
directory locally. Embedding/seq2seq/reranker loaders require safetensors and
`trust_remote_code=False`; the speech adapter uses CTranslate2 format. Do not put
private data, access tokens or model weights in Git.

```bash
python -m pip install -r deploy/knowledge-services/requirements-neural.txt
python -m tiny_experts.knowledge_services --root ./state manifest ./models/embed embedding \
  --source "Actual model source and pinned revision" --license-note "Actual permission"
python -m tiny_experts.knowledge_services --root ./state manifest ./models/speech asr \
  --source "Actual model source and pinned revision" --license-note "Actual permission"
python -m tiny_experts.knowledge_services --root ./state manifest ./models/translate translation \
  --source "Actual bilingual model and revision" --license-note "Actual permission" \
  --source-language en --target-language hi
```

A profile manifest detects changed files; it does not authenticate its author or
prove linguistic quality. Missing weights/dependencies fail explicitly. There is
no dictionary substitution masquerading as a learned translator and no synthetic
embedding fallback masquerading as semantic inference.

Example operator configuration (paths relative to this JSON file):

```json
{
  "limits": {"embedding_batch": 16},
  "models": {
    "embedding": "./models/embed",
    "asr": "./models/speech",
    "translation": "./models/translate"
  }
}
```

Only include models actually installed. The current translator handles ordinary
bilingual seq2seq models; validate the specific checkpoint's generation contract.
Numeric and glossary checks are conservative and can reject a valid localized
translation. Passing them is not a proof of meaning preservation.

## Search and recorded media

```bash
python -m tiny_experts.knowledge_services --root ./state --config ./services.json index
python -m tiny_experts.knowledge_services --root ./state --config ./services.json search "heat cannot all become work"
python -m tiny_experts.knowledge_services --root ./state import ./lecture.mp4 \
  --key lecture-1 --title "Lecture" --mime video/mp4 --license-note "Actual permission"
python -m tiny_experts.knowledge_services --root ./state --config ./services.json transcribe REVISION_ID
python -m tiny_experts.knowledge_services --root ./state --config ./services.json translate SEGMENT_ID hi
```

Indexing returns a cursor; pass `--after CURSOR` to continue a bounded run. An
initial index over changing content is not a globally consistent snapshot: rerun
from the beginning to include concurrent additions that sort before the cursor.
Idempotent segment/model/text-hash checks avoid duplicate embeddings.

Audio chunks are non-overlapping; boundaries and technical vocabulary can cause
recognition errors. ASR is not speaker diarization, formula recognition, or voice
command execution. Original audio/video remains the reference. Translations and
ASR transcripts remain unreviewed, with their originating family and revision.
A model prediction cannot grant training permission or promote itself.

## Controlled crawling

```bash
python -m tiny_experts.knowledge_services --root ./state crawl-config https://example.org/ \
  --max-pages 100 --license-note "Operator-verified access and intended use"
python -m tiny_experts.knowledge_services --root ./state --allow-network crawl WEBSITE_ID
```

Use a real approved origin in place of the example. Configuration does not fetch
anything. Network execution requires `--allow-network`; installed model loaders
still remain local-only. Robots 404 permits requests; 401/403, server failures,
network failures and robots redirects stop the crawl conservatively. Per-host
throttling includes robots requests. Page redirects are re-enqueued and checked,
not followed automatically. A batch may process zero pages because it must wait;
the frontier survives restarts. Configure external scheduling deliberately.

This is **bounded vertical crawling**, not a whole-web search engine. The default
per-site cap is 100 pages, with a configured ceiling of 1,000 in this release.
Sitemaps, RSS discovery, browser-rendered pages and cross-site link traversal are
not implemented. Robots permission is not copyright or training permission.

## Durable workers

```bash
# job.json: {"max_segments":10000}
python -m tiny_experts.knowledge_services --root ./state enqueue semantic_index ./job.json --key initial-index
python -m tiny_experts.knowledge_services --root ./state --config ./services.json worker-once
python -m tiny_experts.knowledge_services --root ./state operation OPERATION_ID
python -m tiny_experts.knowledge_services --root ./state cancel OPERATION_ID
```

An explicit isolated process handles one job. A supervisor can invoke it repeatedly;
no assistant/background task is created by these commands. Jobs use leases,
idempotency keys, attempt budgets and exponential retry delays. The worker prints
its operation status; a processed failed job does not necessarily mean the worker
process itself crashed. On POSIX, whole-process-group timeouts kill codec children.
Windows requires a Job Object/container for equivalent descendant containment.
Cancellation is checked before publication. Operations remain experimental, not
exactly-once external side-effect transactions.

SQLite metadata and exact vector scans are appropriate for a bounded single-host
installation. This release does **not** replace metadata with PostgreSQL, introduce
ANN/distributed vector serving, or prove million-page throughput. Optional S3Mirror
replicates immutable blobs with private keys and server-side encryption; it does
not distribute SQLite or automatically erase remote copies on withdrawal.

## Deployment and security gates

The loopback server keeps the existing `/v1/core/search` route and bearer-token,
Host and Origin checks; health now includes model/queue/index diagnostics.

```bash
# Supply EXPERTOS_BRIDGE_TOKEN or EXPERTOS_BRIDGE_TOKEN_FILE securely.
python -m tiny_experts.knowledge_services --root ./state --config ./services.json serve
```

The Linux compose file uses host networking solely to preserve strict loopback
binding. Prepare `state/` ownership for UID 10001 and a secret file before startup.
Keep the state volume encrypted and backed up, use an egress firewall, and sandbox
untrusted media. The container recipe has not been built in this offline runner.
Do not expose this trusted-local-process API as a public multi-tenant service.

A curator is an application-controlled context, not a self-asserted HTTP field.
Assets are immutable by convention and verified on use, but a hostile OS
administrator is outside this local API's security boundary. No credentials enter
the source corpus. Signed-in browser data is not harvested by the crawler.

## Evaluation and future rollout

`evaluation.retrieval_report` measures Recall@k and MRR from explicitly reviewed
relevance records. `word_error_rate` measures edit-distance WER with documented
whitespace tokenization. Neither supplies independent test data.

Before promotion: install and pin real models, validate speech/translation on
held-out languages and technical terminology, compare retrieval with lexical
baselines, test permitted live sources, measure resource usage and recovery,
run the full repository suite, test Windows and the actual Harness product,
and restore hosted CI. Keep production approval distinct from passing plumbing
tests or simply loading a pretrained checkpoint.
