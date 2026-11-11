import unittest
from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.biography_engine import BiographyEngine
from tiny_experts.pipeline.lexicon_engine import LexiconEngine
from tiny_experts.pipeline.consensus_ranking_engine import ConsensusRankingEngine
from tiny_experts.pipeline.web_directory_engine import UniversalWebDirectoryEngine
from tiny_experts.experts.biographer_expert import BiographerExpert

class TestWorldClassKnowledgePlatform(unittest.TestCase):
    """
    Verification suite for the Planetary Epistemic Knowledge Platform:
    - Universal People Registry & BiographerExpert (#24)
    - Multilingual Lexicon & Dictionary Engine
    - Multi-Source Consensus Ranking (Top-10, How-To, What-Is)
    - Authoritative Web & Statutory Directory (.gov, .edu, .org)
    """

    @classmethod
    def setUpClass(cls):
        cls.orchestrator = TinyExpertOrchestrator(verbose=False)
        cls.bio_engine = cls.orchestrator.biography_engine
        cls.lex_engine = cls.orchestrator.lexicon_engine
        cls.consensus_engine = cls.orchestrator.consensus_engine
        cls.web_engine = cls.orchestrator.web_directory_engine

    def test_01_total_expert_count(self):
        """Verify all 24 specialized micro-experts are loaded on local CPU."""
        self.assertEqual(len(self.orchestrator.experts), 24)
        self.assertIn("biographer", self.orchestrator.experts)
        self.assertIn("librarian", self.orchestrator.experts)
        self.assertIn("review", self.orchestrator.experts)
        self.assertIn("thermodynamics", self.orchestrator.experts)

    def test_02_biography_search_english_and_hindi(self):
        """Verify BiographyEngine retrieves thinker profiles in English and vernacular Hindi."""
        # English
        hits = self.bio_engine.search_people("Albert Einstein")
        self.assertTrue(len(hits) >= 1)
        self.assertEqual(hits[0]["person_id"], "albert_einstein")
        self.assertIn("Special Theory of Relativity", str(hits[0]["major_inventions_and_theories"]))

        # Hindi Vernacular
        hits_hi = self.bio_engine.search_people("आंबेडकर", lang="hi")
        self.assertTrue(len(hits_hi) >= 1)
        self.assertEqual(hits_hi[0]["person_id"], "dr_br_ambedkar")
        self.assertIn("भीमराव", hits_hi[0]["display_name"])

    def test_03_biography_theory_attribution(self):
        """Verify discovering the inventor or author of a physical or legal doctrine."""
        inventors = self.bio_engine.find_inventor_of("General Theory of Relativity")
        self.assertTrue(len(inventors) >= 1)
        self.assertEqual(inventors[0]["person_id"], "albert_einstein")

    def test_04_biographer_expert_evaluation(self):
        """Verify BiographerExpert returns complete profile and landmark quotes."""
        expert = BiographerExpert(biography_engine=self.bio_engine)
        res = expert.evaluate({"query": "Tell me about Richard Feynman"})
        self.assertTrue(res["matched"])
        self.assertEqual(res["primary_person"]["person_id"], "richard_feynman")
        self.assertIn("Quantum Electrodynamics", str(res["primary_person"]["disciplines"]))

    def test_05_lexicon_dictionary_lookups(self):
        """Verify multilingual dictionary provides definitions, etymology, and translations."""
        entry = self.lex_engine.lookup_term("entropy", lang="hi")
        self.assertIsNotNone(entry)
        self.assertIn("Rudolf Clausius", entry["etymology"])
        self.assertIn("hi", entry["multilingual_translations"])
        self.assertIn("एन्ट्रॉपी", entry["localized_term"])

        # Botanical term lookup
        entry_photo = self.lex_engine.lookup_term("photosynthesis", lang="mr")
        self.assertIsNotNone(entry_photo)
        self.assertIn("प्रकाशसंश्लेषण", entry_photo["localized_term"])

    def test_06_consensus_ranking_top_10(self):
        """Verify multi-source consensus Top-10 ranking with RRF scores."""
        top_lit = self.consensus_engine.find_top_10("top 10 literature books")
        self.assertIsNotNone(top_lit)
        self.assertEqual(top_lit["collection_id"], "top_10_world_literature")
        self.assertEqual(len(top_lit["ranked_items"]), 10)
        self.assertEqual(top_lit["ranked_items"][0]["title"], "War and Peace")
        self.assertEqual(top_lit["ranked_items"][1]["title"], "Gitanjali (Song Offerings)")

    def test_07_how_to_and_what_is_primers(self):
        """Verify procedural How-To and axiomatic What-Is primers."""
        how_to = self.consensus_engine.find_how_to("how to diagnose plant diseases")
        self.assertIsNotNone(how_to)
        self.assertTrue(len(how_to["steps"]) >= 4)

        what_is = self.consensus_engine.find_what_is("what is the basic structure doctrine")
        self.assertIsNotNone(what_is)
        self.assertIn("Kesavananda Bharati", what_is["authoritative_source"])

    def test_08_authoritative_web_directory(self):
        """Verify government statutory portals and university archives."""
        sites = self.web_engine.find_sites("supreme court constitution")
        self.assertTrue(len(sites) >= 1)
        self.assertEqual(sites[0]["authority_tier"], "TIER_1_GOV_STATUTORY")
        self.assertIn("gov.in", sites[0]["url"])

    def test_09_end_to_end_orchestration_biography_and_collections(self):
        """Verify end-to-end integration via TinyExpertOrchestrator."""
        # Query 1: Biography
        res_bio = self.orchestrator.process_detailed(query="Who was Sir C.V. Raman?")
        self.assertIn("biographer", res_bio["active_experts"])
        self.assertTrue(res_bio["telemetry"]["biographer"]["matched"])
        self.assertIn("Raman Effect", str(res_bio["telemetry"]["biographer"]["primary_person"]["major_inventions_and_theories"]))

        # Query 2: Top 10 list
        res_top = self.orchestrator.process_detailed(query="Show me top 10 books in world literature")
        self.assertIn("consensus_top_10", res_top["telemetry"])
        self.assertEqual(res_top["telemetry"]["consensus_top_10"]["collection_id"], "top_10_world_literature")

if __name__ == "__main__":
    unittest.main()
