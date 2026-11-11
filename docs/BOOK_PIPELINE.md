# Book ingestion and supervised-training pipeline

This prototype does not require a generative LLM. `BookEngine` uses lexical
FTS5/BM25 retrieval, and the trainer learns categorical labels only.

## Local book import

```bash
python book_pipeline.py --data-dir ./state/books import-file ./book.txt --title "Actual title" --shelf literature --license-note "Check actual rights and source"
python book_pipeline.py --data-dir ./state/books sources
```

The source remains **unreviewed** and **does not train** a neural model.
Its extracted UTF-8 text is stored in a SHA256-addressed snapshot; passages
contain exact character offsets and a revision hash.

## Retrieved passage

```bash
python book_pipeline.py --data-dir ./state/books query YOUR_DOCUMENT_ID "Where was the shoe lost?"
```

Results are excerpts with offsets and provenance, not certified answers.
Unknown and stale document revisions explicitly fail.

## Online sources

```bash
python book_pipeline.py --data-dir ./state/books check-sources
python book_pipeline.py --data-dir ./state/books import-url https://www.gutenberg.org/cache/epub/14838/pg14838.txt --title "The Tale of Peter Rabbit" --license-note "Check public-domain status in your jurisdiction"
```

Only allowlisted public HTTPS hosts, redirects, ports and bounded plain text
responses are accepted. The sandbox that ran this demonstration had no outbound
DNS: Gutenberg, Wikipedia and PubChem all returned `network_unavailable`.
That is **not** evidence of a healthy live download. No offline cache is used
to disguise failures; use a permitted local copy if the live source is unavailable.

## Model training

1. Verify source rights and save accurate metadata.
2. Review passages and create labeled JSONL with real evidence quotes.
3. Export a source manifest with `BookWorkflow.export_sources()`.
4. Mark actual verified reviewers only after human examination.
5. Use `train_book_expert.py` and a categorical training config. Non-demo
   mode requires source-family-separated splits; a single book cannot certify
   unseen-source generalization.
6. Check accuracy, unknown cases, citation support and performance on held-out
   books before enabling a model. A neural book *reader* is not yet implemented.

```bash
python train_book_expert.py --data-dir ./state/books --data ./annotations.jsonl --sources ./sources.json --config training/configs/genetics_topics.json --output ./trained/reader_classifier
```

`--demo` allows an unreviewed single-book smoke test and marks the resulting
model **experimental**. It remains disabled by normal inference.

## Remaining limitations

These commands do not establish scientific correctness, verified source
permissions, page-perfect PDF extraction, open-domain language reasoning,
training scale to thousands of experts, or live source availability.
