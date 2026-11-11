from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class MycologyReferenceLookup(BaseComponent):
    """Selects stored fungi explanations and retrieves passages."""
    name = 'Mycology Reference Lookup'
    description = 'Selects stored fungi explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    MYCOLOGICAL_CONCEPTS = {
        "mycorrhizae": {
            "title": "Mycorrhizal Symbiosis & Wood-Wide Underground Networks",
            "mechanism": "Fungal hyphae penetrate (endomycorrhizae) or sheath (ectomycorrhizae) plant roots, acting as an extended root system that mines inorganic phosphorus and water in exchange for plant carbon.",
            "ecological_role": "Connects multi-species forest canopies into continuous biological networks facilitating inter-tree chemical communication and nutrient redistribution.",
            "fungal_taxa": "Glomeromycota (arbuscular) & Basidiomycota/Ascomycota (ectomycorrhizal)"
        },
        "decomposition": {
            "title": "Saprotrophic Enzymatic Decomposition",
            "mechanism": "White-rot and brown-rot fungi secrete oxidative lignin peroxidases, laccases, and endoglucanases to enzymatically break down recalcitrant lignocellulose polymers in dead wood.",
            "ecological_role": "Primary driver of terrestrial carbon cycling; returns locked organic carbon, nitrogen, and minerals to the forest floor humus layer.",
            "fungal_taxa": "Wood-decay Polyporales & Agaricales"
        },
        "lichen": {
            "title": "Lichenized Composite Symbiosis",
            "mechanism": "Mutualistic integration of a fungal mycobiont (provides structural shelter, moisture retention, and minerals) with a photosynthetic photobiont (alga or cyanobacterium producing sugars).",
            "ecological_role": "Pioneer organisms in primary ecological succession capable of biological weathering of bare rock into primitive soil substrate.",
            "fungal_taxa": "Lecanoromycetes (Ascomycota)"
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Mycology Reference Lookup',
            description='Selects stored fungi explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.MYCOLOGICAL_CONCEPTS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "mycorrhizae" and contains_any(combined, ["fungus", "fungi", "mushroom", "mycelium", "hyphae", "network", "root"])) \
               or (key == "decomposition" and contains_any(combined, ["rot", "decay", "spoil", "decomposer"])) \
               or (key == "lichen" and "lichen" in combined):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="mycology", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct fungal, mycelial, or mycology topics queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Mycology & Fungal Biology",
            "concept": matched["title"] if matched else "Fungal Ecological Adaptations",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Fungal mycelial nutrient absorption."),
            "ecological_role": matched.get("ecological_role", "Essential decomposer and mutualistic root associate.") if matched else "Decomposition & soil cycling.",
            "taxa_group": matched.get("fungal_taxa", "Fungi (Kingdom)") if matched else "Kingdom Fungi",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
MycologyExpert = MycologyReferenceLookup
