"""Comprehensive Pytest Suite for all 10 World-First Architectural Pillars."""
from __future__ import annotations

from pathlib import Path

from tiny_experts.knowledge_services import KnowledgeCore
from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.cas_engine import SymbolicCASEngine
from tiny_experts.pipeline.diagram_solver import DiagramToEquationSolver
from tiny_experts.pipeline.formula_solver import UniversalFormulaSolver
from tiny_experts.pipeline.pedagogical_synthesizer import PedagogicalSynthesizer
from tiny_experts.source_studio.director import TrainingDirector


def test_pillar_1_closed_loop_concept_promotion_and_specialist_retraining(tmp_path: Path):
    """Pillar 1: Closed-Loop Autonomous Concept Promotion & Specialist Retraining."""
    core = KnowledgeCore(tmp_path / "core_p1", tenant="t_p1", curator=True)
    director = TrainingDirector(core)
    promo = director.auto_promote_concepts_and_retrain_specialist(
        "classical_mechanics",
        promoted_concepts=["holonomic_constraint", "dalembert_principle", "adiabatic_invariant"],
        output_dir=tmp_path / "models" / "physics_classical_mechanics_promoted",
        epochs=14,
    )
    assert promo["total_concepts_in_head"] >= 10
    assert "holonomic_constraint" in promo["newly_promoted_concepts"]
    assert promo["shadow_gate"]["promoted"] is True
    assert promo["live_probe_prediction"] == "adiabatic_invariant"


def test_pillar_2_live_equation_discovery_to_symbolic_solver_compilation():
    """Pillar 2: Automated Equation Discovery -> Live Symbolic Solver Compilation."""
    comp = UniversalFormulaSolver.compile_and_register_learned_formula({
        "formula_id": "learned_acoustic_impedance_z",
        "subdomain": "optics_waves",
        "concept": "acoustic_impedance",
        "title": "Acoustic Impedance Law (Z_ac = rho_fluid * v)",
        "lhs": "Z_ac",
        "rhs": "rho_fluid * v",
        "variables": ["Z_ac", "rho_fluid", "v"],
        "keywords": ["acoustic impedance"],
        "variable_definitions": {
            "Z_ac": {
                "name": "acoustic_impedance",
                "si_unit": "Pa*s/m",
                "dimension": "M1 L-2 T-1",
                "aliases": ["acoustic impedance", "z_ac"],
                "unit_map": {"pa*s/m": 1.0, "rayl": 1.0},
            }
        },
    })
    assert comp["compiled"] is True
    assert "Z_ac" in comp["symbolic_inversions"]
    assert "rho_fluid" in comp["symbolic_inversions"]

    solver = UniversalFormulaSolver()
    fwd = solver.solve_query(
        "Find the acoustic impedance when density is 1200 kg/m^3 and velocity is 1500 m/s.",
        preferred_subdomain="optics_waves",
    )
    assert fwd["solved"] is True
    assert abs(fwd["final_value"] - 1800000.0) < 1.0

    rev = solver.solve_query(
        "Find the density when acoustic impedance is 1800000 Pa*s/m and velocity is 1500 m/s.",
        preferred_subdomain="optics_waves",
    )
    assert rev["solved"] is True
    assert abs(rev["final_value"] - 1200.0) < 1e-2


def test_pillar_3_adversarial_self_play_exam_generator_and_debugger(tmp_path: Path):
    """Pillar 3: Adversarial Self-Play Exam Generator & Self-Debugger."""
    core = KnowledgeCore(tmp_path / "core_p3", tenant="t_p3", curator=True)
    director = TrainingDirector(core)
    orch = TinyExpertOrchestrator()
    report = director.run_adversarial_self_play(orch)
    assert report["total_exam_questions"] == 12
    assert report["pass_rate"] == 1.0
    assert report["mode_breakdown"]["forward"]["accuracy"] == 1.0
    assert report["mode_breakdown"]["reverse_inversion"]["accuracy"] == 1.0
    assert report["mode_breakdown"]["cross_domain_3hop"]["accuracy"] == 1.0


def test_pillar_4_visual_diagram_to_equation_multimodal_solver(tmp_path: Path):
    """Pillar 4: Visual Diagram-to-Equation Multimodal Solver (PNG + WinRT OCR + CAS)."""
    img_path = DiagramToEquationSolver.render_labeled_physics_diagram_png(
        tmp_path / "inclined_plane_test.png",
        diagram_type="inclined_plane",
        labels_text="mass = 10 kg velocity = 6 m/s",
    )
    orch = TinyExpertOrchestrator()
    solved = orch.solve_physics_diagram(
        img_path,
        user_question="Calculate the kinetic energy of the block shown in the diagram.",
        diagram_type_override="inclined_plane",
    )
    assert solved["solved"] is True
    assert abs(solved["numerical_solution"]["final_value"] - 180.0) < 1e-2


def test_pillar_5_cross_domain_3hop_physics_chains():
    """Pillar 5: Multi-Hop Cross-Domain Physics Chaining (3-Hop Scene Graph)."""
    # 1. Photoelectric (QM) -> Velocity (CM) -> Cyclotron Radius (EM)
    res1 = SymbolicCASEngine.solve_numerical_word_problem(
        "In a photoelectric effect experiment, light of wavelength 200 nm illuminates a metal with "
        "work function 2.2 eV, and the emitted photoelectron enters a uniform magnetic field of 2 mT. "
        "Calculate the cyclotron radius (Larmor radius) of the photoelectron."
    )
    assert res1 is not None and res1["hops"] == 3
    assert len(res1["steps"]) == 3
    assert abs(res1["final_value"] - 0.0033737) < 1e-4

    # 2. Accelerating Potential (EM) -> Momentum (CM) -> de Broglie Wavelength (QM)
    res2 = SymbolicCASEngine.solve_numerical_word_problem(
        "An electron is accelerated from rest through an electric potential difference of 150 V. "
        "Calculate its resulting de Broglie wavelength."
    )
    assert res2 is not None and res2["hops"] == 3
    assert abs(res2["final_value"] - 1.0013e-10) < 1e-12

    # 3. Torricelli Efflux (Fluid) -> Free Fall (CM) -> Horizontal Range (CM)
    res3 = SymbolicCASEngine.solve_numerical_word_problem(
        "A water tank has a small orifice at depth 5 m below the water surface, and the orifice sits "
        "20 m above the ground. Using Torricelli's law and projectile kinematics, calculate the "
        "horizontal distance where the water jet hits the ground."
    )
    assert res3 is not None and res3["hops"] == 3
    assert abs(res3["final_value"] - 20.0) < 1e-2

    # 4. Joule Heating (EM) -> Thermal Energy -> Calorimetry Temperature Rise (Thermo)
    res4 = SymbolicCASEngine.solve_numerical_word_problem(
        "An electric heater operating at 100 V with resistance 20 ohm heats 2 kg of water with "
        "specific heat 4000 J/kg-K for 60 s. Calculate the temperature rise delta T."
    )
    assert res4 is not None and res4["hops"] == 3
    assert abs(res4["final_value"] - 3.75) < 1e-3


def test_pillar_6_universal_autonomous_subject_hierarchy_spawner(tmp_path: Path):
    """Pillar 6: Universal Autonomous Subject / HuggingFace Dataset Hierarchy Spawner."""
    core = KnowledgeCore(tmp_path / "core_p6", tenant="t_p6", curator=True)
    director = TrainingDirector(core)

    chem_dataset = []
    specs = [
        ("organic_chemistry", "nucleophilic_substitution", "SN1 and SN2 nucleophilic substitution reactions on alkyl halides with leaving group departure."),
        ("organic_chemistry", "electrophilic_aromatic", "Electrophilic aromatic substitution on benzene rings via sigma complex arenium ion intermediate."),
        ("physical_chemistry", "chemical_kinetics", "Arrhenius activation energy and reaction rate law order in chemical kinetics."),
        ("physical_chemistry", "electrochemistry_nernst", "Nernst equation for half-cell electrode potential and galvanic cell Gibbs free energy."),
    ]
    for cat, con, base_txt in specs:
        for i in range(1, 7):
            chem_dataset.append({
                "source_id": f"chem_src_{i}",
                "category": cat,
                "concept": con,
                "text": f"{base_txt} Reference study variation {i} covering {con.replace('_', ' ')} in {cat.replace('_', ' ')}.",
            })

    spawned = director.spawn_domain_hierarchy_from_dataset(
        "chemistry",
        chem_dataset,
        output_root=tmp_path / "spawned_chemistry",
        epochs=16,
    )
    assert spawned["domain_name"] == "chemistry"
    assert set(spawned["categories_discovered"]) == {"organic_chemistry", "physical_chemistry"}
    assert spawned["all_probes_correct"] is True


def test_pillar_7_8_9_10_harmonizer_derivation_proof_and_simulation_widget():
    """Pillars 7, 8, 9, and 10 integrated into PedagogicalSynthesizer & SymbolicCASEngine."""
    orch = TinyExpertOrchestrator()
    out = orch.dispatch_physics_hierarchy(
        "Derive the Euler-Lagrange equation for a harmonic oscillator and calculate the kinetic energy for mass = 4 kg and velocity = 5 m/s."
    )
    # Pillar 7: Convention Harmonizer
    harm = out["convention_harmonizer"]
    assert harm is not None
    assert "convention_name" in harm
    assert "translation_rule" in harm

    # Pillar 8: First-Principles Symbolic Calculus Derivation Tree
    deriv = out["first_principles_derivation"]
    assert deriv is not None
    assert deriv["derived"] is True
    assert len(deriv["steps"]) >= 3

    # Pillar 9: Mathematical & Cryptographic Proof Certificate 2.0
    cert = out["proof_certificate"]
    assert cert is not None
    assert cert["certificate_valid"] is True
    assert len(cert["asymptotic_checks"]) >= 1

    # Pillar 10: Interactive HTML5 Canvas Simulation Widget
    sim = out["simulation_widget"]
    assert sim is not None
    assert "<canvas" in sim["embeddable_html"]
    assert sim["widget_type"] == "html5_canvas_physics_simulation"
