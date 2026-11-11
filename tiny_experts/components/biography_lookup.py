from typing import Dict, Any, List, Optional
from ..pipeline.biography_engine import BiographyEngine

class BiographyLookup:
    """Searches stored person and invention records."""
    name = 'Biography Lookup'
    description = 'Searches stored person and invention records.'
    component_kind = 'catalog_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    def __init__(self, biography_engine: Optional[BiographyEngine] = None):
        self.biography_engine = biography_engine or BiographyEngine()
        self.name = 'Biography Lookup'

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "")
        vernacular_meta = context.get("vernacular_meta", {})
        norm_query = vernacular_meta.get("normalized_query") or query
        lang = vernacular_meta.get("detected_language", "en")

        # 1. Search for people matching query
        people_hits = self.biography_engine.search_people(query=norm_query, lang=lang, limit=3)
        inventor_hits = self.biography_engine.find_inventor_of(theory_query=norm_query)

        if not people_hits and not inventor_hits:
            return {
                "expert": "BiographyLookup",
                "matched": False,
                "people": [],
                "message": "No biographical profile found in the universal registry."
            }

        primary_person = people_hits[0] if people_hits else None

        return {
            "expert": "BiographyLookup",
            "matched": True,
            "primary_person": primary_person,
            "all_matched_people": people_hits,
            "inventions_and_attributions": inventor_hits,
            "total_matches": len(people_hits)
        }


# Compatibility for existing integrations and model-training imports.
BiographerExpert = BiographyLookup
