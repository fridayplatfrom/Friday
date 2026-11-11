# Train and evaluate the experimental browser-action network

The browser-action classifier is an optional, tiny PyTorch MLP. It is **not**
a small LLM and cannot itself navigate, click, or type. Its labels are only:
`navigate`, `extract`, `fill_form`, `abstain`.

## Dataset

Create a JSONL dataset containing each observed `task`, `context`, `label`,
`site_id`, `case_id`, `split` (`train`, `validation`, `test`), `reviewed` and
`reviewer`. Use different websites in every partition. Never copy an identical
observed task into both training and evaluation. Include failed tasks,
negation, ambiguous fields, unexpected UI, and explicit `abstain` examples.

*Do not write `reviewed: true` unless a human really reviewed the label.*

## Train

```bash
PYTHONPATH=python python python/train_browser_policy.py \
  --data training/browser_actions_reviewed.jsonl --output runs/browser_policy --epochs 20
```

To test training mechanics with synthetic examples, pass `--demo` and label
those examples as simulation-only. Checkpoint, configuration and ordered
labels are saved with a SHA256 hash. The model is marked experimental and
remains disabled unless the Python bridge was started with both
`--action-model` and `--allow-experimental`.

## Acceptance criteria before deployment

1. Independently check source and demonstration rights.
2. Use site-disjoint splits and a final untouched website holdout.
3. Compare against rule-based baselines and report per-action F1, form
   completion, verified field accuracy, abstention quality and unsafe actions.
4. Test dynamic websites, repeated fields, autofill side effects, prompt
   injection, cancellation, CAPTCHA/login and broken layout recovery.
5. Keep the allowlist/approval/verification gate **outside** the neural policy.
6. Do not promote from tiny synthetic examples; gather real reviewed data.

No trained model bundle ships with this integration.
