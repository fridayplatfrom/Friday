"""Render completed expert results without claiming professional or factual verification."""
import json
from typing import Any, Dict, Optional
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine


class ResultRenderer(BaseComponent):
    """Converts completed structured results into deterministic prose."""
    name = 'Result Renderer'
    description = 'Converts completed structured results into deterministic prose.'
    component_kind = 'renderer'
    uses_neural_model = False
    updates_parameters_at_inference = False
    def __init__(self, book_engine: Optional[BookEngine] = None):
        super().__init__(name='Result Renderer', description='Converts completed structured results into deterministic prose.')
        self.book_engine = book_engine

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        results = context.get("aggregated_results") or context
        paragraphs = []
        unsupported = results.get("unsupported")
        if unsupported:
            paragraphs.append(unsupported["message"])
        pathology = results.get("pathology", {})
        if pathology.get("relevant"):
            if pathology.get("status") == "insufficient_evidence":
                paragraphs.append(pathology["message"])
            else:
                paragraphs.append(f"Condition reference: {pathology.get('pathology_condition')}. {pathology.get('message', '')}")
        toxicity = results.get("toxicity", {})
        if toxicity:
            paragraphs.append(toxicity.get("advisory", "Toxicity is not established."))
        vision = results.get("vision", {})
        if vision.get("message"):
            paragraphs.append(vision["message"])
        for key in ("math", "electronics", "mechanics", "thermodynamics"):
            result = results.get(key, {})
            for error in result.get("errors", []):
                paragraphs.append(f"{key.title()}: {error}")
            calculations = result.get("calculations")
            details = result.get("details")
            if calculations:
                paragraphs.append(f"{key.title()} calculation: {json.dumps(calculations, ensure_ascii=False)}")
            elif details:
                paragraphs.append(f"{key.title()} result: {json.dumps(details, ensure_ascii=False)}")
        librarian = results.get("librarian", {})
        if librarian.get("relevant"):
            books = librarian.get("matched_books", [])
            paragraphs.append("Matching catalog records: " + "; ".join(b.get("title", "Untitled") for b in books)
                              if books else "No matching source was found in the current catalog.")
        for key in ("genetics", "cell_biology", "biology", "marine", "microbiology", "evolution", "ecology",
                    "mycology", "entomology", "ornithology"):
            result = results.get(key, {})
            if result.get("relevant") and result.get("concept"):
                paragraphs.append(f"Reference topic: {result['concept']}. {result.get('mechanism', result.get('cellular_pathway', ''))}")
        botany = results.get('botany') or {}
        if botany.get('relevant'):
            facts = [str(botany[field]) for field in ('plant_name', 'recommendation', 'sunlight_requirement',
                     'watering_schedule', 'soil_profile') if botany.get(field)]
            if facts:
                paragraphs.append('Botanical reference: ' + '. '.join(facts))
        wildlife = results.get('wildlife') or {}
        if wildlife.get('relevant'):
            facts = [str(wildlife[field]) for field in ('animal_name', 'diet', 'behavior', 'habitat') if wildlife.get(field)]
            if facts:
                paragraphs.append('Wildlife reference: ' + '. '.join(facts))
        for expert_id, result in results.items():
            if isinstance(result, dict) and "model_predictions" in result:
                predictions = result.get("model_predictions", {})
                description = ", ".join(f"{head}: {value['label']}" for head, value in predictions.items())
                paragraphs.append(f"{expert_id}: {description or result.get('message', 'No accepted prediction')}.")
        if results.get("errors"):
            paragraphs.append("Some stages failed; the execution log identifies them. Their outputs were not used as successful results.")
        if not paragraphs:
            paragraphs.append("The matching reference modules ran. Their structured results and source records are shown below.")
        return {"status": "rendered", "persona_code": "result_communicator", "persona_title": "Component results",
                "persona_badge": "🔎", "tone": "Direct, with explicit uncertainty",
                "pedagogy_principles_applied": [], "speech_synthesis": "\n\n".join(paragraphs),
                "is_factual_verification": False, "language": "en"}


# Compatibility for existing integrations and model-training imports.
CommunicatorExpert = ResultRenderer
