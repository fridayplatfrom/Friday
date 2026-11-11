import unittest
from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.book_engine import BookEngine
from tiny_experts.pipeline.review_engine import EpistemicReviewEngine
from tiny_experts.pipeline.contradiction_detector import DialecticContradictionDetector
from tiny_experts.pipeline.universal_concept_graph import UniversalConceptGraph
from tiny_experts.pipeline.ingestion import LiteratureIngestionPipeline
from tiny_experts.experts.thermodynamics_expert import ThermodynamicsExpert
from tiny_experts.experts.electronics_expert import ElectronicsExpert
from tiny_experts.experts.mechanics_expert import MechanicsExpert
from tiny_experts.experts.review_expert import ReviewExpert

class TestPhysicsAndEpistemicFrontiers(unittest.TestCase):
    """Rigorous verification suite for Physics micro-experts and Epistemic Review layer."""

    @classmethod
    def setUpClass(cls):
        cls.orchestrator = TinyExpertOrchestrator(verbose=False)
        cls.book_engine = cls.orchestrator.book_engine

    def test_total_micro_experts_registered(self):
        """Verify all 23 specialized micro-experts are loaded on local CPU."""
        self.assertEqual(len(self.orchestrator.experts), 24)
        self.assertIn("thermodynamics", self.orchestrator.experts)
        self.assertIn("electronics", self.orchestrator.experts)
        self.assertIn("mechanics", self.orchestrator.experts)
        self.assertIn("review", self.orchestrator.experts)

    def test_thermodynamics_carnot_calculation(self):
        """Test exact deterministic Carnot thermal efficiency computation."""
        expert = ThermodynamicsExpert(book_engine=self.book_engine)
        res = expert.evaluate({"query": "Calculate Carnot efficiency for T_H = 500 K and T_C = 300 K"})
        self.assertTrue(res["active"])
        self.assertIn("carnot_efficiency", res["calculations"])
        carnot = res["calculations"]["carnot_efficiency"]
        self.assertEqual(carnot["T_H_Kelvin"], 500.0)
        self.assertEqual(carnot["T_C_Kelvin"], 300.0)
        self.assertEqual(carnot["efficiency_fraction"], 0.4)
        self.assertEqual(carnot["efficiency_percent"], 40.0)

    def test_thermodynamics_fourier_conduction(self):
        """Test Fourier's law of heat conduction."""
        expert = ThermodynamicsExpert(book_engine=self.book_engine)
        res = expert.evaluate({"query": "Fourier heat transfer for k = 0.5, Area = 4, thickness = 0.1, delta_T = 50"})
        self.assertIn("fourier_conduction", res["calculations"])
        fourier = res["calculations"]["fourier_conduction"]
        self.assertEqual(fourier["heat_rate_watts"], 1000.0)
        self.assertEqual(fourier["heat_flux_W_per_m2"], 250.0)

    def test_electronics_ohms_law(self):
        """Test Ohm's law and power dissipation."""
        expert = ElectronicsExpert(book_engine=self.book_engine)
        res = expert.evaluate({"query": "Find current for Voltage = 12 V and Resistance = 4 ohm"})
        self.assertTrue(res["active"])
        self.assertIn("ohms_law", res["calculations"])
        ohm = res["calculations"]["ohms_law"]
        self.assertEqual(ohm["calculated_current_amperes"], 3.0)
        self.assertEqual(ohm["power_dissipation_watts"], 36.0)

    def test_electronics_resistor_network(self):
        """Test series and parallel resistor equivalent networks."""
        expert = ElectronicsExpert(book_engine=self.book_engine)
        res_series = expert.evaluate({"query": "resistors 10 and 20 in series"})
        self.assertIn("resistor_network", res_series["calculations"])
        self.assertEqual(res_series["calculations"]["resistor_network"]["equivalent_resistance_ohms"], 30.0)

        res_parallel = expert.evaluate({"query": "resistors 10 and 10 in parallel"})
        self.assertIn("resistor_network", res_parallel["calculations"])
        self.assertEqual(res_parallel["calculations"]["resistor_network"]["equivalent_resistance_ohms"], 5.0)

    def test_electronics_rc_time_constant(self):
        """Test RC circuit time constant and cutoff frequency."""
        expert = ElectronicsExpert(book_engine=self.book_engine)
        res = expert.evaluate({"query": "Calculate RC time constant for resistance 1000 ohm and capacitance 10 uf"})
        self.assertIn("rc_transient", res["calculations"])
        rc = res["calculations"]["rc_transient"]
        self.assertEqual(rc["time_constant_tau_seconds"], 0.01)

    def test_mechanics_newtons_second_law_and_energy(self):
        """Test F = m*a and Kinetic Energy."""
        expert = MechanicsExpert(book_engine=self.book_engine)
        res = expert.evaluate({"query": "Calculate force for mass = 10 kg and acceleration = 5 m/s^2, velocity = 20 m/s"})
        self.assertTrue(res["active"])
        self.assertIn("newtons_second_law", res["calculations"])
        self.assertEqual(res["calculations"]["newtons_second_law"]["force_Newtons"], 50.0)
        self.assertIn("kinetic_energy_and_momentum", res["calculations"])
        self.assertEqual(res["calculations"]["kinetic_energy_and_momentum"]["kinetic_energy_Joules"], 2000.0)
        self.assertEqual(res["calculations"]["kinetic_energy_and_momentum"]["linear_momentum_kg_m_s"], 200.0)

    def test_epistemic_review_engine(self):
        """Test retrieval of peer reviews and scholarly consensus."""
        engine = EpistemicReviewEngine()
        rev = engine.get_review_by_book_id("griffiths_electrodynamics_4th_ed")
        self.assertIsNotNone(rev)
        self.assertEqual(rev["consensus_status"], "ESTABLISHED_LAW")
        self.assertEqual(rev["scholarly_consensus_score"], 0.99)
        self.assertTrue(len(rev["peer_reviews"]) >= 2)
        self.assertTrue(len(rev["debates_and_critiques"]) >= 1)

    def test_review_expert_evaluation(self):
        """Test ReviewExpert handling a query about academic critique."""
        expert = ReviewExpert(review_engine=self.orchestrator.review_engine)
        res = expert.evaluate({"query": "What are the peer reviews and limitations of Griffiths Electrodynamics?"})
        self.assertTrue(res["matched"])
        self.assertEqual(res["book_id"], "griffiths_electrodynamics_4th_ed")
        self.assertEqual(res["consensus_status"], "ESTABLISHED_LAW")

    def test_dialectic_contradiction_detector(self):
        """Test dialectic arbitrator detects and resolves oomycete classification dispute."""
        query = "Is Phytophthora infestans a true fungus or oomycete?"
        audit = DialecticContradictionDetector.audit_contradictions(aggregated={}, query=query)
        self.assertTrue(audit["has_contradiction"])
        self.assertEqual(audit["status"], "ARBITRATION_VERIFIED")
        self.assertTrue(len(audit["paradigm_disputes"]) >= 1)
        self.assertIn("Stramenopile", audit["paradigm_disputes"][0]["arbitration"])

    def test_universal_concept_graph(self):
        """Test cross-disciplinary concept bridges linking Physics to Botany."""
        links = UniversalConceptGraph.find_cross_connections("solar radiation and photosynthesis in leaf")
        self.assertTrue(len(links) >= 1)
        self.assertEqual(links[0]["subject_faculty"], "Physics")
        self.assertIn("Botany", links[0]["object_faculty"])

    def test_chunk_direct_foreign_key_linking(self):
        """Test that chunking and ingestion attach bidirectional book catalog foreign keys."""
        pipe = LiteratureIngestionPipeline(book_engine=self.book_engine)
        chunks = pipe.chunk_scientific_text(
            raw_text="The Carnot engine operates between two thermal reservoirs. The reversible efficiency is bounded by absolute temperatures.",
            source_title="Test Physics Chapter",
            chunk_size_words=10,
            book_id="test_physics_book_id",
            edition="1st Edition",
            citation="Test Physics Citation (2024)"
        )
        self.assertTrue(len(chunks) >= 1)
        self.assertEqual(chunks[0].get("book_id"), "test_physics_book_id")
        self.assertEqual(chunks[0].get("edition"), "1st Edition")
        self.assertEqual(chunks[0].get("citation"), "Test Physics Citation (2024)")

    def test_end_to_end_orchestrator_physics_and_reviews(self):
        """Test end-to-end multi-expert execution of physics and review queries."""
        # 1. Physics query
        res_phy = self.orchestrator.process_detailed(query="Calculate Carnot efficiency for T_H = 600 K and T_C = 300 K")
        self.assertIn("thermodynamics", res_phy["active_experts"])
        self.assertTrue(res_phy["latency_ms"] < 250)
        self.assertIn("carnot_efficiency", res_phy["telemetry"]["thermodynamics"]["calculations"])

        # 2. Review query
        res_rev = self.orchestrator.process_detailed(query="Peer reviews and debates on Constitution of India Ambedkar")
        self.assertIn("review", res_rev["active_experts"])
        self.assertTrue(res_rev["telemetry"]["review"]["matched"])

if __name__ == "__main__":
    unittest.main()
