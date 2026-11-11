from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class EcologyReferenceLookup(BaseComponent):
    """Selects stored ecology explanations and retrieves passages."""
    name = 'Ecology Reference Lookup'
    description = 'Selects stored ecology explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    ECOLOGICAL_CONCEPTS = {
        "trophic_cascade": {
            "title": "Trophic Cascades & Keystone Species Dynamics",
            "mechanism": "Top apex predators exert reciprocal predatory regulation down food chains, suppressing primary herbivores and releasing plant biomass from overgrazing.",
            "biogeochemical_impact": "Stabilizes riverbank soil morphology, promotes forest canopy regeneration, and increases carbon sequestration density.",
            "theoretical_model": "Top-down trophic regulation (Hairston, Smith, and Slobodkin hypothesis)"
        },
        "succession": {
            "title": "Ecological Succession & Seral Communities",
            "mechanism": "Predictable directional change in species composition over time following disturbance, progressing from pioneer lichens/mosses to climax hardwood forest canopies.",
            "biogeochemical_impact": "Progressive accumulation of organic soil humus, increased biological nitrogen fixation, and enhanced microclimate buffering.",
            "theoretical_model": "Facilitation, inhibition, and tolerance succession pathways"
        },
        "biogeochemical_cycles": {
            "title": "Biogeochemical Nutrient Cycling (N, C, P)",
            "mechanism": "Biological fixing of atmospheric nitrogen by symbiotic Rhizobium bacteria in plant nodules, coupled with fungal mycorrhizal mobilization of rock phosphate.",
            "biogeochemical_impact": "Regulates global photosynthetic carbon fixation limits and oceanic/terrestrial primary productivity.",
            "theoretical_model": "Stoichiometric nutrient limitation (Redfield ratio & Liebig's Law of the Minimum)"
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Ecology Reference Lookup',
            description='Selects stored ecology explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.ECOLOGICAL_CONCEPTS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "trophic_cascade" and contains_any(combined, ["predator", "prey", "keystone", "cascade", "food web", "food chain"])) \
               or (key == "succession" and contains_any(combined, ["succession", "pioneer", "climax", "disturbance", "biome"])) \
               or (key == "biogeochemical_cycles" and contains_any(combined, ["cycle", "nitrogen", "carbon", "phosphorus", "nutrient", "soil cycle"])):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="ecology", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct ecological system, trophic, or biogeochemical topics queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Ecology & Environmental Systems",
            "concept": matched["title"] if matched else "Ecosystem Dynamics & Stability",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Ecosystem energy transfer."),
            "biogeochemical_impact": matched.get("biogeochemical_impact", "Regulates nutrient availability and multi-species coexistence.") if matched else "Nutrient turnover.",
            "theoretical_model": matched.get("theoretical_model", "Trophic ecology and ecological network theory.") if matched else "Ecological network theory.",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
EcologyExpert = EcologyReferenceLookup
