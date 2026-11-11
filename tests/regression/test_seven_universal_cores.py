"""Comprehensive End-to-End Verification Suite for all 7 Universal Cores."""
from __future__ import annotations

from pathlib import Path
import pytest

from tiny_experts.cognition.engine import CognitiveEngine
from tiny_experts.experts.neural_reference_expert import NeuralReferenceExpert
from tiny_experts.experts.vision_expert import VisionExpert
from tiny_experts.knowledge_core.system import KnowledgeCore
from tiny_experts.knowledge_services.crawl import classify_source_trust, extract_structured_dom
from tiny_experts.pipeline.book_engine import BookEngine
from tiny_experts.pipeline.cas_engine import SymbolicCASEngine
from tiny_experts.pipeline.diagram_engine import DiagramEngine
from tiny_experts.pipeline.news_engine import NewsEngine
from tiny_experts.pipeline.structured_synthesis import StructuredSynthesisCore
from tiny_experts.source_studio.director import TrainingDirector


def test_core1_poison_book_quarantine_replay_shadow_and_leech_bus(tmp_path: Path):
    """Verify Core 1: Poison-Book Quarantine, Parallel Leech Bus, Replay Buffer & Shadow Gate."""
    core = KnowledgeCore(tmp_path / "core1_state", tenant="test_tenant", curator=True)
    director = TrainingDirector(core)

    # 1. Feed a corrupted / gibberish OCR source -> must be quarantined
    bad_src = core.register_source("src:corrupt_book", "Corrupted OCR Book", source_type="book")
    bad_body = b"### $$$ @@@ %%% ^^^ &&& *** ~~~ ``` ||| 1234567890 @@@ ### $$$ %%% ^^^ &&&"
    bad_rev = core.ingest(
        bad_src,
        bad_body,
        media_type="text/plain",
        rights={"store": True, "retrieve": True, "train": True},
        license_note="Test license",
    )["revision_id"]
    core.add_segment(bad_rev, {"type": "text", "start": 0, "end": len(bad_body)})
    core.review(bad_rev, decision="accepted", note="Check quarantine gate")

    bad_res = director.teach_from_revision(bad_rev, book_title="Corrupted OCR Book")
    assert bad_res["quarantined"] is True
    assert bad_res["quality_score"] < 0.45

    # 2. Feed a clean Physics textbook passage with equations, scientist bio,acronym, and figure caption
    good_src = core.register_source("src:clean_physics", "Clean Quantum & Thermo Treatise", source_type="book")
    good_text = (
        "The Carnot cycle is defined as an idealized reversible thermodynamic cycle operating between two heat reservoirs.\n"
        "Sadi Carnot (1796-1832) demonstrated that maximum thermal efficiency is bounded by eta = 1 - T_C / T_H.\n"
        "In Quantum Electrodynamics (QED), the de Broglie wavelength is defined as the ratio of Planck constant to momentum.\n"
        "Figure 4.2: Carnot cycle P-V isotherm and adiabat diagram for an ideal gas heat engine."
    )
    good_rev = core.ingest(
        good_src,
        good_text.encode("utf-8"),
        media_type="text/plain",
        rights={"store": True, "retrieve": True, "train": True},
        license_note="Test license",
    )["revision_id"]
    for line in good_text.splitlines():
        st = good_text.index(line)
        core.add_segment(good_rev, {"type": "text", "start": st, "end": st + len(line)})
    core.review(good_rev, decision="accepted", note="Clean physics textbook")

    good_res = director.teach_from_revision(good_rev, book_title="Clean Quantum & Thermo Treatise")
    assert good_res["quarantined"] is False
    assert good_res["quality_score"] >= 0.70
    assert good_res["leech_bus"]["formulas_leeched"] >= 1
    assert good_res["leech_bus"]["biographies_leeched"] >= 1
    assert good_res["leech_bus"]["lexicon_terms_leeched"] >= 1
    assert good_res["leech_bus"]["figures_routed"] >= 1

    # Verify Experience Replay Buffer & Shadow Benchmark Gate
    replay_samples = director.sample_replay_buffer()
    assert len(replay_samples) >= 1
    promoted = director.shadow_evaluate_and_gate({"test_accuracy": 0.96}, {"test_accuracy": 0.94})
    assert promoted["promoted"] is True
    rolled_back = director.shadow_evaluate_and_gate({"test_accuracy": 0.80}, {"test_accuracy": 0.95})
    assert rolled_back["promoted"] is False


def test_core4_unseen_numericals_bidirectional_multihop_and_sanity_critic():
    """Verify Core 4: Forward, Reverse, Multi-Hop Chaining & Physical Sanity Critic on unseen numericals."""
    # 1. Reverse algebraic solve: given Kinetic Energy and Mass, find Velocity!
    rev_ke = SymbolicCASEngine.solve_numerical_word_problem(
        "A body of mass = 2 kg has kinetic energy = 100 J. Find the velocity."
    )
    assert rev_ke["solved"] is True
    assert rev_ke["target_variable"] == "v"
    assert abs(rev_ke["final_value"] - 10.0) < 1e-4

    # 2. Unseen Quantum numerical: de Broglie wavelength from mass (in grams!) and velocity
    db_res = SymbolicCASEngine.solve_numerical_word_problem(
        "A particle with mass = 500 g moves at velocity = 20 m/s. What is its de Broglie wavelength?"
    )
    assert db_res["solved"] is True
    assert db_res["target_variable"] == "lam"
    expected_lambda = 6.62607015e-34 / (0.5 * 20.0)
    assert abs(db_res["final_value"] - expected_lambda) / expected_lambda < 1e-5

    # 3. Multi-Hop Formula Chaining (2 hops: Ramp Height h -> Gravitational PE -> Spring Compression x)
    multihop_res = SymbolicCASEngine.solve_numerical_word_problem(
        "A 2 kg block slides down a 5 m high ramp into a spring with spring constant 400 N/m. How far does the spring compress?"
    )
    assert multihop_res["solved"] is True
    assert multihop_res["mode"] == "multihop_formula_chain"
    assert multihop_res["hops"] == 2
    assert multihop_res["target_variable"] == "x_disp"
    expected_x = ((2.0 * 2.0 * 9.80665 * 5.0) / 400.0) ** 0.5
    assert abs(multihop_res["final_value"] - expected_x) < 1e-3

    # 4. Physical Sanity Critic: speed exceeding speed of light c must flag violation
    superluminal = SymbolicCASEngine.solve_numerical_word_problem(
        "A particle of mass = 1 kg moves at velocity = 4e8 m/s. Find the kinetic energy."
    )
    assert superluminal["solved"] is False
    assert superluminal["status"] == "physical_sanity_violation"
    assert any("Relativistic Violation" in v for v in superluminal["physical_violations"])


def test_core2_and_core3_specialist_models_and_multimodal_vision():
    """Verify Core 2 (Physics Specialist + Numerical Bridge) & Core 3 (Multi-Bundle Vision + Diagrams)."""
    models_root = Path(__file__).resolve().parents[2] / "tiny_experts" / "data" / "models"
    book_engine = BookEngine()

    # Core 2: NeuralReferenceExpert with unseen numerical calculation
    phys_expert = NeuralReferenceExpert(
        "physics_topics",
        models_root / "physics_topics",
        book_engine,
        "physics",
    )
    out = phys_expert.evaluate({
        "query": "In classical mechanics, a particle of mass = 4 kg has velocity = 5 m/s. Find the kinetic energy."
    })
    assert out["relevant"] is True
    assert "numerical_calculation" in out
    assert abs(out["numerical_calculation"]["final_value"] - 50.0) < 1e-4

    # Core 3: VisionExpert multi-bundle routing (Leaf vs Physics Diagram)
    vision = VisionExpert()
    leaf_img = Path(__file__).resolve().parents[2] / "tiny_experts" / "data" / "images" / "leaf_benchmark" / "early_blight" / "early_blight_00.png"
    if leaf_img.exists():
        leaf_res = vision.evaluate({"image": leaf_img, "query": "inspect tomato leaf blight"})
        assert leaf_res["detected"] is True
        assert leaf_res["category"] == "plant_pathology"

    phys_img = Path(__file__).resolve().parents[2] / "tiny_experts" / "data" / "images" / "physics_diagrams" / "carnot_pv_cycle" / "carnot_pv_cycle_18.png"
    if phys_img.exists() and "physics_vision" in vision.vision_bundles:
        phys_vis_res = vision.evaluate({"image": phys_img, "query": "thermodynamic Carnot P-V cycle diagram"})
        assert phys_vis_res["detected"] is True
        assert phys_vis_res["bundle"] == "physics_vision"
        assert phys_vis_res["diagram_id"] == "carnot_pv_cycle"

    # Dynamic SVG generators for Mechanics, Optics, Quantum
    assert "<svg" in DiagramEngine.generate_inclined_plane_svg(5.0, 30.0)
    assert "<svg" in DiagramEngine.generate_snell_refraction_svg(1.0, 1.5, 45.0)
    assert "<svg" in DiagramEngine.generate_quantum_energy_levels_svg(3, 1)


def test_core5_software_workflow_and_gst_return_filing(tmp_path: Path):
    """Verify Core 5: GSTIN validation, CGST/SGST/IGST + ITC calculation, and Software Control plan."""
    core = KnowledgeCore(tmp_path / "core5_state", tenant="gst_tenant", curator=True)
    cog = CognitiveEngine(core)

    assert cog.validate_gstin("27AABCU9603R1ZM")["valid"] is True
    assert cog.validate_gstin("INVALID_GSTIN")["valid"] is False

    gst_plan = cog.prepare_gst_return_workflow(
        supplier_gstin="27AABCU9603R1ZM",
        return_period="2026-10",
        invoices=[
            {"invoice_no": "INV-101", "buyer_gstin": "27BBBCU1234R1Z5", "taxable_value": 10000.0, "gst_rate": 18.0},
            {"invoice_no": "INV-102", "buyer_gstin": "29CCCDU5678R1Z9", "taxable_value": 20000.0, "gst_rate": 18.0},
        ],
        itc_available=2000.0,
    )
    assert gst_plan["total_taxable_value"] == 30000.0
    assert gst_plan["total_cgst"] == 900.0
    assert gst_plan["total_sgst"] == 900.0
    assert gst_plan["total_igst"] == 3600.0
    assert gst_plan["gross_tax_liability"] == 5400.0
    assert gst_plan["itc_applied"] == 2000.0
    assert gst_plan["net_cash_payable"] == 3400.0
    assert gst_plan["requires_human_commit_gate"] is True


def test_core6_coding_sandbox_excel_builder_and_mail_chat_composer():
    """Verify Core 6: Coding AST + Unit Test Sandbox, Excel Formula Builder, and Email/Chat Composer."""
    code_res = StructuredSynthesisCore.synthesize_code("Write a GST tax breakdown calculator function")
    assert code_res["status"] == "verified"
    assert code_res["verification"]["ast_valid"] is True
    assert code_res["verification"]["test_passed"] is True

    # Verify unsafe code with import/eval is blocked
    unsafe_res = StructuredSynthesisCore.verify_python_code("import os\nos.system('echo hi')")
    assert unsafe_res["ast_valid"] is False

    # Excel form & live formula builder
    excel_spec = StructuredSynthesisCore.build_excel_form_spec(sheet_title="October_GST_Register")
    assert excel_spec["row_count"] == 4
    assert "=SUM(E2:E3)" in excel_spec["csv_content"]
    assert excel_spec["evaluated_totals"]["total_taxable_value"] == 75000.0

    # Email & Chat composer
    email_res = StructuredSynthesisCore.compose_email_or_chat(
        mode="email",
        tone="gst_notice_reply",
        recipient_name="GST Assessing Officer",
        subject_topic="GSTR-3B ITC Reconciliation",
        key_facts=["Total IGST reconciled: INR 3,600", "Net cash paid: INR 3,400"],
    )
    assert email_res["mode"] == "email"
    assert "INR 3,600" in email_res["body"]


def test_core7_web_dom_table_extractor_and_temporal_news_supersession():
    """Verify Core 7: Clean DOM/Table extraction, Source Trust Tiers, and Temporal Supersession Clock."""
    sample_html = """
    <html>
      <head>
        <title>CBIC Official GST Rate Notification 2026</title>
        <meta property="article:published_time" content="2026-10-15" />
      </head>
      <body>
        <script>console.log("ignore ad tracker");</script>
        <nav>Menu Home Login</nav>
        <h1>Updated Renewable Energy GST Schedule</h1>
        <p>The Central Board of Indirect Taxes and Customs hereby notifies updated rates for solar modules.</p>
        <table>
          <tr><th>HSN</th><th>Description</th><th>Rate</th></tr>
          <tr><td>8541</td><td>Solar Photovoltaic Cells</td><td>12%</td></tr>
        </table>
      </body>
    </html>
    """
    extracted = extract_structured_dom(sample_html, url="https://cbic-gst.gov.in/notifications/2026")
    assert extracted["title"] == "CBIC Official GST Rate Notification 2026"
    assert extracted["published_date"] == "2026-10-15"
    assert extracted["trust"]["trust_tier"] == "gov_official"
    assert "ignore ad tracker" not in extracted["clean_text"]
    assert extracted["tables"][0][1] == ["8541", "Solar Photovoltaic Cells", "12%"]

    # Temporal fact clock & supersession check
    news = NewsEngine()
    hist_2020 = news.query_temporal_facts("gst_rate_solar_cells", as_of_date="2020-05-01")
    assert len(hist_2020["active_facts"]) == 1
    assert "5%" in hist_2020["active_facts"][0]["claim"]

    curr = news.query_temporal_facts("gst_rate_solar_cells")
    assert len(curr["active_facts"]) == 1
    assert "12%" in curr["active_facts"][0]["claim"]


def test_orchestrator_hierarchical_physics_dispatch_and_visual_bridge():
    """Verify TinyExpertOrchestrator 2-Stage Physics Hierarchy + Specialist + Symbolic + SVG."""
    from tiny_experts.orchestrator import TinyExpertOrchestrator

    orch = TinyExpertOrchestrator()
    phys_img = Path(__file__).resolve().parents[2] / "tiny_experts" / "data" / "images" / "physics_diagrams" / "carnot_pv_cycle" / "carnot_pv_cycle_18.png"
    res = orch.dispatch_physics_hierarchy(
        "In thermodynamics_stat_mech, how does the carnot_cycle determine efficiency when hot reservoir temperature = 600 K and cold reservoir temperature = 300 K? Find the carnot efficiency.",
        image=phys_img if phys_img.exists() else None,
    )
    assert res["specialist_expert_id"].startswith("physics_")
    assert res["concept_prediction"] is not None
    assert res["numerical_solution"]["solved"] is True
    assert abs(res["numerical_solution"]["final_value"] - 0.5) < 1e-4
    assert "<svg" in res["svg_diagram"]


def test_orchestrator_dispatch_universal_core_all_domains():
    """Verify TinyExpertOrchestrator.dispatch_universal_core across Physics, GST, Excel, Coding, Mail, and History/Politics."""
    from tiny_experts.orchestrator import TinyExpertOrchestrator

    orch = TinyExpertOrchestrator()

    # 1. GST Return Workflow (Core 5)
    gst_out = orch.dispatch_universal_core(
        "Prepare GSTR-3B return workflow",
        workflow_payload={
            "supplier_gstin": "27AABCU9603R1ZM",
            "return_period": "2026-10",
            "invoices": [{"invoice_no": "INV-1", "buyer_gstin": "27BBBCU1234R1Z5", "taxable_value": 10000.0, "gst_rate": 18.0}],
            "itc_available": 500.0,
        },
    )
    assert gst_out["core"] == "core_5_action_workflow"
    assert gst_out["result"]["requires_human_commit_gate"] is True
    assert gst_out["result"]["net_cash_payable"] == 1300.0

    # 2. Excel Form Generation (Core 6)
    excel_out = orch.dispatch_universal_core("Build an Excel spreadsheet for GST invoices")
    assert excel_out["core"] == "core_6_structured_synthesis"
    assert excel_out["domain"] == "excel_form_generation"
    assert "=SUM(" in excel_out["result"]["csv_content"]

    # 3. Coding Expert + AST Verification (Core 6)
    code_out = orch.dispatch_universal_core("Write Python code for kinetic energy physics calculation")
    assert code_out["core"] == "core_6_structured_synthesis"
    assert code_out["domain"] == "coding_expert"
    assert code_out["result"]["verification"]["test_passed"] is True

    # 4. Mail & Chat Composer (Core 6)
    mail_out = orch.dispatch_universal_core(
        "Draft a GST notice reply email regarding ITC reconciliation",
        workflow_payload={"key_facts": ["Reconciled INR 1,800 in GSTR-2B"]},
    )
    assert mail_out["core"] == "core_6_structured_synthesis"
    assert mail_out["domain"] == "mail_and_chat_composer"
    assert "Reconciled INR 1,800" in mail_out["result"]["body"]

    # 5. History, Politics & Temporal Fact Clock (Core 2 + Core 7)
    hp_out = orch.dispatch_universal_core(
        "How does the Basic Structure doctrine limit Article 368 constitutional amendment power?",
        workflow_payload={"entity_key": "gst_rate_solar_cells"},
        as_of="2020-05-01",
    )
    assert hp_out["core"] == "core_2_and_7_history_politics_temporal"
    assert hp_out["topic_prediction"] == "constitutional_law_governance"
    assert hp_out["contradiction_analysis"]["has_contradiction"] is True
    assert "5%" in hp_out["temporal_facts"]["active_facts"][0]["claim"]


def test_source_studio_7_core_http_endpoints(tmp_path: Path):
    """Verify Source Studio FastAPI HTTP endpoints for Core 1, Core 5 (GST), and Core 6 (Synthesis)."""
    from fastapi.testclient import TestClient
    from tiny_experts.source_studio.app import create_app

    token = "studio-7-core-secret-token-123456"
    app = create_app(tmp_path / "studio_root", token=token)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}", "Host": "localhost"}

    # Core 5: /api/cognition/gst-workflow
    gst_resp = client.post(
        "/api/cognition/gst-workflow",
        headers=headers,
        json={
            "supplier_gstin": "27AABCU9603R1ZM",
            "return_period": "2026-10",
            "invoices": [{"invoice_no": "INV-1", "buyer_gstin": "27BBBCU1234R1Z5", "taxable_value": 10000.0, "gst_rate": 18.0}],
            "itc_available": 500.0,
        },
    )
    assert gst_resp.status_code == 200
    assert gst_resp.json()["net_cash_payable"] == 1300.0

    # Core 6: /api/synthesis/execute (code & excel)
    code_resp = client.post(
        "/api/synthesis/execute",
        headers=headers,
        json={"mode": "code", "query": "Write a GST tax breakdown calculator function"},
    )
    assert code_resp.status_code == 200
    assert code_resp.json()["verification"]["test_passed"] is True

    excel_resp = client.post(
        "/api/synthesis/execute",
        headers=headers,
        json={"mode": "excel", "sheet_title": "Studio_GST_Sheet"},
    )
    assert excel_resp.status_code == 200
    assert "=SUM(" in excel_resp.json()["csv_content"]



