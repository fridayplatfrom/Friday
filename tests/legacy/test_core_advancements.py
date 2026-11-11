import unittest
import time
from tiny_experts.pipeline.critic import ScientificCritic
from tiny_experts.pipeline.taxonomic_graph import TaxonomicKnowledgeGraph
from tiny_experts.pipeline.biochemical_engine import BiochemicalEngine
from tiny_experts.pipeline.bayesian_calibrator import BayesianCalibrator
from tiny_experts.pipeline.episodic_memory import EpisodicMemory
from tiny_experts.orchestrator import TinyExpertOrchestrator

class TestCoreAdvancements(unittest.TestCase):
    def test_scientific_critic(self):
        aggregated = {
            "toxicity": {"is_hazardous": True, "toxic_agent": "Urushiol", "hazard_level": "HIGH"},
            "botany": {"care_instructions": "Prune foliage with bare hands in summer."},
            "marine": {"relevant": True},
            "math": {"area_sq_meters": 10, "spacing_meters": 2, "total_capacity": 500} # physically impossible
        }
        res = ScientificCritic.audit_and_correct(aggregated, query="How to prune this?")
        self.assertFalse(res["audit_passed"])
        self.assertGreaterEqual(len(res["corrections_applied"]), 2)
        self.assertIn("protective equipment", aggregated["botany"]["care_instructions"])
        self.assertLessEqual(aggregated["math"]["total_capacity"], 10)

    def test_taxonomic_knowledge_graph(self):
        graph = TaxonomicKnowledgeGraph()
        
        # Test Poison Ivy trait inheritance from Anacardiaceae
        ivy_traits = graph.get_inherited_traits("Poison Ivy")
        self.assertTrue(ivy_traits["matched"])
        self.assertIn("urushiol", ivy_traits["inherited_traits"]["active_compounds"])
        self.assertIn("Type IV", ivy_traits["inherited_traits"]["hazard_effect"])

        # Test Deadly Nightshade trait inheritance from Solanaceae
        nightshade_traits = graph.get_inherited_traits("Atropa belladonna")
        self.assertTrue(nightshade_traits["matched"])
        self.assertIn("atropine", nightshade_traits["inherited_traits"]["active_compounds"])

    def test_biochemical_pathway_and_drug_interaction(self):
        # Query with willow and aspirin
        res = BiochemicalEngine.evaluate(
            query="My dog is on aspirin. Is it safe to chew on a willow stick?",
            species_name="Salix alba",
            chemical_name="salicin"
        )
        self.assertIsNotNone(res)
        self.assertIn("Cyclooxygenase", res["pathway_name"])
        self.assertTrue(res["has_severe_drug_interaction"])
        self.assertIn("Synthetic NSAIDs", res["detected_drug_interactions"][0]["class"])

    def test_bayesian_calibrator(self):
        # Query describing wild mushroom with white gills
        res = BayesianCalibrator.evaluate(
            query="Found a wild mushroom with white gills and a ring in the woods. Can I eat it?",
            detected_species="mushroom"
        )
        self.assertIsNotNone(res)
        self.assertTrue(res["ambiguity_detected"])
        self.assertIn("Amanita", res["calibrated_posterior"][0]["candidate"])
        self.assertIn("SPORE PRINT", res["differentiator_test"])

    def test_episodic_memory(self):
        mem = EpisodicMemory()
        ctx = mem.retrieve_context_for_query("Can I take my dog hiking around these plants?")
        self.assertTrue(ctx["has_relevant_profile"])
        self.assertGreaterEqual(len(ctx["pets"]), 1)
        self.assertEqual(ctx["pets"][0]["name"], "Max")
        self.assertEqual(ctx["pets"][0]["species"], "dog")

    def test_end_to_end_orchestrator_latency_and_features(self):
        orchestrator = TinyExpertOrchestrator(verbose=False)
        query = "Can my dog Max chew on willow bark if they are taking aspirin?"

        start = time.perf_counter()
        detailed = orchestrator.process_detailed(query=query)
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\n[LATENCY BENCHMARK: ALL 5 CORE ENGINES ACTIVE] Latency: {duration_ms:.2f} ms")
        self.assertIn("EPISODIC CONTEXT", detailed["thinking_trace"])
        self.assertIn("BIOCHEMICAL PATHWAY", detailed["thinking_trace"])
        self.assertIn("SCIENTIFIC CRITIC", detailed["thinking_trace"])
        self.assertLess(duration_ms, 30.0)

if __name__ == "__main__":
    unittest.main()
