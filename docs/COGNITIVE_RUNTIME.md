# ExpertOS cognitive runtime v0.1 — implemented bounded control, not general intelligence

This module is additive to the shared `KnowledgeCore` and `KnowledgeServices` and does **not** alter the original orchestrator's default behavior. Import:

```python
from tiny_experts.knowledge_services import EnhancedCore
from tiny_experts.cognition import CognitiveEngine, DefinitionLibrary

with EnhancedCore('./state/knowledge', curator=True) as core:
    core.bootstrap()
    cognition = CognitiveEngine(core)
    goal_id = cognition.goal('Check calculation', success=['Confirmed numerical result'])
    state_version = cognition.observe('experiment:1', {'temperature_kelvin':300}, expected_version=0)
    print(cognition.compare(goal_id, [
        {'id':'a','allowed':True,'metrics':{'quality':0.9},'evidence_ids':[]},
        {'id':'b','allowed':True,'metrics':{'quality':0.6},'evidence_ids':[]}
    ], weights={'quality':1.0}))
```

## What it does

- **Goal contracts:** explicit success conditions, constraints and bounded step budgets, with tenant-scoped immutable goal IDs.
- **World-state observations:** tenant-scoped versioned snapshots, optimistic concurrency and hashed audit events. Observations are supplied by a trusted observer; there is no general browser or screen perception yet.
- **Decision comparison:** two to sixteen alternatives scored by explicit, normalized, nonnegative criteria; disallowed options excluded; minimum-quality and ambiguity abstention; exact source evidence checked against access rights. Metrics come from trusted inputs, **not a trained decision model**.
- **Planning:** bounded dependency DAG, ready-capability check, required input and permission preflight, and an `approval_required` marker. Source passages cannot define executable plans. The optional trusted-process execution method calls `core.execute`; it stops unless an independent host verifier confirms a step. No auto-execution API is exposed in Studio.
- **Skills:** explicit curator registration and retirement of bounded workflows, without importing Python strings or silently learning from runs.
- **Observability:** per-goal decision and execution events; tenant isolation.
- **Reviewed definitions:** a curator-written scientific paraphrase links to 1..20 exact source segments and edition metadata. Source reviews and explicit definition review are required. Withdrawn or changed sources make definitions inaccessible for ordinary retrieval. Different definitions may coexist for different scientific scopes. No invented page locators.
- **Source Studio:** authenticated local HTTP endpoints, goal/choice forms, read-only runtime capability availability and definition review APIs. No public network or autonomous action execution.

## Test commands

```bash
python -m pip install -e '.[studio,documents,dev]'
python -m pytest -q tests/cognition tests/regression tests/services tests/studio
```

## Critical limits before real training and production

1. **No general-language reasoning, learned planner or trained neural decision expert** is bundled. The current comparator is transparent deterministic multi-criteria selection, and it requires legitimate task metrics.
2. **No autonomous general web/computer execution** is granted. Existing Harness PR remains a separate product integration requiring real environment and security validation.
3. **No source text self-approval.** Definitions and data labels require independent review. A reviewed paraphrase is not a guarantee of scientific consensus; exact validation is a domain expert responsibility.
4. **No new trainer coverage:** automatic Training Director supports categorical classification and extractive spans. Speech, translation, visual diagnosis, planning, code generation and learned pairwise ranking require compatible independent datasets, new trainers and evaluations.
5. **Trusted local operator only.** Cognition uses the core's tenant selector and curator policy. Studio's loopback bearer token is not a public multi-tenant identity and authorization service. Sandbox untrusted media and Python handlers before public deployment.
6. **No production performance proof:** local unit/integration tests do not establish general scientific accuracy, multimodal inference quality, full Windows/DeepSeek compatibility, distributed scale, or production threat resistance.

Source search/indexing works independently of training. Train only after verified rights, reviewed immutable datasets and independent held-out evaluations. Any promotion or deployment remains a separate approved action.
