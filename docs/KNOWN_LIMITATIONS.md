# Known limitations of version 0.2

## Model quality and source truth

The regression tests establish specific software behavior, not scientific expertise. All three training smoke runs use legacy demonstration data; their scores are not field accuracy evidence. No diagnostic model is promoted by this revision. Raw legacy model files are excluded and cannot silently activate.

The old pathology labels lack healthy/unknown and many independent cases, and some configured outputs have no original examples. Reviewed training rejects unrepresented output labels; redesign the task and collect data before production use. The runtime's negation guard is intentionally conservative and can reject legitimate explanatory questions containing negative words. It is not a learned language-understanding system.

A reviewer string and `reviewed: true` are records of an external workflow, not proof of scientific validity. Artifact hashes detect mismatches, not factual errors. The categorical model has no general language generation, extractive reading, span labeling or confidence calibration. Word/bigram features can confuse meaning, word order, unfamiliar wording, and out-of-distribution cases.

Retrieved source snippets and legacy rule/profile text remain unreviewed. They are labelled accordingly. Bibliographic catalog records do not mean full books are installed. A source hit is not automatically support for an answer. Imported PDF page/section precision depends on extraction and supplied metadata; a complete citation-support checker is future work.

## Runtime scope

The expert order is deterministic, and completed outputs are available to downstream modules. Prerequisites are ordering constraints among active experts; the DAG does not discover arbitrary plans or run missing prerequisites automatically. There is no general-purpose reasoning LLM or learned planner.

The scientific reference experts have a small set of stored topics. Phrases and terms select references, and some still require finer task definitions. Their coverage must be expanded with reviewed sources and independently tested tasks. Broad linguistic variants and all languages are not supported uniformly; the current communicator renders English summaries.

The numeric parser supports explicit named quantities and documented units. It is not a general physics problem parser, circuit solver or dimensional-analysis package. Symbolic operations support a limited grammar and time bound; rejecting an unsupported expression is expected behavior. A formula result does not validate the physical model chosen by the user.

Taxonomic inheritance is based on a small curated graph. Broad family-level traits, exceptions and provenance still need review; inherited hazards are not confirmation about an individual specimen. Weather risk is an unvalidated heuristic rule assessment, not calibrated outbreak prediction. Diagnostic procedures are references, not executable laboratory-confirmed diagnosis. Potential chemical interaction rules do not establish clinical outcomes.

The optional archived news/blog/video/market feeds are disabled by default and must not be presented as live facts. Legacy regulatory/reference records are not a current jurisdiction-aware legal service. Toxicity unknowns stay unknown, and unsafe default 'safe' conclusions are removed.

## Deployment and data scale

The HTTP server is for one local user on loopback. Origin/host and size checks reduce concrete local-server risks; this is not a complete authenticated, encrypted, internet-facing service. Do not expose it to a network without a separate deployment design. Shared requests are serialized for correctness, limiting throughput. Multi-process writers and large model pools need further engineering.

The corpus is loaded in memory and the SQLite cache synchronizes on startup. This is appropriate for a small prototype, not all existing books or a web-scale knowledge store. A large deployment needs incremental indexing, provenance/version management, model lifecycle controls, a capability registry, resource budgets and workload evaluation.

Session IDs isolate application memory logically; they are not authentication credentials. There is no multi-account security boundary. Explicit reset clears the selected session; retention/export controls require product work before a shared service.

## Historical tests

The original tests are preserved under `tests/legacy`. Several asserted inflated confidence, simulated `<think>` tags, default unrelated catalog results or unconditional safety conclusions, and many pathology questions were training examples. Those expectations are obsolete and do not constitute generalization evidence. They are not the current pytest/CI gate. The maintained regression suite lives in `tests/regression` and tests corrected behavior with isolated state.
