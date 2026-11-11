import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tiny_experts.router import RouterModel
from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.book_engine import BookEngine
from tiny_experts.pipeline.session_memory import SessionMemory

class TestAdvancedFrontierFeatures(unittest.TestCase):

    def setUp(self):
        self.orchestrator = TinyExpertOrchestrator()
        self.session = SessionMemory()

    def test_deepseek_r1_thinking_trace(self):
        output = self.orchestrator.process(
            query="Is poison ivy dangerous to touch?",
            hint_species="Poison Ivy",
            show_thinking=True,
            output_format="card"
        )
        # Verify <think> and </think> tags
        self.assertIn("<think>", output)
        self.assertIn("</think>", output)
        self.assertIn("[STEP 3: MULTI-EXPERT ROUTING]", output)
        self.assertIn("SAFETY & TOXICITY AUDIT", output)

    def test_conversational_session_memory_resolution(self):
        session_id = "test_memory_session"

        # Turn 1: Discuss Sunflower
        turn_1 = self.orchestrator.process(
            query="Tell me about Common Sunflower care and sunlight.",
            hint_species="Common Sunflower",
            session_id=session_id
        )
        self.assertIn("Common Sunflower", turn_1)

        # Turn 2: Follow-up question using pronoun "it" without repeating species name!
        turn_2 = self.orchestrator.process(
            query="Is it safe for my dog if they eat the petals?",
            session_id=session_id
        )
        # Should resolve "it" to Common Sunflower from memory!
        self.assertIn("Common Sunflower", turn_2)
        self.assertIn("SAFE / NON-TOXIC", turn_2)
        self.assertIn("CONTEXT RESOLUTION", turn_2)

    def test_autonomous_tool_calling_flow(self):
        # Verify that orchestrator handles tool flow without crashing
        output = self.orchestrator.process(
            query="Tell me about Lavandula",
            hint_species="Lavandula",
            output_format="json"
        )
        self.assertIn('"orchestration_meta"', output)

if __name__ == "__main__":
    unittest.main()
