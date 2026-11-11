# ExpertOS Source Studio + Training Director v0.1

Source Studio is a **local-only, authenticated operator interface** built on the existing Knowledge Core and Knowledge Services. It does not replace the legacy app or independently train a general LLM. It is an initial software interface for source ingestion and controlled specialist training.

## Launch

From the complete `tiny-expert-system` checkout, install the existing project and Source Studio extras:

```bash
python -m pip install -e '.[studio,documents,dev]'
# Windows PowerShell: $env:EXPERTOS_STUDIO_TOKEN = (python -c "import secrets; print(secrets.token_urlsafe(32))")
# Linux/macOS:
export EXPERTOS_STUDIO_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m tiny_experts.source_studio --root ./state/knowledge serve --port 8766
```

Open `http://127.0.0.1:8766` and select **Connect to local core**. Paste the token generated for this process. The UI stores it in session storage; do not send it through a URL. The server only binds loopback and rejects cross-site API requests. This is a trusted single-operator interface, **not yet an Internet-facing multi-user SaaS**.

The server starts a local training-worker loop by default. Use `--without-worker` to prepare sources and datasets without automatically executing queued training. A one-shot worker can run separately:

```bash
python -m tiny_experts.source_studio --root ./state/knowledge worker-once
python -m tiny_experts.source_studio --root ./state/knowledge doctor
```

## Source workflow

1. In **Source Inbox**, upload a local TXT, MD, CSV, JSON, PDF, DOCX, EPUB, JPG, PNG, WEBP, WAV, MP3, MP4, or WEBM source. PDF/DOCX/EPUB extraction requires the main repository's document extraction modules. A scanned-only document requires a separate OCR process. The UI caps a single upload at 64 MiB; larger assets should use the Knowledge Services streaming CLI and dedicated workers.
2. Supply title, stable source key, language, provenance/rights note and optional subject IDs. The only initial rights are storage and private retrieval; enable training **only if independently permitted**. Redistribution is disabled.
3. Original bytes are SHA-256 addressed, and extracted text is indexed with source revisions and evidence offsets. The importer proposes subject links and narrow glossary-style answer-span examples. **All proposals remain unreviewed.**
4. In **Review Center**, check the source and each suggested annotation. Reviews record the local operator identity and note. Review is not proof that an external authority verified the material.
5. The core enforces training rights, accepted source and annotation review, independent source-family/case splits, and immutable release manifests before non-demo training.
6. In **Training Studio**, release a reviewed dataset with explicit `train`, `validation` and `test` assignments and a compatible training configuration.

## Three policies

- **Manual** — review/release, then explicitly queue training.
- **Automatic after approval (default)** — after a reviewed, authorized dataset release is created **with a compatible trainer config**, queue a training job; an enabled worker runs it.
- **Research auto** — only if the operator explicitly enables research preapproval; demo datasets can queue experimental jobs. No production deployment.

All policies keep **model promotion/deployment separately approved**. Uploading or indexing a source never starts training or upgrades a model. A queued job rechecks the immutable dataset and access rights immediately before execution. A revoked source fails the job.

## Training model compatibility and budgets

- `classification` uses `TrainingConfig` and the existing `train_expert` (categorical text model).
- `span_qa` uses the existing `train_reader` (extractive question-answer span model).
- Experimental browser-action proposals, ASR, translation, coding, multimodal and general LLM training are **not automatically matched to these two trainers**.
- Studio caps training configurations at 30 epochs, classifier vocabulary 10,000, hidden layer 512 and four CPU threads. Worker subprocesses have a 900-second timeout. Resource limits are preliminary and should be replaced by robust job/container quotas for public deployment.
- Training outputs are tagged experimental and are not deployed by this component. A run record and model-weight record are registered when a compatible, bounded checkpoint is present. If weights exceed the local core's 20 MiB metadata-asset limit, the external trainer bundle remains on disk and the model record is left absent; no false registry entry is created.

## API (bearer token required)

`GET /api/health`, `/api/sources`, `/api/concepts`, `/api/candidates`, `/api/jobs`, `/api/policy`, `/api/search`.

`POST /api/sources/upload` multipart with `file`, `title`, `source_key`, `license_note`, `language`, `allow_train`, `concept_ids`.

`POST /api/review`, `/api/sources/rights`, `/api/policy`, `/api/datasets/release`, `/api/jobs/queue`.

No arbitrary Python execution, shell action or automatic source review is exposed by this API. Source content is treated as data, never as instructions.

## Known limitations and follow-up validation

- Full DeepSeek Harness / Windows desktop integration, live external fetching, speech/translation model inference, and real scientific accuracy have not been validated here.
- Current topic suggestions use literal concept-label matching and a narrow `Term: Definition` text pattern; they are **candidates**, not learned semantic classification, automatic cross-book truth verification or automatic data annotation.
- The UI supports source and candidate review, but advanced reviewed-data curation, bulk taxonomy reassignment, identity management, browser action logging, generalized train/eval dashboards, and model promotion need further development.
- The web service is **trusted single-operator, loopback-only**. Production must add a dedicated auth/tenant gateway, upload malware scanning, sandboxed document decoders, CSRF/secret policies and quotas.
- The test suite uses synthetic and public-domain fixtures to check execution. Real expert performance must be evaluated on independent, rights-checked data before deployment.

## Assisted preparation of train/validation/test splits

The Review Center can create source-anchored manual question–answer annotations or categorical examples. QA answer text must occur exactly once in the referenced passage. These records remain proposed until reviewed.

After reviewing source rights, source records and all annotations, choose **Suggest source-separated splits** in Training Studio. The director groups accepted, training-permitted examples by source family, assigns at least one family each to validation and test, and returns a **proposal**; it does not freeze or train automatically at this step. The curator must review the suggested assignments and release the dataset. The core then performs stricter case/content/hash/lineage leakage checks and may reject the proposal.

The initial split proposer requires at least three source families and uses deterministic sorted grouping, not optimized class balancing. Before real training, inspect representation across labels and conditions and adjust the proposal as needed.
