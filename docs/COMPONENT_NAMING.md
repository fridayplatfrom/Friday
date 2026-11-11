# Component naming and compatibility

Canonical names describe implementation, not accuracy. A neural adapter is Python glue that may load a trained bundle; it is not itself a guarantee of learned expertise.

## Registered components

| Route key | Canonical class | Mechanism | Legacy class |
|---|---|---|---|
| `vision` | `VisionClassifierAdapter` | neural adapter | `VisionExpert` |
| `botany` | `BotanyReferenceLookup` | reference lookup | `BotanyExpert` |
| `wildlife` | `WildlifeReferenceLookup` | reference lookup | `WildlifeExpert` |
| `toxicity` | `ToxicityReferenceLookup` | reference lookup | `ToxicityExpert` |
| `biology` | `BiologyReferenceLookup` | reference lookup | `BiologyExpert` |
| `genetics` | `GeneticsReferenceLookup` | reference lookup | `GeneticsExpert` |
| `cell_biology` | `CellBiologyReferenceLookup` | reference lookup | `CellBiologyExpert` |
| `mycology` | `MycologyReferenceLookup` | reference lookup | `MycologyExpert` |
| `entomology` | `EntomologyReferenceLookup` | reference lookup | `EntomologyExpert` |
| `ornithology` | `OrnithologyReferenceLookup` | reference lookup | `OrnithologyExpert` |
| `ecology` | `EcologyReferenceLookup` | reference lookup | `EcologyExpert` |
| `pathology` | `PathologyCandidateAdapter` | hybrid adapter | `PathologyExpert` |
| `marine` | `MarineBiologyReferenceLookup` | reference lookup | `MarineBiologyExpert` |
| `microbiology` | `MicrobiologyReferenceLookup` | reference lookup | `MicrobiologyExpert` |
| `evolution` | `EvolutionReferenceLookup` | reference lookup | `EvolutionaryBiologyExpert` |
| `math` | `MathCalculator` | symbolic tool | `MathExpert` |
| `communicator` | `ResultRenderer` | renderer | `CommunicatorExpert` |
| `librarian` | `BookCatalogLookup` | catalog lookup | `LibrarianExpert` |
| `review` | `ReviewRecordLookup` | catalog lookup | `ReviewExpert` |
| `thermodynamics` | `ThermodynamicsCalculator` | symbolic tool | `ThermodynamicsExpert` |
| `electronics` | `CircuitCalculator` | symbolic tool | `ElectronicsExpert` |
| `mechanics` | `MechanicsCalculator` | symbolic tool | `MechanicsExpert` |
| `biographer` | `BiographyLookup` | catalog lookup | `BiographerExpert` |
| `format` | `OutputFormatter` | formatter | `FormatExpert` |

Import these classes from `tiny_experts.components`. `ComponentOrchestrator` uses the `components` mapping and exposes `register_neural_component`. `TinyExpertOrchestrator`, `experts`, `register_neural_expert` and the old module imports remain compatibility aliases. The old import module and the canonical module are the same object, so existing patch targets keep working.

## Source extraction and dictionary work

- **Leech Source Extractor**: `TrainingDirector.extract_source_candidates` and `POST /api/director/extract-source-candidates`. Extracts formula candidates, detects dictionary/biography patterns and routes figure candidates. No neural model or weight update occurs.
- **Dictionary Lookup Service**: `tiny_experts.pipeline.dictionary_lookup.DictionaryLookupService`. Loads existing lexical entries and searches with exact/substring matching and token-overlap ranking. It does not learn definitions from books.
- `dictionary_patterns_detected` counts pattern matches. `dictionary_entries_added` is currently zero. `formula_candidates_stored` counts persisted candidates, not validated laws.
- The old `run_leech_bus`, `/api/director/leech-bus`, `leech_bus` and `*_leeched` fields remain compatibility aliases. SQLite table/column names stay stable to preserve existing local stores.

## Neural and routing names

`CapabilityRouter` combines explicit rules with the optional `NeuralRoutingClassifier`. `RouterModel` and `NeuralMoERouter` are legacy aliases; this is not a transformer mixture-of-experts architecture. Existing model heads, bundle IDs, hashes and checkpoint filenames are unchanged. Neural classifier architectures remain explicitly named neural; training quality must be evaluated separately.

## Catalog and UI

Catalog schema 1.1 uses `component` and `task_component` kinds. Historical `expert.*` and `task_specialist.*` IDs remain stable identifiers, not claims of neural expertise. Legacy search filters are accepted. `describe_components` reports component type, whether it can use a neural model, whether a bundle is available, and whether inference updates parameters. The web UI builds its component list from this runtime status instead of advertising hardcoded neural capabilities.

No existing scientific content or training metric is validated by this naming change.
