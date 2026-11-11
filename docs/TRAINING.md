# Training neural experts without an LLM

## 1. Define a measurable task

A small neural expert learns a mapping from observations to targets. Examples include disease-candidate classification, genetic-topic classification, router intent, image class, error-span tagging or source relevance. These are different learning problems. The reusable trainer in this revision supports **one or more categorical text-classification heads**. It is not a general reader, generator, sequence editor, multilabel classifier, or numerical solver.

Keep numerical algorithms and symbolic tools as tools. A future trained parser can choose an operation and extract its inputs; do not replace exact arithmetic with a paragraph predictor.

## 2. Keep sources and annotations separate

First import a source with `import_book.py`. Preserve actual metadata and the source/page or passage IDs. This updates retrieval only.

Then prepare independently reviewed examples. Do not treat current expert answers, synthetic diagrams, or the old exported `verified_factual` field as gold labels. The response exporter now explicitly marks generated candidates unreviewed. It is a different format from the classifier dataset.

A text training record is one JSON object per line:

```json
{
  "id": "genetics-case-0001",
  "case_id": "original-case-family-0001",
  "source_id": "document-revision-or-independent-dataset-source-017",
  "text": "How is an RNA copy made from a DNA template?",
  "labels": {"topic": "transcription"},
  "reviewed": true,
  "reviewer": "actual-reviewer-identifier",
  "evidence": [{"document_id": "actual-document-id", "passage_id": "actual-passage-id", "page": 42}]
}
```

The values above illustrate the schema. Replace source and evidence placeholders with real records. `reviewed: true` is an assertion by your annotation workflow, not automated verification by this trainer. The included `training/examples/annotation_template.jsonl` deliberately stays unreviewed.

Required fields are `id`, `case_id`, `source_id`, `text`, `labels`, `reviewed` and `reviewer` for normal training. `labels` must contain exactly the configured heads and valid label strings. Evidence is retained in dataset hashing but its scientific support is not automatically checked; human/source review remains necessary.

Use a stable source ID for a document revision or acquisition source. Keep paraphrases, repeated observations, near-duplicate images and template variants in the same case family. Do not assign new IDs merely to make a split pass.

## 3. Partition before fitting features

The default splitter keeps connected **sources, cases and normalized exact-duplicate text** together. It needs at least three independent groups for train, validation and test. All represented target labels must exist in training; all configured labels need training examples in reviewed mode.

You can supply a `split` field (`train`, `validation`, `test`) on every row. The trainer rejects overlaps across those explicit splits. If none is supplied, it selects groups with a seeded split while retaining all observed labels in training. It does not guarantee every class is represented in validation/test; inspect the reported class coverage and add independent data where necessary.

Source-level separation is deliberately conservative. A single textbook may be useful background data but cannot also establish unseen-source generalization. Case-only splitting requires experimental demo mode and is labelled accordingly.

Vocabulary is fitted from **training text only**. The feature representation preserves short and negative words and adjacent bigrams; no random word-scrambling augmentation is used. This preservation does not make a bag-of-words model understand every negation or contradiction.

## 4. Configure an expert

`training/configs/genetics_topics.json` is a minimal single-head example. The pathology configuration retains the legacy disease/pathogen/kingdom/assay/strategy label sets for compatibility. The latter requires reviewed examples for every configured target, or an intentionally revised task definition.

```bash
python train_expert.py \
  --config training/configs/genetics_topics.json \
  --data training/private/genetics_reviewed.jsonl \
  --output tiny_experts/data/models/genetics_topics
```

Useful overrides are `--epochs`, `--batch-size`, `--learning-rate`, `--seed`, and `--threads`. Existing nonempty output directories are protected; use a new version directory or explicit `--overwrite`.

The current loss uses cross entropy per head, with configurable head weights. Multiple heads represent separate categorical decisions; they are not a multilabel output. Undefined labels must be designed explicitly for this version—partial/masked targets are not implemented.

Pathology shortcuts:

```bash
# Export the original 165 examples as explicitly unreviewed records.
python train_pathology_expert.py --export-demo training/private/pathology_legacy_demo.jsonl

# Exercise training on legacy data, without promoting it into normal runtime.
python train_pathology_expert.py --demo --epochs 2 --output runs/pathology-demo

# Use an independently reviewed dataset and activate the corresponding bundle path.
python train_pathology_expert.py --data training/private/pathology_reviewed.jsonl --output tiny_experts/data/models/pathology
```

Calling the pathology/router trainer without `--data` is an explicitly announced experimental legacy demo. `--demo` also permits unreviewed custom data. The generic entry point requires `--allow-unreviewed-demo` to permit that mode. Such bundles stay disabled in normal inference.

For the optional neural router:

```bash
python train_router.py --data training/private/router_reviewed.jsonl --output tiny_experts/data/models/router
```

The current router head is categorical. Whole-term rules can activate multiple domains; do not interpret its softmax scores as independent multilabel probabilities. A future multilabel router needs new targets, loss, threshold validation, and runtime schema.

## 5. Evaluate before promotion

Training uses AdamW, a learning-rate schedule, early stopping and a cloned best validation checkpoint. The final test split does not select the checkpoint.

`metrics.json` includes every active head, per-class support/precision/recall/F1, macro F1, confusion matrices, loss, class coverage, zero-feature counts, and acceptance coverage/accuracy at the configured score threshold. Empty accepted subsets return no accuracy instead of an invented value.

Read the class support counts before interpreting aggregate metrics. Explicitly inspect healthy/unknown/out-of-domain inputs, negation, lookalikes, ambiguity, changed sources and unseen entities. Evaluate the full expert output and retrieved evidence separately from label accuracy. The current metrics are not confidence calibration; temperature scaling or another calibration method remains future work with appropriate held-out data.

The built-in threshold is a starting configuration, not a validated universal threshold. If you tune it, use validation data; reserve final test data for the final evaluation. Repeatedly tuning against the test report invalidates its role as a final holdout.

## 6. Model bundle and runtime

A text bundle contains:

- `model.pt`: weights plus model metadata, loaded with `weights_only=True`.
- `vocab.json`: the exact training vocabulary.
- `manifest.json`: schema, task identity, label order, architecture, preprocessing, training configuration, hashes, acceptance settings, status and limitations.
- `metrics.json`: training/validation/test metrics and history.
- `splits.json`: example, case and source membership with hashes.

New bundles are staged before publication. Replacement writes the manifest last, so a partially replaced/mismatched package cannot silently load. Loading checks the artifact hashes, feature version, label maps, shape, task ID and finite parameters. Hashes detect inconsistent files; they are not a proof that source labels are true.

A `reviewed_data` status records the annotation workflow. It does not imply production or diagnostic approval. Missing/invalid bundles, zero recognized features, rejected labels and scores below threshold abstain. Normal runtime does not load `experimental` bundles. Legacy loose `.pt` files are not sufficient.

Connect an additional reviewed text task:

```python
from tiny_experts import TinyExpertOrchestrator
system = TinyExpertOrchestrator()
system.register_neural_expert(
    "genetics_topics", "tiny_experts/data/models/genetics_topics",
    shelf="genetics", keywords=["transcription", "mutation", "crispr"],
)
result = system.process_detailed("Explain transcription")
```

The ID must match the bundle, must not replace an existing expert, and must use an existing registered shelf. Adding a new discipline requires defining its shelf and capability deliberately. The classifier plus retrieval adapter is suitable for bounded label tasks; its source matches are not automatically validated supporting evidence.

## 7. Train the leaf image specialist

The image trainer requires a separate reviewed JSONL manifest:

```json
{"id":"image-001","case_id":"specimen-017","source_id":"field-site-season-batch-03","path":"early_blight/leaf-001.jpg","label":"early_blight","reviewed":true,"reviewer":"actual-reviewer","synthetic":false}
```

Paths resolve under `--data-dir`. Use real source/specimen grouping, not random image IDs as independent specimens. The current runtime class order is `bacterial_spot`, `early_blight`, `healthy`, `late_blight`, `powdery_mildew`; reviewed training requires each class represented in training.

```bash
python train_leaf_vision.py \
  --data-dir /path/to/real/images \
  --manifest training/private/leaf_reviewed.jsonl \
  --output tiny_experts/data/models \
  --epochs 20
```

Validation/test transformations are deterministic and distinct from training augmentation. BatchNorm maintains running statistics; the best validation checkpoint is saved. Source/case grouping and identical-image checks prevent known overlap, but perceptually near-duplicate images still require review. Images from the old synthetic benchmark are demo fixtures, not field accuracy evidence.

The output comprises `leaf_vision_mobilenet.pt`, `leaf_vision_manifest.json` and split metadata. Runtime requires the matching architecture, label order, preprocessing and checksum. It reports the actual uncalibrated score with no floor. It has no general species-identification head.

## 8. Other expert types

| Capability | Suitable training target | Additional component |
|---|---|---|
| Topic or intent | Categorical label(s) | Current trainer and task definition |
| Disease hypothesis | Reviewed cases, unknown/healthy examples | Evidence and domain validation; separate management review |
| Book retrieval | Query, relevant passage IDs, hard negatives | Retriever/reranker training |
| Book question answering | Question, passage, supported answer span, no-answer | Extractive reader and support evaluation |
| Grammar correction | Error spans, edit tags, accepted corrections | Token/sequence model; the topic classifier cannot locate arbitrary edits |
| Scientific problem parsing | Operation, quantities, units, constraints | Structured extractor feeding the existing exact solver |
| Images | Images with classes/regions and specimen/source IDs | Vision model and independent real-image evaluation |

A useful mesh grows through measured capabilities, not by copying one classifier into hundreds of named classes.
