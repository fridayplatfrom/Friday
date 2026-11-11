from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class MarineBiologyReferenceLookup(BaseComponent):
    """Selects stored marine-biology explanations and retrieves passages."""
    name = 'Marine Biology Reference Lookup'
    description = 'Selects stored marine-biology explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    MARINE_CONCEPTS = {
        "coral_bleaching": {
            "title": "Scleractinian Coral Calcification & Thermal Bleaching",
            "mechanism": "Thermal stress induces photoinhibition in dinoflagellate endosymbionts (Symbiodiniaceae), generating cytotoxic reactive oxygen species (ROS) that force coral hosts to expel symbionts, exposing white aragonite skeletons.",
            "ocean_impact": "Loss of structural reef architecture degrades habitat for 25 percent of all marine organisms.",
            "biogeochemical_role": "Carbonate saturation state (Omega-aragonite) dictates biogenic calcification rates."
        },
        "phytoplankton": {
            "title": "Phytoplankton Primary Productivity & The Biological Carbon Pump",
            "mechanism": "Unicellular marine diatoms, dinoflagellates, and cyanobacteria fix dissolved inorganic carbon via RuBisCO in the sunlit photic zone.",
            "ocean_impact": "Generates >50% of atmospheric oxygen and exports particulate organic carbon into the deep bathypelagic abyss.",
            "biogeochemical_role": "Marine nutrient limitation dictated by iron, nitrate, and silicate ratios (Redfield stoichiometry)."
        },
        "hydrothermal_vents": {
            "title": "Chemolithoautotrophy at Deep-Sea Hydrothermal Vents",
            "mechanism": "Sulfur-oxidizing bacteria (Thiomicrospira) utilize chemical energy from toxic hydrogen sulfide (H2S) exiting hydrothermal chimneys to fix carbon without sunlight.",
            "ocean_impact": "Supports dense abyssal benthic communities including giant tube worms (Riftia pachyptila) harboring symbiotic trophosomes.",
            "biogeochemical_role": "Primary energy input in the aphotic benthic biosphere."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Marine Biology Reference Lookup',
            description='Selects stored marine-biology explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.MARINE_CONCEPTS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "coral_bleaching" and contains_any(combined, ["coral", "reef", "bleach", "bleaching", "zooxanthellae", "polyps"])) \
               or (key == "phytoplankton" and contains_any(combined, ["plankton", "phytoplankton", "algae", "diatom", "kelp", "ocean oxygen"])) \
               or (key == "hydrothermal_vents" and contains_any(combined, ["vent", "deep sea", "abyss", "chemosynthesis", "tube worm"])):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="marine", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct marine, oceanic, or aquatic ecology topics queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Marine Biology & Oceanography",
            "concept": matched["title"] if matched else "Marine Ecosystem & Pelagic Dynamics",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Marine biological process."),
            "oceanographic_impact": matched.get("ocean_impact", "Global marine biological diversity and carbon cycling.") if matched else "Marine biological diversity.",
            "biogeochemical_role": matched.get("biogeochemical_role", "Oceanic nutrient and carbonate flux.") if matched else "Marine nutrient flux.",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
MarineBiologyExpert = MarineBiologyReferenceLookup
