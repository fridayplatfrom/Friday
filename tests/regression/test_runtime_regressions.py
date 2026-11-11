import json
from types import SimpleNamespace

import pytest
from PIL import Image

from tiny_experts import TinyExpertOrchestrator
from tiny_experts.router import RouterModel
from tiny_experts.experts.vision_expert import VisionExpert
from tiny_experts.experts.pathology_expert import PathologyExpert
from tiny_experts.experts.toxicity_expert import ToxicityExpert


@pytest.mark.parametrize("question,expected,excluded", [
    ("Explain quantum mechanics.", {"mechanics"}, {"entomology", "toxicity"}),
    ("Research grammar.", set(), {"marine", "biology", "toxicity", "vision"}),
    ("What is electrical resistance?", {"electronics"}, {"microbiology", "pathology"}),
    ("Explain photosynthesis.", {"cell_biology"}, {"vision", "toxicity"}),
    ("12 + 8", {"math"}, {"biology"}),
])
def test_router_matches_capabilities_not_substrings(question, expected, excluded):
    actual = set(RouterModel().route(question))
    assert expected <= actual
    assert not actual & excluded


def test_unknown_toxicity_is_not_safe():
    result = ToxicityExpert(book_engine=object()).evaluate({"query": "Can I eat these unidentified wild berries?"})
    assert result["status"] == "unknown"
    assert result["is_hazardous"] is None
    assert "SAFE" not in result["hazard_level"]


def test_untrained_image_model_cannot_guess(tmp_path):
    expert = VisionExpert(model_dir=tmp_path)
    result = expert.evaluate({"image": Image.new("RGB", (32, 32)), "query": "Identify this leaf disease."})
    assert result["status"] == "unavailable"
    assert result["detected"] is False
    assert result["confidence"] is None


def test_hint_is_not_a_visual_prediction(tmp_path):
    result = VisionExpert(model_dir=tmp_path).evaluate({"hint_species": "Poison Ivy", "query": "What is it?"})
    assert result["source"] == "user_hint"
    assert result["confidence"] is None
    assert result["identity_verified"] is False


def test_pathology_negation_blocks_confident_false_diagnosis():
    classifier = SimpleNamespace(predict=lambda _: {"available": True, "abstained": False, "disease": "Early Blight", "disease_confidence": .99})
    books = SimpleNamespace(search=lambda **_: [])
    result = PathologyExpert(book_engine=books, classifier=classifier).evaluate({"query": "There are no lesions and my tomato is healthy."})
    assert result["status"] == "insufficient_evidence"
    assert result["diagnosis_confirmed"] is False
    assert result["clinical_treatment"] is None
    assert result["neural_confidence"] is None


def test_complete_numeric_and_unsupported_workflows():
    app = TinyExpertOrchestrator()
    numeric = app.process_detailed("12 + 8", session_id="math")
    assert numeric["telemetry"]["math"]["details"][0]["result"] == 20
    assert not numeric["telemetry"]["errors"]
    assert "<think>" not in numeric["thinking_trace"]
    unsupported = app.process_detailed("Correct this sentence: He go to school yesterday.", session_id="grammar")
    assert unsupported["telemetry"]["unsupported"]["status"] == "unsupported"
    assert unsupported["active_experts"] == []
    assert "100%" not in unsupported["final_output"]
    assert "verified" not in unsupported["human_narrative"].lower()
    json.loads(app.process("mass=500 g acceleration=2", session_id="physics", output_format="json"))


def test_upstream_results_and_taxonomy_reach_downstream_expert():
    app = TinyExpertOrchestrator()
    app.experts["botany"] = SimpleNamespace(evaluate=lambda _: {"status": "completed", "marker": "from_botany"})
    received = {}
    def observe(context):
        received.update(context)
        return {"status": "completed", "relevant": False}
    app.experts["pathology"] = SimpleNamespace(evaluate=observe)
    result = app.process_detailed("Poison Ivy plant disease", session_id="mesh")
    assert received["expert_results"]["botany"]["marker"] == "from_botany"
    assert received["botany_info"]["marker"] == "from_botany"
    assert received["taxonomic_lineage"] is not None
    order = result["telemetry"]["orchestration_meta"]["topological_order"]
    assert order.index("botany") < order.index("pathology")
    events = result["telemetry"]["execution_events"]
    assert events[-1]["stage"] == "communicator"
    assert not result["telemetry"]["errors"]


def test_sessions_do_not_inherit_each_others_subjects_and_reset_clears_memory():
    app = TinyExpertOrchestrator()
    app.process_detailed("Tell me about Common Sunflower", session_id="a")
    unrelated = app.process_detailed("Is it safe?", session_id="b")
    assert unrelated["detected_species"] is None
    assert not app.episodic_memory.get_observations(session_id="b")
    app.reset_session("a")
    assert app.episodic_memory.get_observations(session_id="a") == []
    assert app._get_session("a").last_species is None


def test_new_expert_registration_requires_a_real_bundle(tmp_path):
    app = TinyExpertOrchestrator()
    with pytest.raises(ValueError, match="bundle is unavailable"):
        app.register_neural_expert("genetics_topics", tmp_path, "genetics", ["dna"])
    assert "genetics_topics" not in app.experts
