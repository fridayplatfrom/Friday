# Tiny Expert System

A local **non-LLM** system that combines small supervised neural classifiers, source retrieval, explicit rules, taxonomic graphs, and numerical/symbolic tools. This repository is the corrected development baseline from the original uploaded project.

**Status: research prototype, version 0.2.** The code registers 24 built-in components; most are bounded reference/rule modules, not trained neural networks. Complete reviewed-data model bundles can activate pathology, routing, and leaf classification. Additional text classifiers can be registered through the same interface. No general language model is required or called by the default workflow.

## What this version corrects

- Whole-term routing avoids `ant` inside `quantum`, `sea` inside `research`, and unrelated safety/biology fallbacks. Unsupported questions are explicit.
- A missing, incompatible, experimental, corrupted, or zero-feature text model abstains. Legacy raw checkpoints and randomly initialized image heads are not silently used.
- Text hints are labelled as hints; image scores are never raised to an artificial minimum. Scores remain uncalibrated.
- Pathology produces candidates or condition references. Negative/healthy descriptions are conservatively withheld from this limited lexical classifier. A guessed label does not generate treatment instructions.
- Real upstream component results and taxonomy reach downstream components. The explanation lists execution events after evidence tools finish; it does not simulate an LLM thinking process or claim global verification.
- Calculations validate inputs and units. Symbolic expressions use an allowlisted parser and bounded subprocess, without evaluating user Python code.
- Unknown toxicity remains unknown. Missing weather stays missing; handwritten risk scores are not called outbreak probabilities.
- Source imports preserve supplied metadata and explicitly remain unreviewed. Replacing a document removes stale passages and refreshes retrieval. Unknown shelves fail clearly.
- Sessions have separate memory and start without fabricated personal facts. Automatic web harvesting is off by default.
- The web server binds to loopback, bounds request/image size, rejects foreign origins/hosts, and serializes shared state changes. Result text is rendered without interpolating it into executable HTML.
- Reusable training now provides grouped train/validation/test splits, a train-only vocabulary, best-checkpoint selection, every head's metrics, hashes, and complete inference bundles.

## Install

Use Python 3.11 or newer; this revision was tested on Python 3.12 with CPU PyTorch. Create your own environment—the original Windows `.venv` is not included.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1

# CPU wheels on supported Linux/Windows systems:
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[dev,documents]'
```

On macOS, install `torch torchvision` from the normal package index instead of the Linux/Windows CPU index. GPU configuration is optional and is not needed for the small text classifiers.

## Run

```bash
python demo.py
python web_app.py --port 8000 --no-browser
python -m pytest
```

Open `http://127.0.0.1:8000` for the UI. This is a local application, not a public multi-user service.

```python
from tiny_experts import ComponentOrchestrator

system = ComponentOrchestrator()
print(system.process("mass=500 g acceleration=2"))
print(system.process("Explain CRISPR gene editing."))
print(system.process("The lab ruled out Fusarium wilt. My plant is healthy."))
```

Mutable imports, indexes, and conversation state use `TINY_EXPERT_STATE_DIR` when set, or `~/.local/share/tiny-expert-system`. Tests always use temporary stores. Call `reset_session(session_id)` to clear the specified conversation and its scoped persistent memory.

## Import books and source text

```bash
python import_book.py /path/to/source.pdf --shelf genetics --title 'Actual source title' --author 'Actual author'
```

PDF, EPUB, DOCX, TXT, Markdown and supported JSON inputs are handled by the importer. Supply actual bibliographic details when known; unknown fields remain unknown. The importer accepts `--document-id`, `--publisher`, `--year`, `--edition`, `--source-url`, `--license` and `--pages`.

**Importing a document makes its passages searchable. It does not train model parameters.** A catalog entry also does not mean the full book is present. The bundled snippets are labelled unverified demonstration notes, not authenticated copies of the named textbooks.

## Train neural classifiers

Read [the training guide](docs/TRAINING.md) for the exact JSONL schemas and reviewed-data workflow.

A quick check using the old pathology examples:

```bash
python train_pathology_expert.py --export-demo training/private/pathology_legacy_demo.jsonl
python train_pathology_expert.py --demo --epochs 2 --output runs/pathology-demo
```

This trains a real neural network but produces an **experimental** bundle. The 165 handwritten legacy inputs are not an independent disease benchmark; the result is disabled in normal inference.

Train a reviewed pathology dataset:

```bash
python train_pathology_expert.py --data training/private/pathology_reviewed.jsonl --output tiny_experts/data/models/pathology
```

Train another categorical task with the same framework:

```bash
python train_expert.py --config training/configs/genetics_topics.json --data training/private/genetics_reviewed.jsonl --output tiny_experts/data/models/genetics_topics
```

Then register the complete bundle:

```python
system.register_neural_component(
    "genetics_topics",
    "tiny_experts/data/models/genetics_topics",
    shelf="genetics",
    keywords=["transcription", "mutation", "crispr"],
)
```

The generic adapter returns predicted labels and passages retrieved from the original question. It does not generate an unrestricted explanation or certify that a passage supports a label. A grammar edit model, extractive reader, retriever and image classifier need different task-specific datasets/architectures; a topic classifier is not a substitute for those tasks.

## Repository map

| Path | Purpose |
|---|---|
| `tiny_experts/orchestrator.py` | Local workflow, execution log, session handling and component registration |
| `tiny_experts/router.py` | Whole-term rules and optional packaged neural routing |
| `tiny_experts/components/` | Named reference lookups, calculators, renderers and neural adapters; `experts/` retains compatibility imports |
| `tiny_experts/neural/` | Shared feature extraction, model loading, grouped splits, training and metrics |
| `tiny_experts/pipeline/` | Source indexes, ingestion, scoped memory, graphs, constraints and symbolic calculation |
| `training/configs/` | Pathology, router and example genetics task definitions |
| `tests/regression/` | Current verification gates, including actual CPU training |
| `tests/legacy/` | Original historical assertions; not the current correctness gate |
| `docs/` | Training instructions, validation record, known limitations and roadmap |

The publication excludes the old virtual environment, generated databases, self-labelled SFT export, unvalidated raw weights, synthetic leaf fixtures and falsely attributed figure assets. They remain in the original upload; they are not used as a reviewed training corpus here.

## Limits and next work

This correction establishes a safer, testable foundation; it does not validate all scientific content or make the system an autonomous scientific authority. Legacy subject prose needs independent review. Numeric tools accept a documented, limited input grammar. The current text network uses word/bigram counts and has limited semantic generalization. No calibrated probabilities, validated field diagnostic model, unrestricted book reader, general grammar corrector or 1,000-expert deployment is claimed.

See [known limitations](docs/KNOWN_LIMITATIONS.md), [validation](docs/VALIDATION.md), and [the staged roadmap](docs/ROADMAP.md). Expand one measurable task at a time and promote a model only after inspecting independent errors and rejection behavior.

## Component names and indirect extraction

See [the component catalog](docs/COMPONENT_NAMING.md) for canonical Python names
and [the complete atlas](docs/EXPERT_ATLAS.md) for the registry. Reference lookups,
calculators, renderers and extraction services are distinguished from neural
classifiers. The Leech Source Extractor harvests source candidates; its dictionary
pattern count does not mean dictionary entries were learned or neural weights
updated. The Dictionary Lookup Service searches stored lexical entries.

Harness now combines relevant components and reports their contributions and
bounded cross-checks. See [coordinated answers](docs/COORDINATED_ANSWERS.md).
