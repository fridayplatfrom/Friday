import unittest
import os
import sys
import time
from PIL import Image

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tiny_experts.pipeline.figure_extractor import FigureExtractor
from tiny_experts.pipeline.visual_reference_atlas import VisualReferenceAtlas
from tiny_experts.pipeline.multilingual_normalizer import MultilingualVernacularNormalizer
from tiny_experts.pipeline.chemical_regulatory_registry import ChemicalRegulatoryRegistry
from tiny_experts.pipeline.disease_triangle_engine import DiseaseTriangleEngine
from tiny_experts.experts.vision_expert import VisionExpert
from tiny_experts.orchestrator import TinyExpertOrchestrator

class TestAllAdvancedFrontiers(unittest.TestCase):
    """
    Comprehensive test suite validating all 7 Advanced Scientific & Agricultural Frontiers:
    1. PDF Figure & Diagram Extractor
    2. Visual Reference Atlas (Textbook Plates & Hallmarks)
    3. PlantVillage Curated Leaf Benchmark Dataset
    4. MobileNetV3-Small Leaf Vision Head
    5. Multilingual Vernacular Engine (Hindi, Punjabi, Telugu, Tamil, Marathi)
    6. Government Portal Integration (CIBRC / EPA Legal Chemical Registry & PHI)
    7. Weather Trigger / Disease Triangle Outbreak Engine
    """

    @classmethod
    def setUpClass(cls):
        print("\n========================================================")
        print("  [TEST SUITE] ADVANCED AGRICULTURAL & CLINICAL FRONTIERS")
        print("========================================================")
        cls.orchestrator = TinyExpertOrchestrator(verbose=False)

    # ----------------------------------------------------
    # FRONTIER 1: Figure Extractor & Catalog
    # ----------------------------------------------------
    def test_frontier_1_figure_extractor_and_catalog(self):
        extractor = FigureExtractor()
        catalog = extractor.load_catalog()
        self.assertGreater(len(catalog), 0, "Figure catalog should contain registered plates/figures.")
        
        # Verify catalog entry structure
        first_entry = catalog[0]
        self.assertIn("figure_label", first_entry)
        self.assertIn("disease", first_entry)
        self.assertIn("filename", first_entry)
        self.assertTrue(os.path.exists(os.path.join(extractor.figures_dir, first_entry["filename"])))

    # ----------------------------------------------------
    # FRONTIER 2: Visual Reference Atlas
    # ----------------------------------------------------
    def test_frontier_2_visual_reference_atlas(self):
        # 1. Test Fungal Plate (Early Blight)
        plate_eb = VisualReferenceAtlas.get_reference_plate("Early Blight")
        self.assertIsNotNone(plate_eb)
        self.assertIn("Agrios", plate_eb["book"])
        self.assertIn("concentric", plate_eb["hallmarks"].lower())
        self.assertTrue(plate_eb["exists_locally"], "Plate image should exist locally on disk.")

        # 2. Test Bacterial Plate (Rice BLB)
        plate_blb = VisualReferenceAtlas.get_reference_plate("Rice Bacterial Leaf Blight")
        self.assertIsNotNone(plate_blb)
        self.assertIn("ICAR", plate_blb["book"])
        self.assertTrue(plate_blb["exists_locally"])

        # 3. Test Abiotic Plate (Blossom End Rot)
        plate_ber = VisualReferenceAtlas.get_reference_plate("Blossom End Rot")
        self.assertIsNotNone(plate_ber)
        self.assertIn("Plate 14.1", plate_ber["plate_id"])

        # 4. Verify End-to-End Orchestrator attaches Visual Reference
        res = self.orchestrator.process_detailed(query="Tomato leaves have concentric target rings with yellow halo")
        path_data = res["telemetry"].get("pathology", {})
        self.assertTrue(path_data.get("relevant"))
        self.assertIsNotNone(path_data.get("visual_reference_plate"))
        self.assertIn("Visual Ref: [Plate", res["rendered_card"])

    # ----------------------------------------------------
    # FRONTIER 3: Leaf Benchmark Dataset
    # ----------------------------------------------------
    def test_frontier_3_leaf_benchmark_dataset(self):
        benchmark_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tiny_experts", "data", "images", "leaf_benchmark"
        )
        self.assertTrue(os.path.exists(benchmark_dir), "Benchmark directory must exist.")
        
        expected_classes = ["early_blight", "late_blight", "powdery_mildew", "bacterial_spot", "healthy"]
        for c in expected_classes:
            class_path = os.path.join(benchmark_dir, c)
            self.assertTrue(os.path.exists(class_path), f"Class directory '{c}' missing.")
            images = [f for f in os.listdir(class_path) if f.endswith((".jpg", ".png", ".jpeg"))]
            self.assertGreaterEqual(len(images), 10, f"Class '{c}' must have at least 10 sample images.")
            
            # Verify image format and readability
            with Image.open(os.path.join(class_path, images[0])) as sample_img:
                self.assertIn(sample_img.size, [(224, 224), (256, 256)])

    # ----------------------------------------------------
    # FRONTIER 4: MobileNetV3-Small Leaf Vision Head
    # ----------------------------------------------------
    def test_frontier_4_mobilenet_leaf_vision(self):
        vision_expert = VisionExpert()
        sample_leaf_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "tiny_experts", "data", "images", "leaf_benchmark", "early_blight", "sample_early_blight_01.jpg"
        )
        self.assertTrue(os.path.exists(sample_leaf_path))

        start = time.perf_counter()
        res = vision_expert.evaluate({
            "image": sample_leaf_path,
            "query": "Diagnose this tomato leaf condition."
        })
        latency_ms = (time.perf_counter() - start) * 1000

        self.assertTrue(res.get("detected"))
        self.assertEqual(res.get("source"), "mobilenet_leaf_vision_head")
        self.assertIn(res.get("category"), ["plant_pathology", "plant"])
        self.assertLess(latency_ms, 150.0, f"Vision CPU latency must be <150ms on cold start, got {latency_ms:.2f}ms")

    # ----------------------------------------------------
    # FRONTIER 5: Multilingual Vernacular Engine (5 Regional Languages)
    # ----------------------------------------------------
    def test_frontier_5_multilingual_vernacular_engine(self):
        # 1. Hindi (Devanagari)
        hi_res = MultilingualVernacularNormalizer.normalize("टमाटर में अगेती झुलसा के लक्षण")
        self.assertEqual(hi_res["detected_language"], "hi")
        self.assertEqual(hi_res["canonical_disease"], "Early Blight")
        self.assertIn("tomato", hi_res["detected_crops"])

        # 2. Punjabi (Gurmukhi)
        pa_res = MultilingualVernacularNormalizer.normalize("ਕਣਕ ਵਿੱਚ ਕੁੰਗੀ ਰੋਗ ਦਾ ਹੱਲ")
        self.assertEqual(pa_res["detected_language"], "pa")
        self.assertEqual(pa_res["canonical_disease"], "Black Stem Rust")
        self.assertIn("wheat", pa_res["detected_crops"])

        # 3. Telugu (తెలుగు)
        te_res = MultilingualVernacularNormalizer.normalize("వరి లో ఎండ్ర తెగులు నివారణ")
        self.assertEqual(te_res["detected_language"], "te")
        self.assertEqual(te_res["canonical_disease"], "Rice Bacterial Leaf Blight")
        self.assertIn("rice", te_res["detected_crops"])

        # 4. Tamil (தமிழ்)
        ta_res = MultilingualVernacularNormalizer.normalize("கரும்பில் செவ்வழுகல் நோய் தாக்குதல்")
        self.assertEqual(ta_res["detected_language"], "ta")
        self.assertEqual(ta_res["canonical_disease"], "Sugarcane Red Rot")
        self.assertIn("sugarcane", ta_res["detected_crops"])

        # 5. Marathi (मराठी)
        mr_res = MultilingualVernacularNormalizer.normalize("सोयाबीन पिकावर करपा आणि भुरी रोग")
        self.assertEqual(mr_res["detected_language"], "mr")
        self.assertIn(mr_res["canonical_disease"], ["Early Blight", "Powdery Mildew"])

        # 6. Transliterated / Romanized Vernacular Query
        trans_res = MultilingualVernacularNormalizer.normalize("tamatar me pacheti jhulsa rog kaise thik kare?")
        self.assertEqual(trans_res["canonical_disease"], "Late Blight")

        # 7. End-to-End Orchestrator Multilingual Advisory
        out = self.orchestrator.process("टमाटर में अगेती झुलसा का उपचार")
        self.assertIn("REGIONAL MULTILINGUAL ADVISORY: HI", out)
        self.assertIn("Early Blight", out)

    # ----------------------------------------------------
    # FRONTIER 6: Government Portal Integration (CIBRC / EPA Registry)
    # ----------------------------------------------------
    def test_frontier_6_cibrc_epa_chemical_registry(self):
        # 1. Test Banned Pesticide: Endosulfan
        audit_endo = ChemicalRegulatoryRegistry.audit_chemical("Endosulfan")
        self.assertFalse(audit_endo["is_legal"])
        self.assertTrue(audit_endo["is_banned"])
        self.assertIn("BANNED", audit_endo["status"])
        self.assertIn("Chlorantraniliprole", audit_endo["recommended_substitute"])

        # 2. Test Banned Pesticide on Vegetables: Monocrotophos
        audit_mono = ChemicalRegulatoryRegistry.audit_chemical("Monocrotophos")
        self.assertFalse(audit_mono["is_legal"])
        self.assertIn("VEGETABLES", audit_mono["status"])

        # 3. Test Approved Active & PHI: Copper Hydroxide
        audit_cu = ChemicalRegulatoryRegistry.audit_chemical("Copper Hydroxide")
        self.assertTrue(audit_cu["is_legal"])
        self.assertEqual(audit_cu["phi_days"], 0)
        self.assertEqual(audit_cu["frac_group"], "FRAC M01 (Multi-site inorganic copper)")

        # 4. Test Approved Active & PHI: Mancozeb
        audit_manc = ChemicalRegulatoryRegistry.audit_chemical("Mancozeb")
        self.assertTrue(audit_manc["is_legal"])
        self.assertEqual(audit_manc["phi_days"], 7)

        # 5. End-to-End Violation Interception in Orchestrator
        banned_query = "Can I spray Endosulfan or Monocrotophos on tomato early blight?"
        banned_card = self.orchestrator.process(banned_query)
        self.assertIn("LEGAL & STATUTORY REGULATORY ALERT: BANNED PESTICIDE", banned_card)
        self.assertIn("PROHIBITED BY CIBRC/EPA", banned_card)

    # ----------------------------------------------------
    # FRONTIER 7: Weather Trigger / Disease Triangle Outbreak Engine
    # ----------------------------------------------------
    def test_frontier_7_weather_disease_triangle_engine(self):
        # 1. Late Blight Emergency High Risk (Wallin SV >= 3)
        res_high = DiseaseTriangleEngine.evaluate_outbreak_risk(
            disease_name="Late Blight",
            temp_c=18.0,
            rh_percent=94.0,
            leaf_wetness_hours=17.0
        )
        self.assertIsNotNone(res_high)
        self.assertEqual(res_high["risk_level"], "EMERGENCY HIGH RISK")
        self.assertGreaterEqual(res_high["outbreak_probability_pct"], 90.0)
        self.assertIn("SV 3/4", res_high["severity_value"])
        self.assertIn("mandipropamid", res_high["preventative_action"])

        # 2. Late Blight Low Risk (Dry Canopy)
        res_low = DiseaseTriangleEngine.evaluate_outbreak_risk(
            disease_name="Late Blight",
            temp_c=22.0,
            rh_percent=55.0,
            leaf_wetness_hours=1.0
        )
        self.assertEqual(res_low["risk_level"], "LOW RISK")
        self.assertEqual(res_low["severity_value"], "SV 0/4")

        # 3. Powdery Mildew Meteorological Divergence (Warm, dry foliage, humid air)
        res_pm = DiseaseTriangleEngine.evaluate_outbreak_risk(
            disease_name="Powdery Mildew",
            temp_c=24.0,
            rh_percent=75.0,
            leaf_wetness_hours=1.0 # Dry leaves
        )
        self.assertEqual(res_pm["risk_level"], "EMERGENCY HIGH RISK")
        self.assertIn("potassium bicarbonate", res_pm["preventative_action"])

        # 4. End-to-End Natural Language Weather Extraction & Trigger in Orchestrator
        weather_query = "Tomato late blight risk under temp 18C, 95% humidity, and leaf wetness 18 hours?"
        weather_card = self.orchestrator.process(weather_query)
        self.assertIn("WEATHER EPIDEMIOLOGY: EMERGENCY HIGH RISK", weather_card)
        self.assertIn("Wallin's Severity Value", weather_card)

if __name__ == "__main__":
    unittest.main()
