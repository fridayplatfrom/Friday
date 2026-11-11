# Experimental neural passage reader

The project now includes a small **trainable neural span extractor**, not a
general-purpose LLM. The model takes the question and a retrieved passage and
predicts answer start/end token positions (or a no-answer label). It cannot
generate unrestricted explanations.

## What is implemented

* PyTorch embeddings + bidirectional GRU; question-conditioned start/end span
  scores and an explicit null-answer class.
* Separate train, validation and test data. Source-family, source-revision,
  duplicate question/passage, and underlying case leakage are rejected in
  non-demo training.
* Exact source snapshot hashes and passage offsets are verified by the book
  ingestion pipeline before training, retrieval and answer extraction.
* Model bundle includes architecture, vocabulary, model hashes, train/validation
  /test metrics, and explicit experimental status.
* Runtime rejects mismatched bundles and **disables experimental models by default**.
* The existing orchestrator exposes a typed process_book_question method that
  returns verified retrieved passages and optionally an experimental predicted
  span with execution traces. A predicted span is **not** proof of entailment.

## Training

First import a lawful source via book_pipeline.py. Prepare JSONL examples:
id, source_id, source_revision, case_id, split, question, passage_id,
answer_text, answer_start, reviewed and reviewer. For unanswerable examples,
set answer_text and answer_start to null. All answer offsets refer to the
retrieved passage, not raw PDF page coordinates.

For an offline *single-book demonstration*:

    python train_book_reader.py --books-dir ./state/books \
        --data ./demo_qa.jsonl --output ./runs/reader-demo \
        --epochs 30 --demo

For reviewed material, omit --demo and provide --review-manifest pointing to
a JSON object keyed by source ID, each entry with: sha256, review_status
"reviewed", reviewer, license, and source_family_id. These fields document
asserted review; their truth must be independently checked by humans.

    python train_book_reader.py --books-dir ./state/books \
        --data ./reviewed_qa.jsonl --review-manifest ./reviewed_sources.json \
        --output ./runs/reader-reviewed

Both versions remain **experimental**. A small one-book fixture cannot establish
generalizable reading accuracy.

## Observed demo results

On one normalized local copy of Beatrix Potter's *The Tale of Peter Rabbit*,
33 handwritten answer-span/no-answer examples were used. The experimental
reader, trained from scratch with no pretrained language encoder, obtained
only 1/5 = 20% exact-span matches on its held-out questions. This is *not*
a production reader or a verified model of scientific comprehension.

The pipeline's local data and source-consistency integration tests have passed
in the development environment. GitHub Actions previously could not start
because of account billing/spending-limit issues. Separately verify the
merged revision before deploying.

## Scientific data and pathology

The legacy pathology training examples are handwritten and augmented.
Near-duplicate validation metrics do not prove performance on new crop cases.
For an independent dataset with expert-reviewed records, consider
PlantExpertVQA: https://huggingface.co/datasets/SyedNazmusSakib/PlantExpertVQA
(Sakib et al., Scientific Data 2026; reported CC BY 4.0). Most questions
are **image-grounded**. It is invalid to evaluate a text-only pathology
classifier as if it had been given the image. Confirm terms for each
constituent image dataset and use the official split membership.

Until that independently reviewed dataset and its required images/records
are downloaded and evaluated, **no independent pathology accuracy claim is made**.

## Additional local validation after leakage hardening

A replayed local application copy passed `16` focused tests and `5`
parameterized subtests on 2026-11-05. These covered import, text offsets,
restart persistence, source tampering, neural model loading, evaluation guards,
and the orchestrator/reader integration. The isolated integration smoke case
intentionally reuses a passage and therefore runs only in explicit demo mode.
This result does **not** certify the exact merged GitHub tree or the historical
99-test baseline, and hosted CI remains unavailable until the GitHub Actions
billing/spending-limit issue is resolved.

The official PlantExpertVQA images and split records could not be retrieved
in the current environment. Published review claims are not a measured test
of this repository's pathology model.
