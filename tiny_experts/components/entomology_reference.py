from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class EntomologyReferenceLookup(BaseComponent):
    """Selects stored insect explanations and retrieves passages."""
    name = 'Entomology Reference Lookup'
    description = 'Selects stored insect explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    ENTOMOLOGICAL_CONCEPTS = {
        "metamorphosis": {
            "title": "Complete (Holometabolous) Metamorphosis",
            "mechanism": "Life cycle progression through four distinct ontogenetic stages: egg, feeding larva, quiescent pupa, and reproductive imago.",
            "hormonal_control": "Regulated by ecdysone (initiates molting) balanced by juvenile hormone (JH) from the corpora allata; drop in JH triggers pupation.",
            "ecological_advantage": "Eliminates intra-specific competition between juveniles and adults by partitioning larval feeding niches from adult reproductive dispersal."
        },
        "eusociality": {
            "title": "Eusocial Colony Organization & Acoustic/Dance Communication",
            "mechanism": "Division of reproductive labor (queens/drones) supported by non-reproductive worker castes exhibiting cooperative brood care and overlapping generations.",
            "hormonal_control": "Queen mandibular pheromones suppress ovarian development in workers; waggle dances encode vector azimuth and distance to floral resources.",
            "ecological_advantage": "Allows colony superorganisms to harvest energy and maintain collective micro-climate homeostasis far exceeding individual insect capacities."
        },
        "exoskeleton": {
            "title": "Sclerotized Chitin Exoskeleton & Biomechanics",
            "mechanism": "Composed of polysaccharide poly-N-acetylglucosamine (chitin) cross-linked with arthropodin/resilin proteins via quinone tanning (sclerotization).",
            "hormonal_control": "Apolysis and ecdysis triggered by prothoracicotropic hormone (PTTH) and ecdysteroids.",
            "ecological_advantage": "Provides rigid structural attachment for flight musculature, extreme desiccation resistance, and physical protection."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Entomology Reference Lookup',
            description='Selects stored insect explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.ENTOMOLOGICAL_CONCEPTS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "metamorphosis" and contains_any(combined, ["larva", "caterpillar", "pupa", "cocoon", "chrysalis", "molt"])) \
               or (key == "eusociality" and contains_any(combined, ["bee", "ant", "wasp", "hive", "queen", "worker", "dance", "colony"])) \
               or (key == "exoskeleton" and contains_any(combined, ["chitin", "shell", "cuticle", "insect", "bug"])):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="entomology", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct entomological or insect topics queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Entomology (Insect Biology)",
            "concept": matched["title"] if matched else "Insect Physiological Adaptations",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Insect morphological adaptation."),
            "endocrine_or_structural_control": matched.get("hormonal_control", "Ecdysteroid and neuroendocrine hormonal regulation.") if matched else "Endocrine regulation.",
            "ecological_advantage": matched.get("ecological_advantage", "High reproductive fecundity and ecological niche specialization.") if matched else "Ecological specialization.",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
EntomologyExpert = EntomologyReferenceLookup
