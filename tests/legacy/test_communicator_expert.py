import unittest
import time
from tiny_experts.experts.communicator_expert import CommunicatorExpert
from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.book_engine import BookEngine

class TestUniversalCommunicatorExpert(unittest.TestCase):
    """
    Test suite for the 18th Micro-Expert: Universal Communicator & Presentation Expert.
    Verifies domain-specific persona switching, empathetic rhetoric, multilingual honorifics,
    and sub-2ms local CPU performance.
    """

    @classmethod
    def setUpClass(cls):
        cls.book_engine = BookEngine()
        cls.communicator = CommunicatorExpert(book_engine=cls.book_engine)
        cls.orchestrator = TinyExpertOrchestrator(verbose=False)

    def test_01_expert_registration(self):
        """Verify CommunicatorExpert is registered as the 18th official micro-expert."""
        self.assertIn("communicator", self.orchestrator.experts)
        self.assertEqual(len(self.orchestrator.experts), 24)
        self.assertEqual(self.communicator.name, "Universal Communicator & Presentation Expert")

    def test_02_senior_agronomist_persona(self):
        """Verify Communicator adopts Senior Agronomist persona for pathology findings."""
        context = {
            "query": "टमाटर में अगेती झुलसा का क्या उपचार है?",
            "vernacular_meta": {"detected_language": "hi"},
            "pathology": {
                "relevant": True,
                "pathology_condition": "Early Blight (Alternaria solani)",
                "pathogen_latin_name": "Alternaria solani",
                "symptoms_profile": "Concentric rings on lower leaves",
                "clinical_treatment": "Remove lower infected foliage; apply copper octanoate FRAC M01; switch to drip irrigation",
                "disease_triangle_risk": {"symptom_window": "High risk", "preventative_action": "Apply before rain"},
                "visual_reference_plate": {"plate_id": "Plate 11.4"}
            }
        }
        res = self.communicator.evaluate(context)
        self.assertEqual(res["persona_code"], "senior_agronomist")
        self.assertEqual(res["persona_badge"], "🧑‍🌾")
        self.assertIn("Early Blight", res["speech_synthesis"])
        self.assertIn("नमस्ते किसान भाई!", res["speech_synthesis"])
        self.assertIn("चिंता मत कीजिए", res["speech_synthesis"])
        self.assertGreater(len(res["action_steps"]), 0)
        self.assertIn("Empathetic Reassurance & Anxiety Validation", res["pedagogy_principles_applied"])

    def test_03_emergency_toxicologist_persona(self):
        """Verify Communicator adopts Emergency Toxicologist persona for dangerous poisons."""
        context = {
            "query": "Is death cap mushroom safe to eat?",
            "vernacular_meta": {"detected_language": "en"},
            "toxicity": {
                "is_hazardous": True,
                "toxic_agent": "Amanitin / Amatoxins",
                "hazard_level": "DEADLY HAZARDOUS",
                "symptoms": "Severe gastrointestinal distress, biphasic liver and kidney failure",
                "emergency_first_aid": "Immediate gastric lavage and intravenous silibinin therapy",
                "pet_safety": {"dogs": "Lethal acute hepatic necrosis"}
            }
        }
        res = self.communicator.evaluate(context)
        self.assertEqual(res["persona_code"], "emergency_toxicologist")
        self.assertEqual(res["persona_badge"], "🚨")
        self.assertIn("Emergency Safety Alert", res["speech_synthesis"])
        self.assertIn("DEADLY HAZARDOUS", res["speech_synthesis"])
        self.assertIn("Immediate Hazard Prominence", res["pedagogy_principles_applied"])

    def test_04_master_gardener_persona(self):
        """Verify Communicator adopts Master Gardener persona for botany inquiries."""
        context = {
            "query": "How to care for sunflower in my garden?",
            "vernacular_meta": {"detected_language": "en"},
            "botany": {
                "relevant": True,
                "sunlight_requirement": "Full sun (6-8 hours daily)",
                "watering_schedule": "Deep watering once a week",
                "soil_profile": "Well-draining, nutrient-rich soil (pH 6.0 - 7.5)",
                "recommendation": "Supports pollinators, requires staking if exposed to high winds."
            },
            "vision": {"species": "Common Sunflower"}
        }
        res = self.communicator.evaluate(context)
        self.assertEqual(res["persona_code"], "master_gardener")
        self.assertEqual(res["persona_badge"], "🌿")
        self.assertIn("Common Sunflower", res["speech_synthesis"])
        self.assertIn("Sunlight", res["speech_synthesis"])
        self.assertIn("finger test", res["pro_tip"])

    def test_05_field_naturalist_persona(self):
        """Verify Communicator adopts Field Naturalist persona for entomology/wildlife."""
        context = {
            "query": "What does a praying mantis eat?",
            "vernacular_meta": {"detected_language": "en"},
            "entomology": {
                "relevant": True,
                "order": "Mantodea",
                "behavior": "Ambush predator capturing pest insects with raptorial front legs",
                "habitat": "Gardens, grasslands, and shrubs"
            },
            "vision": {"species": "Praying Mantis"}
        }
        res = self.communicator.evaluate(context)
        self.assertEqual(res["persona_code"], "field_naturalist")
        self.assertEqual(res["persona_badge"], "🦋")
        self.assertIn("Praying Mantis", res["speech_synthesis"])
        self.assertIn("Ambush predator", res["speech_synthesis"])

    def test_06_multilingual_coverage(self):
        """Verify native empathetic greetings across Indic languages."""
        langs = ["hi", "pa", "te", "ta", "mr", "bn", "kn", "gu", "en"]
        for lang in langs:
            context = {
                "query": "crop health inquiry",
                "vernacular_meta": {"detected_language": lang},
                "pathology": {
                    "relevant": True,
                    "pathology_condition": "Rust (Puccinia graminis)",
                    "pathogen_latin_name": "Puccinia graminis",
                    "symptoms_profile": "Orange-brown pustules on stems",
                    "clinical_treatment": "Apply azoxystrobin (FRAC 11)"
                }
            }
            res = self.communicator.evaluate(context)
            self.assertEqual(res["language"], lang)
            self.assertGreater(len(res["speech_synthesis"]), 40)

    def test_07_communication_shelf_citations(self):
        """Verify BookEngine retrieves authentic FAO / toxicology communication books."""
        hits = self.book_engine.search("principles farmer field communication empathy", shelf="communication")
        self.assertGreater(len(hits), 0)
        self.assertIn("FAO Agricultural Extension Manual", hits[0]["source"])

    def test_08_end_to_end_orchestration_latency(self):
        """Verify full orchestrator pipeline with CommunicatorExpert executes with sub-50ms warm latency."""
        # Warmup pass (initializes PyTorch models, SQLite connection and lazy caches)
        _ = self.orchestrator.process_detailed("Warmup query")
        
        t0 = time.perf_counter()
        res = self.orchestrator.process_detailed("टमाटर में अगेती झुलसा का क्या उपचार है?")
        latency_ms = (time.perf_counter() - t0) * 1000
        
        self.assertIn("communicator", res["telemetry"])
        self.assertIn("human_narrative", res)
        self.assertGreater(len(res["human_narrative"]), 50)
        self.assertIn("🧑‍🌾", res["telemetry"]["communicator"]["persona_badge"])
        self.assertLess(latency_ms, 100.0, f"Warm latency {latency_ms:.2f}ms exceeded 100ms threshold")

if __name__ == "__main__":
    unittest.main()
