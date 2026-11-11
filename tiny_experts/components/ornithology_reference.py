from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class OrnithologyReferenceLookup(BaseComponent):
    """Selects stored bird explanations and retrieves passages."""
    name = 'Ornithology Reference Lookup'
    description = 'Selects stored bird explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    ORITHOLOGICAL_CONCEPTS = {
        "flight_aerodynamics": {
            "title": "Avian Flight Biomechanics & Skeletal Pneumatization",
            "mechanism": "Asymmetric primary remiges generate aerodynamic lift via cambered airfoils; enlarged pectoralis muscles provide downstroke power anchored to an expanded sternal keel (carina).",
            "physiological_adaptation": "Trabecular hollow pneumatic bones reduce body mass without sacrificing torsional structural rigidity.",
            "ecological_significance": "Facilitates high-speed aerial predation, sustained long-distance soaring, and predator evasion."
        },
        "respiration": {
            "title": "Unidirectional Cross-Current Air Sac Respiration",
            "mechanism": "Inhaled air travels through posterior air sacs, flows continuously through parabronchi in a single direction, and exits via anterior air sacs across two full respiratory cycles.",
            "physiological_adaptation": "Blood flows perpendicular to airflow (cross-current exchange), enabling near-complete oxygen saturation even in hypoxic high-altitude flight.",
            "ecological_significance": "Provides the massive sustained metabolic oxygen delivery required for powered avian flight."
        },
        "navigation": {
            "title": "Quantum Cryptochrome & Geomagnetic Trans-Continental Navigation",
            "mechanism": "Migratory songbirds detect magnetic inclination angles via light-activated radical pair mechanisms in retinal cryptochrome proteins (Cry4).",
            "physiological_adaptation": "Calibrated against celestial star rotations and polarized twilight patterns during nocturnal migratory flights.",
            "ecological_significance": "Guides multi-thousand-kilometer trans-hemispheric journeys to exact natal or wintering territories with sub-kilometer fidelity."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Ornithology Reference Lookup',
            description='Selects stored bird explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.ORITHOLOGICAL_CONCEPTS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "flight_aerodynamics" and contains_any(combined, ["wing", "feather", "fly", "flight", "aerodynamics", "soar", "beak", "plumage", "bone", "bones"])) \
               or (key == "respiration" and contains_any(combined, ["lung", "air sac", "breath", "oxygen", "altitude"])) \
               or (key == "navigation" and contains_any(combined, ["bird", "eagle", "sparrow", "hawk", "owl", "migrate", "song", "nest"])):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="ornithology", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct avian or ornithological topics queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Ornithology (Avian Science)",
            "concept": matched["title"] if matched else "Avian Functional Morphology",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Avian physiological adaptation."),
            "physiological_adaptation": matched.get("physiological_adaptation", "High-efficiency metabolic and respiratory adaptations.") if matched else "Metabolic adaptation.",
            "ecological_significance": matched.get("ecological_significance", "Aviation and global migratory range.") if matched else "Global dispersal.",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
OrnithologyExpert = OrnithologyReferenceLookup
