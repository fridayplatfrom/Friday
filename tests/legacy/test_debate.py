import unittest
import time
from tiny_experts.pipeline.debate_engine import MultiAgentDebateEngine
from tiny_experts.orchestrator import TinyExpertOrchestrator

class TestMultiAgentDebate(unittest.TestCase):
    def test_crossover_debate_matching(self):
        query = "How does the monarch caterpillar sequester toxic cardenolides from milkweed without dying?"
        active_experts = ["entomology", "toxicity", "ornithology"]
        
        debate = MultiAgentDebateEngine.evaluate_debate(
            query=query,
            active_experts=active_experts,
            aggregated_data={}
        )

        self.assertIsNotNone(debate)
        self.assertEqual(debate["status"], "CONSENSUS_VERIFIED")
        self.assertEqual(debate["consensus_score"], 100)
        self.assertEqual(debate["round_1_proposition"]["squad"], "entomology")
        self.assertEqual(debate["round_2_cross_examination"]["squad"], "toxicity")
        self.assertIn("Na+/K+-ATPase", debate["round_2_cross_examination"]["audit"])
        self.assertIn("100% Agreement", debate["final_consensus"])

    def test_dynamic_fallback_debate(self):
        query = "Evaluate physiological interactions in a diverse forest ecosystem"
        active_experts = ["botany", "ecology", "pathology", "format"]

        debate = MultiAgentDebateEngine.evaluate_debate(
            query=query,
            active_experts=active_experts,
            aggregated_data={}
        )

        self.assertIsNotNone(debate)
        self.assertEqual(debate["pattern_id"], "dynamic_cross_check")
        self.assertGreaterEqual(debate["consensus_score"], 95)

    def test_end_to_end_debate_latency_and_output(self):
        orchestrator = TinyExpertOrchestrator(verbose=False)
        query = "Can monarch caterpillars feed on toxic milkweed and become poisonous to avian predators?"

        start = time.perf_counter()
        detailed = orchestrator.process_detailed(query=query)
        duration_ms = (time.perf_counter() - start) * 1000

        # Assert thinking trace contains debate step
        self.assertIn("MULTI-AGENT CROSS-VERIFICATION & DEBATE", detailed["thinking_trace"])
        self.assertIn("Round 1 Proposition", detailed["thinking_trace"])
        self.assertIn("Round 2 Cross-Examination", detailed["thinking_trace"])
        
        # Assert rendered card contains consensus section
        self.assertIn("MULTI-AGENT CROSS-VERIFICATION & CONSENSUS", detailed["rendered_card"])

        # Crucial test: latency must remain ultra-lightweight (< 100 ms on 24-expert local CPU)
        print(f"\n[LATENCY BENCHMARK] Multi-Agent Cross-Verification finished in: {duration_ms:.2f} ms")
        self.assertLess(duration_ms, 100.0)

if __name__ == "__main__":
    unittest.main()
