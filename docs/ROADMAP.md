# Development and training roadmap

## Milestone 1: corrected local baseline

Implemented in version 0.2: honest routing and unavailable states, exact-tool input fixes, bounded symbolic parsing, explicit execution events, session isolation, source replacement/provenance, reviewed-data training schemas, complete bundles and regression gates. Read VALIDATION.md for the observed checks; this is not a claim that every scientific statement has been reviewed.

## Milestone 2: one credible pathology task

1. Define the intended host/crop, observation inputs and output scope. Prefer disease candidates plus unknown/insufficient evidence; separate assay/management decisions.
2. Assemble source-permitted, reviewed cases with real source/specimen IDs. Add healthy samples, insufficient descriptions, lookalikes, negative findings and confirmed alternatives.
3. Review the legacy profile text, remove unsupported claims and attach source/passage provenance. Do not convert a topic classifier label directly into a treatment instruction.
4. Compare rules, a simple lexical baseline and the small neural model on independent sources/cases. Report per-class errors, confusion, coverage, rejection quality and full answer support.
5. Tune acceptance on validation data and calibrate with appropriate held-out data. Keep a final untouched test set and evaluate real field inputs separately from textbook examples.
6. Version the accepted bundle and define an explicit deployment threshold/rollback procedure. Add model-specific regression cases based on real errors.

## Milestone 3: one additional neural subject

Use `genetics_topics` as a bounded starting configuration. Train only after annotation and splits are ready. Register it through `register_neural_expert`. Establish that adding one specialist improves a real task relative to the existing reference lookup before multiplying it.

For a grammar expert, define a narrow edit class such as subject–verb agreement, gather error/correction pairs, then implement a sequence tagger or constrained edit model with span/edit evaluation. The current categorical trainer can detect an error category but cannot perform unrestricted correction.

## Milestone 4: source-grounded readers and actual decision workflows

Add retrieval/reranking datasets, extractive answer/no-answer targets, entity/quantity extraction, and claim-to-passage support checks. Turn diagnostic procedures into typed question/test nodes with unknown branches and recorded observations. Give rule conclusions explicit premises, applicability conditions, provenance and unresolved conflicts.

## Milestone 5: a larger expert mesh

Replace growing keyword tables with a versioned capability registry, measurable task descriptions and a trained multilabel router where justified. Route only relevant experts. Add budgets, prerequisites, data contracts, failure/rejection behavior and independent evaluators before asynchronous execution or large model pools.

Choose the next expert from measured workload gaps. One thousand names or checkpoints do not guarantee useful coordination. Track end-to-end answer quality, source support, latency, memory, rejection quality and marginal value for every added capability.
