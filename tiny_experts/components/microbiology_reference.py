from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class MicrobiologyReferenceLookup(BaseComponent):
    """Selects stored microbiology explanations and retrieves passages."""
    name = 'Microbiology Reference Lookup'
    description = 'Selects stored microbiology explanations and retrieves passages.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    MICROBIAL_CONCEPTS = {
        "nitrogen_fixation": {
            "title": "Diazotrophic Symbiotic Nitrogen Fixation",
            "mechanism": "Rhizobium and Bradyrhizobium bacteria infect legume root hairs, inducing root nodules where the oxygen-labile nitrogenase metalloenzyme reduces atmospheric N2 into bio-available NH3 (ammonia).",
            "biochemical_cofactor": "MoFe (molybdenum-iron) nitrogenase catalytic center, protected from O2 denaturation by host leghemoglobin.",
            "ecological_importance": "Primary natural terrestrial input of bio-available nitrogen, eliminating need for synthetic chemical fertilizers."
        },
        "bacteriophage": {
            "title": "Bacteriophage Lytic vs. Lysogenic Infection Cycles",
            "mechanism": "Phages adsorb to outer membrane lipopolysaccharides or pili, inject dsDNA genomes into the bacterial cytoplasm, hijack host transcriptional machinery, and synthesize holins/endolysins to lyse the host peptidoglycan wall.",
            "biochemical_cofactor": "Endolysins and phage holin membrane pores.",
            "ecological_importance": "Regulates bacterial population density via 'kill the winner' viral shunt dynamics, recycling microbial carbon in soils and oceans."
        },
        "antibiotic_resistance": {
            "title": "Bacterial Antimicrobial Resistance (AMR) Mechanisms",
            "mechanism": "Bacteria synthesize beta-lactamase enzymes to hydrolyze penicillin core rings, upregulate multi-drug RND efflux pumps, or alter target penicillin-binding proteins (PBP2a).",
            "biochemical_cofactor": "Beta-lactamase serine active sites; mobile genetic transposons and R-plasmids.",
            "ecological_importance": "Rapid horizontal dissemination across clinical and environmental bacterial microbiomes via bacterial conjugation."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Microbiology Reference Lookup',
            description='Selects stored microbiology explanations and retrieves passages.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        for key, data in self.MICROBIAL_CONCEPTS.items():
            if contains_term(combined, key.replace("_", " ")) or (key == "nitrogen_fixation" and contains_any(combined, ["rhizobium", "nitrogen fix", "nodule", "bacteria root"])) \
               or (key == "bacteriophage" and contains_any(combined, ["phage", "bacteriophage", "virus", "viral", "lysis", "lytic"])) \
               or (key == "antibiotic_resistance" and contains_any(combined, ["antibiotic", "resistance", "amr", "beta-lactamase", "bacteria"])):
                matched = data
                break

        citations = self.book_engine.search(query=query, shelf="microbiology", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct microbiology, bacterial, or virological topics queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "reference_review_status": "unreviewed",
            "domain": "Microbiology & Virology",
            "concept": matched["title"] if matched else "Microbial Physiological Process",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "Bacterial biochemical process."),
            "biochemical_machinery": matched.get("biochemical_cofactor", "Metalloenzymes and bacterial membrane complexes.") if matched else "Microbial enzymatic complexes.",
            "ecological_importance": matched.get("ecological_importance", "Foundational prokaryotic nutrient and carbon turnover.") if matched else "Prokaryotic ecological turnover.",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
MicrobiologyExpert = MicrobiologyReferenceLookup
