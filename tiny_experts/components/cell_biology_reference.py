from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class CellBiologyReferenceLookup(BaseComponent):
    """Selects stored cell-biology explanations and retrieves passages."""
    name = 'Cell Biology Reference Lookup'
    description = 'Selects stored cell-biology explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    CELL_MECHANISMS = {
        "photosynthesis": {
            "title": "Chloroplast Photosynthetic Bioenergetics",
            "mechanism": "Photons excite chlorophyll pigments in Photosystems II and I within thylakoid membranes, generating an electrochemical proton gradient driving ATP and NADPH synthesis.",
            "cellular_pathway": "Z-scheme electron transport coupled to photolysis of water, releasing O2 and feeding the Calvin cycle for triose phosphate carbon fixation.",
            "organelle": "Chloroplast (Thylakoid membrane & Stroma)"
        },
        "mitochondria": {
            "title": "Mitochondrial Oxidative Phosphorylation & ATP Synthesis",
            "mechanism": "NADH and FADH2 donate electrons to the inner mitochondrial electron transport chain, generating a transmembrane proton motive force.",
            "cellular_pathway": "Proton reflux through the F0-F1 ATP synthase complex catalyzes phosphorylation of ADP to ATP with high stoichiometric efficiency.",
            "organelle": "Mitochondrion (Inner membrane cristae & Matrix)"
        },
        "transport": {
            "title": "Membrane Ion Pumps & Osmotic Homeostasis",
            "mechanism": "Primary active transport via Na+/K+-ATPase and H+-ATPases establishes steep electrochemical gradients across plasma membranes.",
            "cellular_pathway": "Enables secondary active transport (glucose/amino acid symporters) and osmotic turgor regulation in plant stomatal guard cells.",
            "organelle": "Plasma Membrane"
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Cell Biology Reference Lookup',
            description='Selects stored cell-biology explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.CELL_MECHANISMS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "photosynthesis" and contains_any(combined, ["light", "chlorophyll", "chloroplast", "calvin"])) \
               or (key == "mitochondria" and contains_any(combined, ["atp", "energy", "respiration", "metabolism", "cristae"])) \
               or (key == "transport" and contains_any(combined, ["membrane", "pump", "osmosis", "turgor"])):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="cell_biology", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct cellular, metabolic, or organellar pathway queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Cell Biology & Cytology",
            "concept": matched["title"] if matched else "Cellular Metabolic Organization",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Cellular bioenergetic pathway."),
            "cellular_pathway": matched.get("cellular_pathway", "Enzymatic membrane transport and bioenergetics.") if matched else "Membrane bioenergetics.",
            "organelle_locus": matched.get("organelle", "Cellular cytoplasm and membrane complexes") if matched else "Intracellular compartment",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
CellBiologyExpert = CellBiologyReferenceLookup
