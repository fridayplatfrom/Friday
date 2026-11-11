# Component and Neural Model Catalog

Names describe implemented work. The 24 registered components are not 24 neural networks.

Neural adapters load models; reference lookups, calculators, renderers, extractors and stores do not become neural models because they consume model output. Stable IDs retain their historical prefixes for compatibility.

## Indirect source extraction

The **Leech Source Extractor** harvests formula candidates and routes figure candidates from imported passages. It counts dictionary and biography patterns; it currently does not insert dictionary entries or update model parameters. The **Dictionary Lookup Service** searches the stored dictionary using lexical matching. Neither is a neuron or a trained neural dictionary learner.

## Inventory

### Component (24)

- **Result Renderer** — `expert.communicator`. Converts completed structured results into deterministic prose.
- **Output Formatter** — `expert.format`. Formats structured results as cards or JSON.
- **Biology Reference Lookup** — `expert.biology`. Selects stored biology explanations and retrieves passages.
- **Botany Reference Lookup** — `expert.botany`. Matches plant records and reference passages using explicit rules.
- **Cell Biology Reference Lookup** — `expert.cell_biology`. Selects stored cell-biology explanations and retrieves passages.
- **Ecology Reference Lookup** — `expert.ecology`. Selects stored ecology explanations and retrieves passages.
- **Entomology Reference Lookup** — `expert.entomology`. Selects stored insect explanations and retrieves passages.
- **Evolution Reference Lookup** — `expert.evolution`. Selects stored evolution explanations and retrieves passages.
- **Genetics Reference Lookup** — `expert.genetics`. Selects stored genetics explanations and retrieves passages; this module is not the optional genetics neural classifier.
- **Marine Biology Reference Lookup** — `expert.marine`. Selects stored marine-biology explanations and retrieves passages.
- **Microbiology Reference Lookup** — `expert.microbiology`. Selects stored microbiology explanations and retrieves passages.
- **Mycology Reference Lookup** — `expert.mycology`. Selects stored fungi explanations and retrieves passages.
- **Ornithology Reference Lookup** — `expert.ornithology`. Selects stored bird explanations and retrieves passages.
- **Plant Pathology Candidate Adapter** — `expert.pathology`. Combines an optional neural classifier, condition-reference rules and retrieval; candidates are not confirmed diagnoses.
- **Toxicity Reference Lookup** — `expert.toxicity`. Looks up toxicity references and applies conservative safety rules.
- **Wildlife Reference Lookup** — `expert.wildlife`. Matches animal records and reference passages using explicit rules.
- **Circuit Calculator** — `expert.electronics`. Calculates supported ideal resistor and RC circuit quantities.
- **Math Calculator** — `expert.math`. Runs deterministic arithmetic, unit conversion and bounded symbolic calculations.
- **Mechanics Calculator** — `expert.mechanics`. Parses supported mechanical quantities and applies numerical and symbolic formulas.
- **Thermodynamics Calculator** — `expert.thermodynamics`. Parses supported thermal quantities and applies numerical and symbolic formulas.
- **Biography Lookup** — `expert.biographer`. Searches stored person and invention records.
- **Book Catalog Lookup** — `expert.librarian`. Searches bibliographic metadata; catalog membership does not imply full text is available.
- **Review Record Lookup** — `expert.review`. Retrieves stored reviews and applies explicit comparison rules; does not establish scientific consensus.
- **Vision Classifier Adapter** — `expert.vision`. Loads optional neural image classifiers and performs explicit text entity lookup.

### Harness Tool (9)

- **Browser Workflow Tool** — `harness_tool.expertos_browser_workflow`. Browser Workflow Tool; typed integration endpoint, not a neural model.
- **Component Catalog Tool** — `harness_tool.expertos_experts`. Component Catalog Tool; typed integration endpoint, not a neural model.
- **Form Map Tool** — `harness_tool.expertos_form_map`. Form Map Tool; typed integration endpoint, not a neural model.
- **Form Verify Tool** — `harness_tool.expertos_form_verify`. Form Verify Tool; typed integration endpoint, not a neural model.
- **Plan Tool** — `harness_tool.expertos_plan`. Plan Tool; typed integration endpoint, not a neural model.
- **Propose Action Tool** — `harness_tool.expertos_propose_action`. Propose Action Tool; typed integration endpoint, not a neural model.
- **Read Source Tool** — `harness_tool.expertos_read_source`. Read Source Tool; typed integration endpoint, not a neural model.
- **Recover Tool** — `harness_tool.expertos_recover`. Recover Tool; typed integration endpoint, not a neural model.
- **Route Tool** — `harness_tool.expertos_route`. Route Tool; typed integration endpoint, not a neural model.

### Neural Model (5)

- **Neural Image Classifier Architecture** — `neural_model.leaf_vision`. Neural Image Classifier Architecture; learned weights require a compatible bundle, and architecture presence does not establish accuracy.
- **Neural Extractive Reader Architecture** — `neural_model.passage_reader`. Neural Extractive Reader Architecture; learned weights require a compatible bundle, and architecture presence does not establish accuracy.
- **Neural Pathology Classifier Architecture** — `neural_model.pathology_classifier`. Neural Pathology Classifier Architecture; learned weights require a compatible bundle, and architecture presence does not establish accuracy.
- **Neural Routing Classifier Architecture** — `neural_model.router`. Neural Routing Classifier Architecture; learned weights require a compatible bundle, and architecture presence does not establish accuracy.
- **Neural Text Classifier Architecture** — `neural_model.text_classifier`. Neural Text Classifier Architecture; learned weights require a compatible bundle, and architecture presence does not establish accuracy.

### Planned (7)

- **Autonomous Browser Agent (Planned)** — `planned.autonomous_browser_agent`. Autonomous Browser Agent: not implemented. See referenced source for its exact contract.
- **Coding Test Repair (Planned)** — `planned.coding_test_repair`. Coding Test Repair: not implemented. See referenced source for its exact contract.
- **Desktop Computer Agent (Planned)** — `planned.desktop_computer_agent`. Desktop Computer Agent: not implemented. See referenced source for its exact contract.
- **General Code Generator (Planned)** — `planned.general_code_generator`. General Code Generator: not implemented. See referenced source for its exact contract.
- **Independent Pathology Benchmark (Planned)** — `planned.independent_pathology_benchmark`. Independent Pathology Benchmark: not implemented. See referenced source for its exact contract.
- **Robust Task Planner (Planned)** — `planned.robust_task_planner`. Robust Task Planner: not implemented. See referenced source for its exact contract.
- **Scientific Entailment (Planned)** — `planned.scientific_entailment`. Scientific Entailment: not implemented. See referenced source for its exact contract.

### Support Service (45)

- **Passage Contradiction Heuristic** — `support_service.automated_contradiction_engine`. Passage Contradiction Heuristic; supporting Python service, not a trained neural expert.
- **Reference Consensus Ranker** — `support_service.consensus_ranking_engine`. Reference Consensus Ranker; supporting Python service, not a trained neural expert.
- **Stored Contradiction Lookup** — `support_service.contradiction_detector`. Stored Contradiction Lookup; supporting Python service, not a trained neural expert.
- **Training Corpus Validator** — `support_service.corpus_validation`. Training Corpus Validator; supporting Python service, not a trained neural expert.
- **Result Rule Checker** — `support_service.critic`. Result Rule Checker; supporting Python service, not a trained neural expert.
- **Stored Perspective Comparator** — `support_service.debate_engine`. Stored Perspective Comparator; supporting Python service, not a trained neural expert.
- **Source Figure Extractor** — `support_service.figure_extractor`. Source Figure Extractor; supporting Python service, not a trained neural expert.
- **Review Catalog Search** — `support_service.review_engine`. Review Catalog Search; supporting Python service, not a trained neural expert.
- **Visual Reference Catalog** — `support_service.visual_reference_atlas`. Visual Reference Catalog; supporting Python service, not a trained neural expert.
- **BM25 Passage Ranker** — `support_service.bm25`. BM25 Passage Ranker; supporting Python service, not a trained neural expert.
- **Bibliographic Catalog Search** — `support_service.book_catalog_engine`. Bibliographic Catalog Search; supporting Python service, not a trained neural expert.
- **FTS/BM25 Passage Retrieval** — `support_service.book_engine`. FTS/BM25 Passage Retrieval; supporting Python service, not a trained neural expert.
- **Book Import and Dataset Workflow** — `support_service.book_workflow`. Book Import and Dataset Workflow; supporting Python service, not a trained neural expert.
- **Dataset Export Service** — `support_service.dataset_exporter`. Dataset Export Service; supporting Python service, not a trained neural expert.
- **Document Text Importer** — `support_service.ingestion`. Document Text Importer; supporting Python service, not a trained neural expert.
- **SQLite Full-Text Index** — `support_service.sqlite_fts_engine`. SQLite Full-Text Index; supporting Python service, not a trained neural expert.
- **Biography Catalog Search** — `support_service.biography_engine`. Biography Catalog Search; supporting Python service, not a trained neural expert.
- **SVG Diagram Renderer** — `support_service.diagram_engine`. SVG Diagram Renderer; supporting Python service, not a trained neural expert.
- **Dictionary Lookup Service** — `support_service.lexicon_engine`. Dictionary Lookup Service; supporting Python service, not a trained neural expert.
- **Archived Market Reference Lookup** — `support_service.market_economics_engine`. Archived Market Reference Lookup; supporting Python service, not a trained neural expert.
- **Source Record Schema** — `support_service.schema`. Source Record Schema; supporting Python service, not a trained neural expert.
- **Context Risk Heuristic** — `support_service.bayesian_calibrator`. Context Risk Heuristic; supporting Python service, not a trained neural expert.
- **Biochemical Pathway Reference Lookup** — `support_service.biochemical_engine`. Biochemical Pathway Reference Lookup; supporting Python service, not a trained neural expert.
- **Bounded Symbolic Calculator** — `support_service.cas_engine`. Bounded Symbolic Calculator; supporting Python service, not a trained neural expert.
- **Diagnostic Procedure Reference Lookup** — `support_service.diagnostic_tree_engine`. Diagnostic Procedure Reference Lookup; supporting Python service, not a trained neural expert.
- **Disease Context Rule Checker** — `support_service.disease_triangle_engine`. Disease Context Rule Checker; supporting Python service, not a trained neural expert.
- **Quantity and Unit Parser** — `support_service.quantity_parser`. Quantity and Unit Parser; supporting Python service, not a trained neural expert.
- **Taxonomy Graph Lookup** — `support_service.taxonomic_graph`. Taxonomy Graph Lookup; supporting Python service, not a trained neural expert.
- **Concept Connection Lookup** — `support_service.universal_concept_graph`. Concept Connection Lookup; supporting Python service, not a trained neural expert.
- **Template Narrative Renderer** — `support_service.conversational_synthesizer`. Template Narrative Renderer; supporting Python service, not a trained neural expert.
- **Dependency Execution Scheduler** — `support_service.dag_orchestrator`. Dependency Execution Scheduler; supporting Python service, not a trained neural expert.
- **Scoped Observation Store** — `support_service.episodic_memory`. Scoped Observation Store; supporting Python service, not a trained neural expert.
- **Vernacular Alias Normalizer** — `support_service.multilingual_normalizer`. Vernacular Alias Normalizer; supporting Python service, not a trained neural expert.
- **Execution Log Renderer** — `support_service.reasoning_engine`. Execution Log Renderer; supporting Python service, not a trained neural expert.
- **Session Context Store** — `support_service.session_memory`. Session Context Store; supporting Python service, not a trained neural expert.
- **Archived Guide Lookup** — `support_service.blog_engine`. Archived Guide Lookup; supporting Python service, not a trained neural expert.
- **Chemical Reference Registry** — `support_service.chemical_regulatory_registry`. Chemical Reference Registry; supporting Python service, not a trained neural expert.
- **Opt-In Source Harvester** — `support_service.harvester`. Opt-In Source Harvester; supporting Python service, not a trained neural expert.
- **Archived News and Temporal Fact Lookup** — `support_service.news_engine`. Archived News and Temporal Fact Lookup; supporting Python service, not a trained neural expert.
- **Bounded Public Source Fetcher** — `support_service.source_fetch`. Bounded Public Source Fetcher; supporting Python service, not a trained neural expert.
- **Toxicology Reference Connector** — `support_service.toxicology_connector`. Toxicology Reference Connector; supporting Python service, not a trained neural expert.
- **Media Demonstration Catalog** — `support_service.video_audio_ingestor`. Media Demonstration Catalog; supporting Python service, not a trained neural expert.
- **Website Directory Lookup** — `support_service.web_directory_engine`. Website Directory Lookup; supporting Python service, not a trained neural expert.
- **Local Reference Record Store** — `support_service.knowledge_store`. Local Reference Record Store; supporting Python service, not a trained neural expert.
- **Leech Source Extractor** — `support_service.source_candidate_extractor`. Extracts formula candidates, counts dictionary and biography patterns, and routes figure candidates from imported passages. Does not train neural weights or add dictionary definitions.

### Task Component (8)

- **Optional Neural Browser Action Classifier** — `task_specialist.browser_action_policy`. Optional Neural Browser Action Classifier; bounded integration component, not an autonomous general expert.
- **Rule-Based Browser Planner** — `task_specialist.browser_planner`. Rule-Based Browser Planner; bounded integration component, not an autonomous general expert.
- **Browser Field Value Verifier** — `task_specialist.browser_verifier`. Browser Field Value Verifier; bounded integration component, not an autonomous general expert.
- **Accessible Label Form Mapper** — `task_specialist.form_mapper`. Accessible Label Form Mapper; bounded integration component, not an autonomous general expert.
- **Pathology Reference Adapter** — `task_specialist.pathology_reference`. Pathology Reference Adapter; bounded integration component, not an autonomous general expert.
- **Browser Failure Rule Handler** — `task_specialist.recovery`. Browser Failure Rule Handler; bounded integration component, not an autonomous general expert.
- **Rule-Based Browser Task Router** — `task_specialist.router`. Rule-Based Browser Task Router; bounded integration component, not an autonomous general expert.
- **Source Passage Retrieval Adapter** — `task_specialist.source_reader`. Source Passage Retrieval Adapter; bounded integration component, not an autonomous general expert.

