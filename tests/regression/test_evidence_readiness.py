"""Regression checks for epistemic claims; no network and no trained model needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tiny_experts.pipeline.harvester import ScientificDataHarvester
from tiny_experts.pipeline.market_economics_engine import MarketEconomicsEngine
from tiny_experts.pipeline.news_engine import NewsEngine
from tiny_experts.pipeline.taxonomic_graph import TaxonomicKnowledgeGraph
from tiny_experts.pipeline.visual_reference_atlas import VisualReferenceAtlas


class EvidenceTrainingReadinessTests(unittest.TestCase):
    def test_unrelated_wikipedia_summary_cannot_certify_edibility(self):
        example = {"title": "Unknown berry", "extract": "A potentially toxic berry was discovered.",
                   "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Berry"}}}
        with patch.object(ScientificDataHarvester, "fetch_wikipedia_summary", return_value=example):
            result = ScientificDataHarvester.harvest("unknown berry")
        self.assertEqual(result.hazard_level, "UNKNOWN")
        self.assertEqual(result.review_status, "unreviewed")
        self.assertNotIn("NON-TOXIC", result.toxin_notes.upper())
        self.assertIn("Not established", result.habitat)

    def test_ancestral_toxins_are_not_species_predictions(self):
        graph = TaxonomicKnowledgeGraph()
        result = graph.get_inherited_traits("Atropa belladonna")
        self.assertTrue(result["matched"])
        self.assertNotIn("active_compounds", result["inherited_traits"])
        self.assertFalse(result["hazard_inference_allowed"])
        self.assertIn("active_compounds", result["ancestral_trait_hints_unverified"])
        self.assertFalse(graph.get_inherited_traits("a")["matched"])

    def test_market_ratio_is_not_treatment_approval(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "market.json"
            path.write_text(json.dumps([{"crop": "Rice", "modal_price_per_quintal_inr": 2000,
                                         "average_yield_quintals_per_acre": 20}]), encoding="utf-8")
            econ = MarketEconomicsEngine(data_file=str(path))
            r = econ.evaluate_viability("Rice", 800)
            self.assertAlmostEqual(r["treatment_cost_to_assumed_gross_value_ratio"], .02)
            self.assertEqual(r["viability_status"], "NOT_ASSESSED")
            self.assertIn("No treatment", r["financial_advisory"])
            self.assertIsNone(econ.evaluate_viability("Unidentified crop"))

    def test_news_match_is_not_local_outbreak_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bulletins.json"
            path.write_text(json.dumps([{"date": "2026-11-01", "ttl_days": 14,
                                         "crops": ["rice"], "pathogens": []}]), encoding="utf-8")
            news = NewsEngine(news_file=str(path))
            r = news.evaluate_outbreaks(crop="rice", current_date_str="2026-11-05")
            self.assertTrue(r["bulletin_match"])
            self.assertFalse(r["local_outbreak_confirmed"])
            self.assertIsNone(r["is_active_outbreak"])
            self.assertIsNone(news.evaluate_outbreaks(crop="rice", current_date_str="2026-12-05"))

    def test_unverified_atlas_has_no_reference_citation(self):
        result = VisualReferenceAtlas.get_reference_plate("Early Blight")
        self.assertEqual(result["verification_status"], "unverified")
        self.assertIsNone(result["citation"])
        self.assertNotIn("page", result)
        self.assertIn("legacy_unverified_attribution", result)


if __name__ == "__main__":
    unittest.main()
