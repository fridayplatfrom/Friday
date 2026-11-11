from ..matching import contains_any, contains_term
from typing import Any, Dict, List
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class BiologyReferenceLookup(BaseComponent):
    """Selects stored biology explanations and retrieves passages."""
    name = 'Biology Reference Lookup'
    description = 'Selects stored biology explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    BIOLOGICAL_MECHANISMS = {
        "phototropism": {
            "concept": "Phototropism & Phytohormone Signaling",
            "mechanism": "Light stimulates asymmetric migration of auxin to shaded stem cells, promoting cellular elongation toward the solar vector.",
            "cellular_pathway": "Acid growth hypothesis: Auxin triggers H+-ATPases, acidifying apoplast and activating expansins to loosen cellulose microfibrils.",
            "ecological_benefit": "Maximizes photosynthetic light capture for carbon fixation in Helianthus and other heliophilic angiosperms."
        },
        "coevolution": {
            "concept": "Chemical Ecology & Toxin Bio-Accumulation",
            "mechanism": "Plant defenses (e.g. cardenolides) drive selective mutations in herbivore Na+/K+ ATPase pumps, converting poisons into predator shields.",
            "cellular_pathway": "Single nucleotide polymorphisms in target transmembrane ion pumps confer toxin resistance without loss of cellular ion homeostasis.",
            "ecological_benefit": "Enables specialized niche partitioning between Danaus plexippus and Asclepias ecosystems."
        },
        "pollination": {
            "concept": "Eusocial Foraging & Energetics",
            "mechanism": "Acoustic communication and floral UV pigment recognition maximize pollen and nectar intake for colony thermoregulation.",
            "cellular_pathway": "High-rate glycogen and trehalose carbohydrate metabolism inside flight muscle mitochondria.",
            "ecological_benefit": "Facilitates cross-pollination across 80% of angiosperm plant species."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Biology Reference Lookup',
            description='Selects stored biology explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        # 1. Match core biological mechanisms
        matched_concept = None
        for key, data in self.BIOLOGICAL_MECHANISMS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "phototropism" and contains_any(combined, ["sun", "turn", "light", "track"])) \
               or (key == "coevolution" and contains_any(combined, ["caterpillar", "milkweed", "toxic", "immune"])) \
               or (key == "pollination" and contains_any(combined, ["bee", "nectar", "dance", "pollen"])):
                matched_concept = data
                break

        # 2. Search OpenStax biology textbook passages via BookEngine
        textbook_citations = self.book_engine.search(query=f"{species} {query}", shelf="biology", top_k=1)

        if not matched_concept and not textbook_citations:
            return {
                "relevant": False,
                "message": "No direct cellular or evolutionary mechanism queried."
            }

        citation = textbook_citations[0] if textbook_citations else None

        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "concept": matched_concept["concept"] if matched_concept else "General Biological Adaptation",
            "mechanism": matched_concept["mechanism"] if matched_concept else citation["text"],
            "cellular_pathway": matched_concept.get("cellular_pathway", "Cellular membrane signaling and enzymatic regulation.") if matched_concept else "Cellular membrane signaling and enzymatic regulation.",
            "textbook_citation": citation,
            "status": "reference_only",
            "reference_review_status": "unreviewed"
        }


# Compatibility for existing integrations and model-training imports.
BiologyExpert = BiologyReferenceLookup
