from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class EvolutionReferenceLookup(BaseComponent):
    """Selects stored evolution explanations and retrieves passages."""
    name = 'Evolution Reference Lookup'
    description = 'Selects stored evolution explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    EVOLUTIONARY_CONCEPTS = {
        "speciation": {
            "title": "Allopatric vs. Sympatric Speciation & Reproductive Isolation",
            "mechanism": "Geographic vicariance or ecological disruptive selection terminates gene flow; independent mutation and genetic drift establish pre-zygotic (behavioral/temporal) and post-zygotic (hybrid sterility) barriers.",
            "macroevolution_significance": "Drives the branching cladogenesis of new biological species across deep geological epochs.",
            "phylogenetic_principle": "Bifurcating cladograms rooted by common ancestral nodes."
        },
        "adaptive_radiation": {
            "title": "Adaptive Radiation & Ecological Opportunity",
            "mechanism": "A single ancestral lineage rapidly diversifies into an array of morphologically distinct descendant species adapted to specialized ecological niches following colonization of unexploited environments (e.g. Darwin's finches).",
            "macroevolution_significance": "Underlies major bursts of morphological disparity following mass extinction events.",
            "phylogenetic_principle": "Rapid polytomies resolving into specialized derived clades."
        },
        "fossil_transitions": {
            "title": "Transitional Fossil Stratigraphy & Homology",
            "mechanism": "Sedimentary rock strata record morphological intermediate states exhibiting mosaic evolution—combining ancestral (plesiomorphic) and novel derived (apomorphic) anatomical traits (e.g. Tiktaalik, Archaeopteryx).",
            "macroevolution_significance": "Empirically validates deep-time evolutionary lineages linking disparate modern phyla.",
            "phylogenetic_principle": "Homologous skeletal structures derived from common ancestral embryonic development."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Evolution Reference Lookup',
            description='Selects stored evolution explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.EVOLUTIONARY_CONCEPTS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "speciation" and contains_any(combined, ["speciation", "isolation", "reproductive barrier", "allopatric", "sympatric"])) \
               or (key == "adaptive_radiation" and contains_any(combined, ["radiation", "darwin", "finch", "ancestor", "lineage", "diverge"])) \
               or (key == "fossil_transitions" and contains_any(combined, ["fossil", "deep time", "homology", "paleontology", "extinct", "transitional", "evolve", "evolution"])):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="evolution", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct macroevolution, speciation, or paleontological topics queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Evolutionary Biology & Paleontology",
            "concept": matched["title"] if matched else "Macroevolutionary Diversification",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Evolutionary natural selection process."),
            "macroevolution_significance": matched.get("macroevolution_significance", "Generation of biological disparity across geological time.") if matched else "Generation of biological disparity.",
            "phylogenetic_principle": matched.get("phylogenetic_principle", "Cladistic monophyly and synapomorphic character states.") if matched else "Phylogenetic reconstruction.",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
EvolutionaryBiologyExpert = EvolutionReferenceLookup
