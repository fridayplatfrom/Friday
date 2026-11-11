from ..matching import contains_any
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine

class GeneticsReferenceLookup(BaseComponent):
    """Selects stored genetics explanations and retrieves passages; this module is not the optional genetics neural classifier."""
    name = 'Genetics Reference Lookup'
    description = 'Selects stored genetics explanations and retrieves passages; this module is not the optional genetics neural classifier.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    GENETIC_CONCEPTS = {
        "transcription": {
            "title": "DNA Transcription & Gene Expression",
            "mechanism": "RNA polymerase reads the template DNA strand (3' to 5') and synthesizes precursor mRNA containing complementary ribonucleotides.",
            "regulation": "Promoter binding is modulated by sequence-specific transcription factors, enhancers, and histone acetylation.",
            "significance": "Controls the temporal and spatial synthesis of cellular functional enzymes and structural proteins."
        },
        "mutation": {
            "title": "Genetic Variation & Point Mutations",
            "mechanism": "Single nucleotide substitutions, insertions, or deletions induce synonymous, missense, or nonsense codon shifts.",
            "regulation": "DNA mismatch repair and nucleotide excision repair enzymes proofread nascent strands during replication.",
            "significance": "Primary source of novel genetic diversity, underlying evolutionary adaptation and resistance mechanisms (e.g. cardenolide Na+/K+ pump mutations in monarch butterflies)."
        },
        "crispr": {
            "title": "CRISPR-Cas9 & Gene Editing",
            "mechanism": "Guide RNA (gRNA) directs the Cas9 endonuclease to target genomic loci adjacent to a protospacer adjacent motif (PAM) to induce double-strand breaks.",
            "regulation": "Repaired via non-homologous end joining (NHEJ) or homology-directed repair (HDR).",
            "significance": "Enables precision targeted genomic modification and synthetic biological trait engineering."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Genetics Reference Lookup',
            description='Selects stored genetics explanations and retrieves passages; this module is not the optional genetics neural classifier.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        species = context.get("species", "")
        combined = f"{query} {species}".lower()

        matched = None
        # Specific topics precede broad words such as 'gene' and 'DNA'.
        for key, terms in [("crispr", ["crispr", "cas9", "gene editing"]),
                           ("transcription", ["transcription", "rna synthesis"]),
                           ("mutation", ["mutation", "mutations", "allele", "variation"])]:
            if contains_any(combined, terms):
                matched = self.GENETIC_CONCEPTS[key]
                break

        citations = self.book_engine.search(query=query, shelf="genetics", top_k=1)
        if not matched and not citations:
            return {
                "relevant": False,
                "message": "No direct genetic, molecular, or DNA/RNA processes queried."
            }

        citation = citations[0] if citations else None
        return {
            "relevant": True,
            "status": "reference_only",
            "reference_review_status": "unreviewed",
            "domain": "Genetics & Molecular Biology",
            "concept": matched["title"] if matched else "Gene Regulation & Genomic Structure",
            "mechanism": matched["mechanism"] if matched else (citation["text"] if citation else "DNA-encoded hereditary mechanisms."),
            "regulatory_control": matched.get("regulation", "Enzymatic chromatin remodeling and transcription factor modulation.") if matched else "Chromatin remodeling.",
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
GeneticsExpert = GeneticsReferenceLookup
