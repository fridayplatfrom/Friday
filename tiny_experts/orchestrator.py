import time
import re
from typing import Any, Dict, Optional, List, Tuple
from .router import CapabilityRouter
from .matching import contains_term
from .neural.neural_router import NeuralRoutingClassifier
from .pipeline.book_engine import BookEngine
from .pipeline.knowledge_store import KnowledgeStore
from .pipeline.harvester import ScientificDataHarvester
from .pipeline.session_memory import SessionMemory
from .pipeline.reasoning_engine import ReasoningEngine
from .pipeline.critic import ScientificCritic
from .pipeline.taxonomic_graph import TaxonomicKnowledgeGraph
from .pipeline.biochemical_engine import BiochemicalEngine
from .pipeline.bayesian_calibrator import BayesianCalibrator
from .pipeline.episodic_memory import EpisodicMemory
from .pipeline.multilingual_normalizer import MultilingualVernacularNormalizer
from .pipeline.conversational_synthesizer import ConversationalSynthesizer
from .pipeline.news_engine import NewsEngine
from .pipeline.blog_engine import BlogWebEngine
from .pipeline.video_audio_ingestor import VideoAudioIngestor
from .pipeline.market_economics_engine import MarketEconomicsEngine
from .pipeline.diagnostic_tree_engine import DiagnosticTreeEngine
from .pipeline.book_catalog_engine import BookCatalogEngine
from .pipeline.review_engine import EpistemicReviewEngine
from .pipeline.contradiction_detector import DialecticContradictionDetector
from .pipeline.universal_concept_graph import UniversalConceptGraph
from .pipeline.biography_engine import BiographyEngine
from .pipeline.dictionary_lookup import DictionaryLookupService
from .pipeline.consensus_ranking_engine import ConsensusRankingEngine
from .pipeline.web_directory_engine import UniversalWebDirectoryEngine
from .pipeline.dag_orchestrator import TopologicalDAGOrchestrator
from .pipeline.automated_contradiction_engine import AutomatedContradictionEngine
from .pipeline.diagram_engine import DiagramEngine
from .pipeline.cas_engine import SymbolicCASEngine
from .components import (
    VisionClassifierAdapter,
    BotanyReferenceLookup,
    WildlifeReferenceLookup,
    ToxicityReferenceLookup,
    BiologyReferenceLookup,
    GeneticsReferenceLookup,
    CellBiologyReferenceLookup,
    MycologyReferenceLookup,
    EntomologyReferenceLookup,
    OrnithologyReferenceLookup,
    EcologyReferenceLookup,
    PathologyCandidateAdapter,
    MarineBiologyReferenceLookup,
    MicrobiologyReferenceLookup,
    EvolutionReferenceLookup,
    MathCalculator,
    ResultRenderer,
    BookCatalogLookup,
    ReviewRecordLookup,
    ThermodynamicsCalculator,
    CircuitCalculator,
    MechanicsCalculator,
    BiographyLookup,
    OutputFormatter
)

PHYSICS_CONCEPT_INTENT_RULES: List[Tuple[str, str, str, str]] = [
    # 1. Fundamental Kinematics & Motion
    (r"(?:what\s+is\s+|explain\s+|define\s+)?(?:motion\b|types\s+of\s+motion|kinematics\b)|(?:rectilinear|translational)\s+motion", "classical_mechanics", "motion", "lagrangian_variational"),
    (r"diff(?:erence)?\s+between\s+distance\s+and\s+displacement|distance\s+(?:vs\.?|versus)\s+displacement", "classical_mechanics", "distance_and_displacement", "rigid_body_rotational"),
    (r"diff(?:erence)?\s+between\s+speed\s+and\s+velocity|speed\s+(?:vs\.?|versus)\s+velocity", "classical_mechanics", "speed_vs_velocity", "rigid_body_rotational"),
    (r"(?:what\s+is\s+|explain\s+|define\s+)?acceleration\b|rate\s+of\s+change\s+of\s+velocity", "classical_mechanics", "acceleration", "lagrangian_variational"),
    (r"equations?\s+of\s+motion|kinematic\s+equations?|\bv\s*=\s*u\s*\+\s*a\s*t\b", "classical_mechanics", "equations_of_motion", "lagrangian_variational"),
    (r"free\s*fall|acceleration\s+due\s+to\s+gravity|\bg\s*=\s*9\.8", "classical_mechanics", "free_fall", "lagrangian_variational"),
    (r"projectile\s+motion|trajectory\s+of\s+a\s+projectile|range\s+of\s+a\s+projectile", "classical_mechanics", "projectile_motion", "rigid_body_rotational"),
    (r"centripetal\s+acceleration|circular\s+motion|centripetal\s+force", "classical_mechanics", "centripetal_acceleration", "rigid_body_rotational"),

    # 2. Newton's Laws & Dynamics
    (r"(?:newton'?s?\s+)?third\s+law|(?:3rd|third)\s+law\s+of\s+newton|action\s+(?:and|&)\s+reaction|action\s*[-–]\s*reaction", "classical_mechanics", "newton_third_law", "lagrangian_variational"),
    (r"(?:newton'?s?\s+)?first\s+law|\blaw\s+of\s+inertia\b|\binertia\b", "classical_mechanics", "newton_first_law", "lagrangian_variational"),
    (r"(?:newton'?s?\s+)?second\s+law|\bF\s*=\s*m\s*a\b", "classical_mechanics", "newton_second_law", "lagrangian_variational"),
    (r"conservation\s+of\s+momentum|momentum\s+conservation|\blinear\s+momentum\b|\bimpulse\b", "classical_mechanics", "conservation_of_momentum", "lagrangian_variational"),
    (r"work\s+energy\s+theorem|work\s+and\s+energy", "classical_mechanics", "work_energy_theorem", "lagrangian_variational"),
    (r"conservation\s+of\s+energy|mechanical\s+energy\s+conservation", "classical_mechanics", "conservation_of_energy", "lagrangian_variational"),
    (r"(?:what\s+is\s+|explain\s+)?friction\b|static\s+friction|kinetic\s+friction", "classical_mechanics", "friction", "lagrangian_variational"),
    (r"simple\s+harmonic\s+motion|\bshm\b|hooke'?s?\s+law|restoring\s+force", "classical_mechanics", "simple_harmonic_motion", "hamiltonian_symplectic"),
    (r"torque\b|moment\s+of\s+inertia|rotational\s+dynamics|angular\s+acceleration", "classical_mechanics", "torque_and_rotational_motion", "rigid_body_rotational"),

    # 3. Gravitation & Planetary Laws (including Kepler's 3rd Law & Newton's Gravity)
    (r"(?:3rd|third)\s+law\s+of\s+gravity|kepler'?s?\s+(?:3rd|third)\s+law|kepler'?s?\s+laws?|harmonic\s+law", "classical_mechanics", "third_law_of_gravity", "lagrangian_variational"),
    (r"(?:what\s+is\s+|explain\s+)?(?:gravity\b|gravitation\b)|universal\s+gravitation|law\s+of\s+gravity|gravitational\s+(?:force|field|attraction)", "classical_mechanics", "universal_gravitation", "lagrangian_variational"),
    (r"escape\s+velocity|orbital\s+velocity|satellite\s+motion", "classical_mechanics", "escape_and_orbital_velocity", "lagrangian_variational"),

    # 4. Fluids & Buoyancy
    (r"archimedes|buoyan|float\w*\s+in\s+water|displaced\s+fluid", "fluid_plasma", "archimedes_principle", "incompressible_flow"),
    (r"bernoulli|lift\s+on\s+an\s+airplane\s+wing|fluid\s+streamline", "fluid_plasma", "bernoulli_principle", "incompressible_flow"),
    (r"pascal'?s?\s+principle|hydraulic\s+press|fluid\s+pressure", "fluid_plasma", "pascals_principle", "incompressible_flow"),

    # 5. Thermodynamics & Heat
    (r"zeroth\s+law\s+of\s+thermodynamics|thermal\s+equilibrium", "thermodynamics_stat_mech", "zeroth_law_thermodynamics", "free_energy_potentials"),
    (r"first\s+law\s+of\s+thermodynamics|\bdelta\s*u\s*=\s*q\s*-\s*w", "thermodynamics_stat_mech", "first_law_thermodynamics", "free_energy_potentials"),
    (r"second\s+law\s+of\s+thermodynamics|entropy\s+increase|carnot\s+engine", "thermodynamics_stat_mech", "second_law_thermodynamics", "free_energy_potentials"),
    (r"third\s+law\s+of\s+thermodynamics|absolute\s+zero\s+entropy", "thermodynamics_stat_mech", "third_law_thermodynamics", "free_energy_potentials"),
    (r"ideal\s+gas\s+law|\bp\s*v\s*=\s*n\s*r\s*t\b", "thermodynamics_stat_mech", "ideal_gas_law", "free_energy_potentials"),

    # 6. Waves, Optics & Light
    (r"why\s+(?:is\s+)?(?:the\s+)?sky\s+blue|rayleigh\s+scattering|blue\s+sky", "optics_waves", "rayleigh_scattering", "dispersive_polarization_wave"),
    (r"doppler(?:\s+effect|\s+shift)?", "optics_waves", "doppler_effect", "dispersive_polarization_wave"),
    (r"refraction|snell'?s?\s+law", "optics_waves", "snells_law_refraction", "dispersive_polarization_wave"),
    (r"total\s+internal\s+reflection|critical\s+angle", "optics_waves", "total_internal_reflection", "dispersive_polarization_wave"),
    (r"thin\s+lens|mirror\s+formula|lens\s+equation|\b1/f\s*=\s*1/d", "optics_waves", "thin_lens_equation", "geometric_ray_lens"),
    (r"dispersion\s+of\s+light|rainbow|prism\s+spectrum", "optics_waves", "dispersion_of_light", "dispersive_polarization_wave"),
    (r"(?:sound\s+waves?|speed\s+of\s+sound|pitch\s+and\s+loudness)", "optics_waves", "sound_waves", "dispersive_polarization_wave"),

    # 7. Electromagnetism & Circuits
    (r"(?:what\s+is\s+|explain\s+)?electric\s+current|flow\s+of\s+charge|drift\s+velocity", "electromagnetism", "electric_current", "electrostatic_gauss"),
    (r"coulomb'?s?\s+law|electrostatic\s+force", "electromagnetism", "coulombs_law", "electrostatic_gauss"),
    (r"electric\s+field|electric\s+potential\b|voltage\b", "electromagnetism", "electric_field_and_potential", "electrostatic_gauss"),
    (r"ohm'?s?\s+law|\bv\s*=\s*i\s*r\b|electrical\s+resistance", "electromagnetism", "ohms_law", "electrostatic_gauss"),
    (r"capacit\w+|stored\s+charge\s+in\s+capacitor|\bc\s*=\s*q/v\b", "electromagnetism", "capacitance", "electrostatic_gauss"),
    (r"faraday'?s?\s+law|electromagnetic\s+induction|lenz'?s?\s+law", "electromagnetism", "faradays_law", "electrodynamic_maxwell_wave"),
    (r"lorentz\s+force|magnetic\s+force\s+on\s+moving\s+charge|\bq\s*v\s*b\b", "electromagnetism", "lorentz_force", "electrodynamic_maxwell_wave"),
    (r"maxwell'?s?\s+equations?|unified\s+electromagnetism", "electromagnetism", "maxwell_equations", "electrodynamic_maxwell_wave"),

    # 8. Modern, Quantum & Relativity
    (r"photoelectric\s+effect|work\s+function", "quantum_mechanics", "photoelectric_effect", "hilbert_operator_algebra"),
    (r"wave\s*[-–]\s*particle\s+duality|de\s+broglie\s+wavelength", "quantum_mechanics", "wave_particle_duality", "wavefunction_schrodinger"),
    (r"heisenberg\s+uncertainty(?:\s+principle)?|uncertainty\s+principle", "quantum_mechanics", "heisenberg_uncertainty", "hilbert_operator_algebra"),
    (r"mass\s*[-–]\s*energy\s+equivalence|\be\s*=\s*m\s*c\s*\^?2\b", "relativity_cosmology", "mass_energy_equivalence", "minkowski_special_relativity"),
]


class ComponentOrchestrator:
    """Local expert workflows with explicit routing, retrieval and tool execution.

    No language model is used. Neural models must load a compatible reviewed-data
    bundle. Bundled prose is reference material, not verified case evidence.
    """

    def __init__(self, verbose: bool = False, allow_network: bool = False, enable_reference_feeds: bool = False, neural_router=None):
        if verbose:
            print("[SYSTEM] Initializing local expert workflows...")
        self.router = CapabilityRouter(neural_router if neural_router is not None else NeuralRoutingClassifier())
        self.allow_network = allow_network
        self.enable_reference_feeds = enable_reference_feeds
        self.book_engine = BookEngine()
        self.taxonomic_graph = TaxonomicKnowledgeGraph()
        self.episodic_memory = EpisodicMemory()
        self.sessions: Dict[str, SessionMemory] = {}
        
        # Partitioned Multi-Source Knowledge Engines (Strictly Sandboxed)
        self.news_engine = NewsEngine()
        self.blog_engine = BlogWebEngine()
        self.video_engine = VideoAudioIngestor()
        self.market_engine = MarketEconomicsEngine()
        self.diagnostic_tree_engine = DiagnosticTreeEngine()
        self.catalog_engine = BookCatalogEngine()
        self.review_engine = EpistemicReviewEngine()
        self.biography_engine = BiographyEngine()
        self.lexicon_engine = DictionaryLookupService()
        self.consensus_engine = ConsensusRankingEngine()
        self.web_directory_engine = UniversalWebDirectoryEngine()
        
        # Initialize complete suite of 24 bounded components
        self.components = {
            "vision": VisionClassifierAdapter(),
            "botany": BotanyReferenceLookup(book_engine=self.book_engine),
            "wildlife": WildlifeReferenceLookup(book_engine=self.book_engine),
            "toxicity": ToxicityReferenceLookup(book_engine=self.book_engine),
            "biology": BiologyReferenceLookup(book_engine=self.book_engine),
            "genetics": GeneticsReferenceLookup(book_engine=self.book_engine),
            "cell_biology": CellBiologyReferenceLookup(book_engine=self.book_engine),
            "mycology": MycologyReferenceLookup(book_engine=self.book_engine),
            "entomology": EntomologyReferenceLookup(book_engine=self.book_engine),
            "ornithology": OrnithologyReferenceLookup(book_engine=self.book_engine),
            "ecology": EcologyReferenceLookup(book_engine=self.book_engine),
            "pathology": PathologyCandidateAdapter(book_engine=self.book_engine),
            "marine": MarineBiologyReferenceLookup(book_engine=self.book_engine),
            "microbiology": MicrobiologyReferenceLookup(book_engine=self.book_engine),
            "evolution": EvolutionReferenceLookup(book_engine=self.book_engine),
            "math": MathCalculator(),
            "librarian": BookCatalogLookup(catalog_engine=self.catalog_engine),
            "review": ReviewRecordLookup(review_engine=self.review_engine),
            "thermodynamics": ThermodynamicsCalculator(book_engine=self.book_engine),
            "electronics": CircuitCalculator(book_engine=self.book_engine),
            "mechanics": MechanicsCalculator(book_engine=self.book_engine),
            "biographer": BiographyLookup(biography_engine=self.biography_engine),
            "communicator": ResultRenderer(book_engine=self.book_engine),
            "format": OutputFormatter()
        }
        self.experts = self.components  # Legacy mapping alias.
        if verbose:
            print(f"[SYSTEM] Registered {len(self.components)} components; neural availability depends on installed model bundles.\n")

    def _get_session(self, session_id: str) -> SessionMemory:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionMemory()
        return self.sessions[session_id]

    def register_neural_component(self, expert_id: str, bundle_dir, shelf: str, keywords):
        """Add a packaged bounded task. This does not train a model or add language generation."""
        from .components.neural_classification import NeuralClassificationAdapter
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", expert_id) or expert_id in self.components:
            raise ValueError("Choose a new lowercase component identifier.")
        if not isinstance(keywords, (list, tuple)) or not keywords or not all(isinstance(k, str) and k.strip() for k in keywords):
            raise ValueError("Provide nonempty routing keywords.")
        expert = NeuralClassificationAdapter(expert_id, bundle_dir, self.book_engine, shelf)
        if not expert.classifier.available:
            raise ValueError(f"Neural classifier bundle is unavailable: {expert.classifier.load_error}")
        self.components[expert_id] = expert
        self.router.intent_keywords[expert_id] = list(keywords)
        return expert

    register_neural_expert = register_neural_component  # Legacy method alias.

    def reset_session(self, session_id: str = "default_session") -> None:
        if session_id in self.sessions:
            self.sessions[session_id].clear()
        self.episodic_memory.clear_session(session_id)

    def process(
        self,
        query: str,
        image: Optional[Any] = None,
        hint_species: Optional[str] = None,
        session_id: str = "default_session",
        show_thinking: bool = True,
        output_format: str = "card"
    ) -> str:
        """
        Executes an end-to-end multi-expert reasoning cycle and returns formatted text.
        """
        detailed = self.process_detailed(
            query=query,
            image=image,
            hint_species=hint_species,
            session_id=session_id,
            show_thinking=show_thinking,
            output_format=output_format
        )
        return detailed["final_output"]

    def process_detailed(
        self,
        query: str,
        image: Optional[Any] = None,
        hint_species: Optional[str] = None,
        session_id: str = "default_session",
        show_thinking: bool = True,
        output_format: str = "card"
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end multi-expert reasoning cycle and returns structured telemetry.
        """
        if not isinstance(query, str) or len(query) > 16000:
            raise ValueError("Query must be text of at most 16,000 characters.")
        if not query.strip() and image is None:
            raise ValueError("Provide a question or an image.")
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            raise ValueError("Invalid session ID.")
        if output_format not in {"card", "json"}:
            raise ValueError("Output format must be card or json.")
        start_time = time.perf_counter()
        session = self._get_session(session_id)
        events = []
        errors = []

        def run_stage(stage, operation):
            try:
                result = operation()
                status = (result.get("status", "completed") if isinstance(result, dict)
                          else "completed" if result else "no_match")
                events.append({"stage": stage, "status": status, "detail": "Returned a result." if result else "No result matched."})
                return result
            except Exception as exc:
                # A failed expert cannot silently become a successful answer.
                detail = f"{type(exc).__name__}: {exc}"
                errors.append({"stage": stage, "error": detail})
                events.append({"stage": stage, "status": "error", "detail": detail})
                return None

        vernacular_meta = MultilingualVernacularNormalizer.normalize(query)
        effective_query = vernacular_meta["normalized_query"] if vernacular_meta["is_vernacular"] else query
        context_res = session.resolve_context(effective_query)
        effective_species = hint_species or context_res.get("resolved_species")
        was_context_resolved = bool(context_res.get("resolved_species") and not hint_species)
        if not effective_species:
            for entry in VisionClassifierAdapter.SPECIES_CATALOG:
                names = [entry["name"], entry["id"].replace("_", " "), entry["scientific"]]
                if any(contains_term(effective_query, name) for name in names):
                    effective_species = entry["name"]
                    break
        episodic_ctx = self.episodic_memory.retrieve_context_for_query(effective_query, session_id=session_id)
        active_keys = self.router.route(effective_query, has_image=image is not None, hint_species=effective_species)
        if vernacular_meta.get("canonical_disease") and "pathology" not in active_keys:
            active_keys.append("pathology")
        events.append({"stage": "routing", "status": "completed" if active_keys else "unsupported",
                       "detail": ", ".join(active_keys) if active_keys else "No registered capability matched the question."})
        aggregated = {"query": query, "normalized_query": effective_query, "vernacular_meta": vernacular_meta,
                      "episodic_context": episodic_ctx, "execution_events": events, "errors": errors,
                      "orchestration_meta": {"invoked_experts": active_keys, "latency_ms": 0,
                                             "autonomous_tool_called": False, "context_resolved": was_context_resolved,
                                             "execution_mode": "local_non_llm", "reference_data_reviewed": False}}
        detected_species = effective_species
        if "vision" in active_keys:
            result = run_stage("vision", lambda: self.components["vision"].evaluate(
                {"image": image, "hint_species": effective_species, "query": effective_query}))
            if result:
                aggregated["vision"] = result
                if result.get("detected"):
                    detected_species = result.get("species")
                    if result.get("category") == "plant_pathology" and "pathology" not in active_keys:
                        active_keys.append("pathology")
                    elif result.get("category") == "physics_diagram":
                        diag_id = result.get("diagram_id", "")
                        if diag_id == "carnot_pv_cycle" and "thermodynamics" not in active_keys:
                            active_keys.append("thermodynamics")
                        elif diag_id == "inclined_plane" and "mechanics" not in active_keys:
                            active_keys.append("mechanics")
                        elif diag_id == "parallel_circuit" and "electronics" not in active_keys:
                            active_keys.append("electronics")
        # Explicit network opt-in applies only to an explicit named subject.
        autonomous_tool_called = False
        if self.allow_network and hint_species and not KnowledgeStore.find(hint_species):
            record = run_stage("source_harvest", lambda: ScientificDataHarvester.harvest(hint_species))
            if record:
                KnowledgeStore.save(record, search_alias=hint_species)
                autonomous_tool_called = True
                aggregated["orchestration_meta"]["autonomous_tool_called"] = True
        if detected_species:
            taxa = run_stage("taxonomy", lambda: self.taxonomic_graph.get_inherited_traits(detected_species))
            if taxa and taxa.get("matched"):
                taxa["status"] = "reference_only"
                aggregated["taxonomic_lineage"] = taxa
        eval_context = {"query": effective_query, "species": detected_species or "", "image": image,
                        "vernacular_meta": vernacular_meta, "taxonomic_lineage": aggregated.get("taxonomic_lineage"),
                        "expert_results": {}}
        domain_keys = [key for key in active_keys if key in self.components and key not in {"vision", "communicator", "format"}]
        ordered = TopologicalDAGOrchestrator.compute_execution_order(domain_keys)
        aggregated["orchestration_meta"]["topological_order"] = ordered
        for key in ordered:
            result = run_stage(key, lambda key=key: self.components[key].evaluate(eval_context))
            if not isinstance(result, dict):
                continue
            result.setdefault("status", "reference_only")
            aggregated[key] = result
            eval_context["expert_results"][key] = result
            eval_context[f"{key}_info"] = result
            if result.get("svg_diagram") and not aggregated.get("svg_diagram"):
                aggregated["svg_diagram"] = result["svg_diagram"]
        if not domain_keys and image is None:
            aggregated["unsupported"] = {"status": "unsupported", "message": "No supported expert matched this question. Add a tested capability or provide a more specific task."}
        tool_results = [
            ("biochemical_pathway", lambda: BiochemicalEngine.evaluate(query=query, species_name=detected_species or "", chemical_name=aggregated.get("toxicity", {}).get("toxic_agent", ""))),
            ("bayesian_calibration", lambda: BayesianCalibrator.evaluate(query=query, detected_species=detected_species or "")),
            ("cross_disciplinary_bridges", lambda: UniversalConceptGraph.find_cross_connections(effective_query)),
        ]
        for key, operation in tool_results:
            result = run_stage(key, operation)
            if result:
                aggregated[key] = result
        detected_crop = vernacular_meta.get("canonical_crop") or ("Tomato" if contains_term(query, "tomato") else None)
        pathology = aggregated.get("pathology", {})
        condition = pathology.get("pathology_condition", "").split(" (")[0] if pathology.get("status") in {"candidate", "reference_only"} else None
        if condition:
            diagnostic = run_stage("diagnostic_procedure", lambda: self.diagnostic_tree_engine.get_in_field_test(condition=condition, crop=detected_crop, query=query))
            if diagnostic:
                aggregated["in_field_diagnostic_test"] = diagnostic
        # The optional feeds are archived reference examples, not live alerts.
        if self.enable_reference_feeds:
            feeds = [
                ("outbreak_alert", lambda: self.news_engine.evaluate_outbreaks(crop=detected_crop, pathogen=condition, query=query)),
                ("extension_blog", lambda: self.blog_engine.find_relevant_guide(crop=detected_crop, disease=condition, query=query)),
                ("field_demonstration", lambda: self.video_engine.find_demonstration(crop=detected_crop, disease=condition, query=query)),
                ("market_economics", lambda: self.market_engine.evaluate_viability(crop=detected_crop)),
            ]
            for key, operation in feeds:
                result = run_stage(key, operation)
                if result:
                    result = {**result, "status": "archived_reference", "freshness_verified": False}
                    aggregated[key] = result
        lang = vernacular_meta.get("detected_language", "en")
        lex_hit = run_stage("lexicon", lambda: self.lexicon_engine.lookup_term(effective_query, lang=lang))
        if lex_hit:
            aggregated["lexicon_definition"] = lex_hit
        passages = []
        for key in ordered:
            result = aggregated.get(key, {})
            citations = list(result.get("textbook_citations") or [])
            if result.get("textbook_citation") and not citations:
                citations.append(result["textbook_citation"])
            for citation in citations:
                if isinstance(citation, dict):
                    passages.append({"source": citation.get("source", key), "text": citation.get("text") or citation.get("excerpt", "")})
        if len(passages) >= 2:
            conflicts = run_stage("citation_conflicts", lambda: AutomatedContradictionEngine.discover_contradictions(passages=passages, query=effective_query))
            if conflicts and conflicts.get("contradiction_detected"):
                aggregated["automated_contradiction"] = conflicts
        aggregated["critic_audit"] = run_stage("rule_checks", lambda: ScientificCritic.audit_and_correct(aggregated=aggregated, query=query)) or {}
        communicator = run_stage("communicator", lambda: self.components["communicator"].evaluate({"query": query, "aggregated_results": aggregated})) or {}
        aggregated["communicator"] = communicator
        narrative = communicator.get("speech_synthesis", "")
        aggregated["human_narrative"] = narrative
        # Generate the explanation from stages that actually ran, after all evidence tools.
        thinking_trace = ReasoningEngine.generate_thinking_trace(query=query,
            resolved_species=detected_species if was_context_resolved else None,
            autonomous_tool_called=autonomous_tool_called, active_experts=active_keys, aggregated_data=aggregated)
        aggregated["thinking_trace"] = thinking_trace
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        aggregated["orchestration_meta"]["latency_ms"] = elapsed_ms
        formatted = self.components["format"].evaluate({"format": output_format, "aggregated_results": aggregated})
        rendered = formatted.get("rendered", "")
        final_output = f"{thinking_trace}\n\n{rendered}" if show_thinking and output_format == "card" else rendered
        category = aggregated.get("vision", {}).get("category")
        session.record_turn(query=query, response=rendered, meta={"species": detected_species, "category": category})
        if detected_species:
            self.episodic_memory.log_observation(organism_name=detected_species, category=category or "organism", notes=f"Query: {query}", session_id=session_id)
        return {"query": query, "session_id": session_id, "detected_species": detected_species, "category": category,
                "human_narrative": narrative, "thinking_trace": thinking_trace, "rendered_card": rendered,
                "final_output": final_output, "telemetry": aggregated, "latency_ms": elapsed_ms,
                "active_components": active_keys, "active_experts": active_keys, "autonomous_tool_called": autonomous_tool_called,
                "context_resolved": was_context_resolved, "turn_count": len(session.history),
                "svg_diagram": aggregated.get("svg_diagram")}


    def process_book_question(
        self, document_id: str, question: str, *,
        reader_bundle=None, allow_experimental: bool = False, top_k: int = 3,
        min_score: float = 0.03,
    ) -> Dict[str, Any]:
        """Typed document retrieval and optional neural answer-span prediction.

        Both source-matching and model predictions are explicitly separated
        from evidence entailment and clinical diagnostic validation.
        """
        from .neural.passage_reader import PassageReaderBundle
        if not isinstance(question, str) or not question.strip():
            raise ValueError("A nonempty question is required")
        if not isinstance(min_score, (int, float)) or not 0 <= min_score <= 1:
            raise ValueError("min_score must be in [0,1]")
        result = self.book_engine.lookup_document(document_id, question, top_k)
        trace = [{"action": "source_lookup", "status": result["status"],
                  "document_id": document_id, "retrieved": len(result["passages"])}]
        if result["status"] != "retrieved":
            return {"status": result["status"], "answer": None, "evidence": [], "execution_trace": trace}
        verified = []
        for item in result["passages"]:
            try:
                proof = self.book_engine.verify_passage(item["passage_id"])
            except (ValueError, OSError, UnicodeError) as error:
                trace.append({"action": "source_integrity", "status": "rejected", "reason": str(error)})
                continue
            verified.append((item, proof))
        if not verified:
            return {"status": "source_integrity_failure", "answer": None,
                    "evidence": [], "execution_trace": trace}
        trace.append({"action": "source_integrity", "status": "passed",
                      "verified_passages": len(verified)})
        evidence = [{"passage_id": p["passage_id"], "document_id": p["document_id"],
                     "text": p["text"], "source_revision": proof["source_revision"],
                     "source_consistency": True, "semantic_support": "not_evaluated"}
                    for p, proof in verified]
        if reader_bundle is None:
            return {"status": "evidence_only", "answer": None,
                    "evidence": evidence, "execution_trace": trace}
        reader = (reader_bundle if isinstance(reader_bundle, PassageReaderBundle)
                  else PassageReaderBundle(reader_bundle, allow_experimental=allow_experimental))
        if reader.manifest.get("experimental") and not allow_experimental:
            raise ValueError("Experimental neural reader is disabled")
        proposals = []
        for p, _ in verified:
            guess = reader.predict(question, p["text"], min_score=min_score)
            if guess["status"] != "experimental_answer":
                continue
            if p["text"][guess["start"]:guess["end"]] != guess["answer"]:
                continue
            proposals.append((guess, p))
        if not proposals:
            trace.append({"action": "neural_span_reader", "status": "abstained"})
            return {"status": "reader_abstained", "answer": None,
                    "evidence": evidence, "execution_trace": trace, "model_status": "experimental"}
        best, parent = max(proposals, key=lambda pair: pair[0]["score"])
        trace.append({"action": "neural_span_reader", "status": "experimental_prediction",
                      "score_type": best["score_type"]})
        return {"status": "experimental_answer", "answer": best["answer"],
                "answer_passage_id": parent["passage_id"], "confidence": None,
                "score": best["score"], "score_type": best["score_type"],
                "evidence": evidence, "execution_trace": trace, "model_status": "experimental",
                "limitation": "Extracted text span is model-predicted, not independently entailed or diagnostically validated."}

    def dispatch_physics_hierarchy(self, query: str, image: Optional[Any] = None) -> Dict[str, Any]:
        """Coordinate routing, calculation, references and bounded cross-checks."""
        from pathlib import Path
        from .neural.text_expert import NeuralTextClassifier

        models_dir = Path(__file__).resolve().parent / "data" / "models"
        intent_match = None
        for pat, sub_match, conc_match, reg_match in PHYSICS_CONCEPT_INTENT_RULES:
            if re.search(pat, query, re.IGNORECASE):
                intent_match = (sub_match, conc_match, reg_match)
                break

        if intent_match:
            subdomain, concept_override, regime_override = intent_match
            specialist_id = f"physics_{subdomain}"
            specialist_pred = {"label": concept_override, "score": None}
            regime_pred = {"label": regime_override, "score": None}
            neural_solver_mode = "conceptual_theory"
            neural_target_observable = "concept_explanation"
        else:
            top_router = NeuralTextClassifier(models_dir / "physics_topics")
            top_pred = top_router.predict(query, min_score=0.0)
            top_heads = top_pred.get("predictions") or {}
            subdomain = (top_heads.get("topic") or {}).get("label") or "classical_mechanics"
            neural_solver_mode = (top_heads.get("solver_mode") or {}).get("label")
            neural_target_observable = (top_heads.get("target_observable") or {}).get("label")

            specialist_id = f"physics_{subdomain}"
            specialist_pred = {}
            regime_pred = {}
            if (models_dir / specialist_id / "manifest.json").is_file():
                spec_clf = NeuralTextClassifier(models_dir / specialist_id)
                sp_out = spec_clf.predict(query, min_score=0.0)
                sp_heads = sp_out.get("predictions") or {}
                specialist_pred = sp_heads.get("concept") or {}
                regime_pred = sp_heads.get("regime") or {}

        vision_out = None
        if image is not None:
            vision_out = self.components["vision"].evaluate({"image": image, "query": query, "vision_domain": "physics"})

        numerical_out = None
        if any(c.isdigit() for c in query):
            numerical_out = SymbolicCASEngine.solve_numerical_word_problem(
                query,
                preferred_subdomain=subdomain,
                neural_solver_mode=neural_solver_mode,
                neural_target_observable=neural_target_observable,
            )
            if numerical_out and numerical_out.get("solved"):
                first_step = (numerical_out.get("steps") or [{}])[0]
                num_sub = first_step.get("subdomain")
                num_concept = first_step.get("concept")
                if num_sub and num_sub in {"classical_mechanics", "electromagnetism", "thermodynamics_stat_mech", "optics_waves", "quantum_mechanics", "special_relativity", "general_relativity"}:
                    subdomain = num_sub
                    specialist_id = f"physics_{subdomain}"
                if num_concept:
                    specialist_pred["label"] = num_concept

        if subdomain == "thermodynamics_stat_mech":
            svg = DiagramEngine.generate_carnot_pv_svg()
        elif subdomain == "electromagnetism":
            svg = DiagramEngine.generate_circuit_svg(config="parallel")
        elif subdomain == "optics_waves":
            svg = DiagramEngine.generate_snell_refraction_svg()
        elif subdomain in {"quantum_mechanics", "quantum_field_theory", "quantum_information"}:
            svg = DiagramEngine.generate_quantum_energy_levels_svg()
        else:
            svg = DiagramEngine.generate_inclined_plane_svg()

        from .pipeline.answer_coordination import AnswerCoordinator
        coordination = AnswerCoordinator.review_calculation(
            query, subdomain, numerical_out, self.components)
        numerical_out = coordination['numerical_solution']

        from .pipeline.pedagogical_synthesizer import PedagogicalSynthesizer
        pedagogical = PedagogicalSynthesizer.synthesize_physics_response(
            query=query,
            subdomain=subdomain,
            concept_label=specialist_pred.get("label"),
            book_engine=self.book_engine,
            numerical_solution=numerical_out,
        )
        context = AnswerCoordinator.collect_context(
            query, self.lexicon_engine, pedagogical['verified_citations'])
        coordination.update({'definitions': context['definitions'], 'citation_audit': context['citation_audit']})
        coordination['contributions'].extend(context['contributions'])
        contributions = [
            {'id': 'routing', 'name': 'Concept Rule Router' if intent_match else 'Neural Routing Classifiers',
             'status': 'matched' if intent_match else 'abstained' if top_pred.get('abstained') else 'classified'},
            {'id': 'formula_solver', 'name': 'Formula and Symbolic Calculator',
             'status': numerical_out.get('status', 'completed') if numerical_out else 'not_applicable'},
            *coordination['contributions'],
            {'id': 'retrieval', 'name': 'Textbook Retrieval and Integrity Checks',
             'status': 'matched' if pedagogical['verified_citations'] else 'no_match'},
            {'id': 'explanation', 'name': 'Structured Explanation Renderer', 'status': 'completed'},
        ]

        return {
            "subdomain": subdomain,
            "routing_method": "concept_rule" if intent_match else "neural_classifier",
            "coordination": coordination,
            "component_contributions": contributions,
            "neural_solver_mode": neural_solver_mode,
            "neural_target_observable": neural_target_observable,
            "specialist_expert_id": specialist_id,
            "concept_prediction": specialist_pred.get("label"),
            "concept_score": specialist_pred.get("score"),
            "regime_prediction": regime_pred.get("label"),
            "neural_answer_span": pedagogical.get("neural_answer_span"),
            "vision_analysis": vision_out,
            "numerical_solution": numerical_out,
            "pedagogical_explanation": pedagogical,
            "teacher_markdown": pedagogical["teacher_markdown"],
            "verified_citations": pedagogical["verified_citations"],
            "convention_harmonizer": pedagogical.get("convention_harmonizer"),
            "first_principles_derivation": pedagogical.get("first_principles_derivation"),
            "proof_certificate": pedagogical.get("proof_certificate"),
            "simulation_widget": pedagogical.get("simulation_widget"),
            "svg_diagram": svg,
        }

    def solve_physics_diagram(
        self,
        image_path: Any,
        *,
        user_question: str = "",
        diagram_type_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """World-First Pillar 4: Visual Diagram-to-Equation Multimodal Solver."""
        from .pipeline.diagram_solver import DiagramToEquationSolver
        return DiagramToEquationSolver.solve_diagram(
            image_path,
            user_question=user_question,
            vision_expert=self.components.get("vision"),
            diagram_type_override=diagram_type_override,
        )

    def dispatch_universal_core(
        self,
        query: str,
        *,
        image: Optional[Any] = None,
        workflow_payload: Optional[Dict[str, Any]] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Unified dispatcher across all 7 Universal Cores (Physics, Vision, Formula CAS, GST/Software Control, Coding/Excel/Mail Synthesis, History/Politics, and Temporal Web/News)."""
        from pathlib import Path
        from .neural.text_expert import NeuralTextClassifier
        from .pipeline.structured_synthesis import StructuredSynthesisCore
        from .cognition.engine import CognitiveEngine

        q_lower = (query or "").lower()
        payload = workflow_payload or {}
        models_dir = Path(__file__).resolve().parent / "data" / "models"

        arithmetic = re.fullmatch(
            r"\s*(?:(?:solve|calculate|compute|what is)\s+)?([\d\s.()+*/^%\-]+)\s*\??\s*",
            query or "", re.IGNORECASE,
        )
        if arithmetic and any(op in arithmetic.group(1) for op in "+-*/^%"):
            return {"core": "bounded_arithmetic", "domain": "mathematics",
                    "result": SymbolicCASEngine.calculate(arithmetic.group(1).strip())}

        # Core 5: GST Return & Software Control Workflow
        if any(k in q_lower for k in ("gstr", "gstin", "gst return", "cgst", "sgst", "igst")) or "supplier_gstin" in payload:
            from .knowledge_services import KnowledgeCore
            state_dir = Path(__file__).resolve().parents[1] / "state" / "knowledge"
            cog = CognitiveEngine(KnowledgeCore(state_dir, tenant="default_tenant", curator=True))
            return {
                "core": "core_5_action_workflow",
                "domain": "gst_and_software_control",
                "result": cog.prepare_gst_return_workflow(
                    supplier_gstin=str(payload.get("supplier_gstin", "27AABCU9603R1ZM")),
                    return_period=str(payload.get("return_period", "2026-10")),
                    invoices=list(payload.get("invoices", [])),
                    itc_available=float(payload.get("itc_available", 0.0)),
                ),
            }

        # Core 6: Excel Form Builder, Code Synthesis, or Mail/Chat Composer
        if any(k in q_lower for k in ("excel", "spreadsheet", "csv", "invoice table", "workbook")):
            return {
                "core": "core_6_structured_synthesis",
                "domain": "excel_form_generation",
                "result": StructuredSynthesisCore.build_excel_form_spec(
                    sheet_title=str(payload.get("sheet_title", query[:60] or "Generated Sheet")),
                    template_type=str(payload.get("template_type", "gst_invoice_register")),
                    rows_data=payload.get("rows_data"),
                ),
            }
        if any(k in q_lower for k in ("write python", "python function", "def ", "code for", "coding", "algorithm")):
            code_clf = NeuralTextClassifier(models_dir / "coding_topics")
            pred = code_clf.predict(query, min_score=0.0) if code_clf.available else {}
            return {
                "core": "core_6_structured_synthesis",
                "domain": "coding_expert",
                "topic_prediction": ((pred.get("predictions") or {}).get("topic") or {}).get("label"),
                "result": StructuredSynthesisCore.synthesize_code(
                    task_query=query,
                    custom_code=payload.get("custom_code"),
                ),
            }
        if any(k in q_lower for k in ("reply email", "draft email", "compose email", "formal mail", "gst notice reply")):
            return {
                "core": "core_6_structured_synthesis",
                "domain": "mail_and_chat_composer",
                "result": StructuredSynthesisCore.compose_email_or_chat(
                    mode=str(payload.get("mode", "email")),
                    tone=str(payload.get("tone", "gst_notice_reply" if "gst" in q_lower else "formal_business")),
                    recipient_name=str(payload.get("recipient_name", "Respected Officer")),
                    subject_topic=str(payload.get("subject_topic", query[:80])),
                    key_facts=list(payload.get("key_facts", [query])),
                ),
            }

        # Core 2 + Core 7: History, Politics & Temporal Fact Queries
        if any(k in q_lower for k in ("constitution", "amendment", "basic structure", "prime minister", "history", "dynasty", "treaty", "article 368", "geopolitics", "fiscal policy")):
            hp_clf = NeuralTextClassifier(models_dir / "history_politics_topics")
            pred = hp_clf.predict(query, min_score=0.0) if hp_clf.available else {}
            entity_key = str(payload.get("entity_key", "gst_rate_solar_cells"))
            temporal_facts = self.news_engine.query_temporal_facts(
                entity_key,
                as_of_date=as_of,
            )
            return {
                "core": "core_2_and_7_history_politics_temporal",
                "domain": "history_and_politics",
                "topic_prediction": ((pred.get("predictions") or {}).get("topic") or {}).get("label"),
                "contradiction_analysis": DialecticContradictionDetector.audit_contradictions({}, query),
                "temporal_facts": temporal_facts,
            }

        # The Harness also uses the existing dependency-ordered reference workflow
        # instead of forcing biology and source questions through physics.
        active = CapabilityRouter().route(query, has_image=image is not None)
        reference_keys = {'botany', 'wildlife', 'toxicity', 'biology', 'genetics', 'cell_biology',
                          'mycology', 'entomology', 'ornithology', 'ecology', 'pathology',
                          'marine', 'microbiology', 'evolution', 'librarian', 'review'}
        if reference_keys.intersection(active) or (
            'biographer' in active and re.search(r'\b(?:who|born|biography|invented)\b', query, re.I)
        ):
            # Harness history does not provide a trusted application session ID.
            # Keep this turn stateless rather than sharing the default memory.
            import uuid
            session_id = 'harness-components-' + uuid.uuid4().hex
            try:
                detailed = self.process_detailed(query, image=image, session_id=session_id, show_thinking=False)
            finally:
                self.reset_session(session_id)
                self.sessions.pop(session_id, None)
            return {'core': 'coordinated_components', 'domain': 'reference_workflow', 'result': detailed}

        # Core 2 + Core 3 + Core 4: Hierarchical Physics + Vision + Universal Formula Solver
        return {
            "core": "core_2_3_4_physics_vision_cas",
            "domain": "physics",
            "result": self.dispatch_physics_hierarchy(query, image=image),
        }


TinyExpertOrchestrator = ComponentOrchestrator  # Legacy public import.
