# Coordinated component answers

Harness uses complementary components for a question; it does not ask every
component to produce a competing answer or turn component agreement into a
confidence score.

## Physics questions

1. Existing concept rules or neural classifiers select the physics topic.
2. The formula/symbolic solver attempts supported numerical work.
3. A relevant Mechanics, Circuit or Thermodynamics Calculator evaluates the
   original query. Only named calculated outputs for the same target variable
   and SI unit can corroborate the primary result. Calling the same universal
   solver twice does not count as a separate check. Unsupported comparisons
   and reviewer failures are reported. Conflicting values withhold a single
   numerical answer rather than being averaged.
4. Whole-term dictionary matches can supply up to two stored definitions.
5. Textbook retrieval and source integrity checking supply reference passages;
   the existing limited conflict checker compares suitable retrieved claims.
   A lack of comparable evidence does not count as verification.
6. The explanation renderer combines the primary answer, available definitions,
   calculation checks and unresolved warnings. The answer and execution report
   list the components used and their actual statuses.

Relative comparison tolerance is 0.1% to accommodate conventional rounding of
standard gravity. There is no absolute tolerance that would make tiny physical
values agree automatically. These checks do not establish scientific accuracy.

## Reference questions

Explicit biology, plant, source and related intents reach the existing
dependency-ordered component workflow instead of being forced through physics.
Relevant component results reach the renderer together. Harness turns use
temporary application sessions that are cleared after each turn, rather than
sharing the application's default conversation memory. This does not implement
general language understanding or conversational follow-up resolution.

## Components that work before answering

Source importers, the Leech Source Extractor, indexing services and supervised
trainers serve preparation workflows. They should not all run for every chat
question. Extraction produces candidates, ingestion produces searchable text,
and reviewed training produces model bundles through separate explicit steps.
No new weight training or source self-approval happens while answering.

Basic numeric arithmetic uses a restricted AST and bounded rational arithmetic
directly, avoiding a separate SymPy process for additions such as `20+6`.
Expression length, node count, depth, intermediate magnitude, exponent and
rational bit size remain limited. Functions and symbolic operations retain the
bounded subprocess path.

## Validation

`tests/regression/test_answer_coordination.py` covers relevant component
selection, exact target/unit comparison, zero and very small values, conflicting
results, failure reporting, repeated-solver non-independence, whole-term
dictionary matching, multi-domain Harness output and temporary-session cleanup.
It also covers the previously observed `3rd law of newton` wording error.
