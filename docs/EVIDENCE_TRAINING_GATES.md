# Evidence and model-training readiness gates

This branch hardens **specific** legacy pathways; it does not certify the complete
knowledge base or enable new subject models.

## Before accepting any book-derived supervision

1. Record the actual source identifier, edition, author/publisher (when known),
   license/permission, file hash and extraction version. Never invent metadata.
2. Store the original source and immutable passage locators. OCR or page positions
   must be reported as unknown unless actually observed.
3. Separate **source indexing** from **model training**. Indexing a book alone
   never changes neural weights.
4. Require reviewed labels, question/answer evidence spans and explicit
   unsupported/unknown examples. Reviewers must check that answer locations
   support each label.
5. Split by source and underlying real-world case *before* augmentation and
   vocabulary fitting; report held-out source and case metrics separately.
6. Train in a restricted environment with no automatic network access, and
   do not permit untrusted book contents to execute code or shell commands.
7. Promote a model only after independent testing (accuracy, coverage,
   abstention, per-class errors, robustness to negation, evidence support).
8. Keep manifests, hashes, tokenizer, labels, training provenance,
   evaluation and rollback with each promoted model.

## Remaining blockers

- The old encyclopedia harvester is a discovery tool, not a safety database.
- Synthetic diagrams are not authenticated textbook figures.
- Family/genus traits cannot establish toxicity, chemical contents or
  antidotes for an individual species.
- A crop-price ratio cannot establish treatment return on investment.
- A matched bulletin does not confirm an outbreak at the user's location.
- Numerous legacy rules and citations elsewhere still need independent review.
- A capable neural passage reader, grammar editor, and independent scientific
  corpus are **not** implemented by these changes.

No general-purpose LLM is required for the supervised training process.
