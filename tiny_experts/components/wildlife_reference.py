from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.knowledge_store import KnowledgeStore
from ..pipeline.book_engine import BookEngine

class WildlifeReferenceLookup(BaseComponent):
    """Matches animal records and reference passages using explicit rules."""
    name = 'Wildlife Reference Lookup'
    description = 'Matches animal records and reference passages using explicit rules.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    FAUNA_KNOWLEDGE_BASE = {
        "Monarch Butterfly": {
            "class": "Insecta (Lepidoptera)",
            "diet": "Nectar from milkweed, goldenrod, and cone flowers",
            "habitat": "Fields, meadows, prairie grasslands, gardens",
            "migration": "Famous multi-generational migration up to 3,000 miles to central Mexican mountain forests",
            "conservation_status": "Vulnerable / Endangered in certain regions",
            "behavior": "Larvae feed exclusively on milkweed which gives them toxic protection against predators."
        },
        "European Honeybee": {
            "class": "Insecta (Hymenoptera)",
            "diet": "Nectar and pollen from flowering plants",
            "habitat": "Meadows, agricultural orchards, forest edges, managed apiaries",
            "migration": "Non-migratory; colonies overwinter inside hives clustering for heat",
            "conservation_status": "Managed globally, facing colony collapse pressures",
            "behavior": "Highly social eusocial insect communicating food locations via the waggle dance."
        },
        "House Sparrow": {
            "class": "Aves (Passeriformes)",
            "diet": "Seeds, grains, berries, and small insects",
            "habitat": "Urban landscapes, farmsteads, suburban parks",
            "migration": "Resident / Non-migratory",
            "conservation_status": "Least Concern (widespread globally)",
            "behavior": "Gregarious flocking bird nesting in crevices of human buildings."
        },
        "Bald Eagle": {
            "class": "Aves (Accipitriformes)",
            "diet": "Opportunistic carnivore; primarily fish, waterfowl, and small mammals",
            "habitat": "Near large open bodies of water with abundant food and mature nest trees",
            "migration": "Partial migrant depending on coastal or frozen inland waters",
            "conservation_status": "Least Concern (Major historical recovery success story)",
            "behavior": "Apex aerial predator known for building the largest tree nests on record."
        },
        "Red Fox": {
            "class": "Mammalia (Carnivora)",
            "diet": "Omnivorous: rodents, rabbits, birds, fruits, and invertebrates",
            "habitat": "Highly adaptable across forests, grasslands, mountains, and suburban areas",
            "migration": "Sedentary / Non-migratory",
            "conservation_status": "Least Concern",
            "behavior": "Nocturnal / Crepuscular solitary hunter with keen auditory detection."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Wildlife Reference Lookup',
            description='Matches animal records and reference passages using explicit rules.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        species = context.get("species", "")
        query = context.get("query", "").lower()
        target_name = species or query

        # Search field guides via BookEngine
        book_citations = self.book_engine.search(query=target_name, shelf="wildlife", top_k=1)
        citation = book_citations[0] if book_citations else None

        # 1. Check dynamic knowledge store first
        stored = KnowledgeStore.find(target_name)
        if stored and stored.get("category") in ["animal", "bird", "insect", "mammal"]:
            return {
                "relevant": True,
                "animal_name": stored.get("common_name"),
                "biological_class": f"{stored.get('category').capitalize()} ({stored.get('scientific_name')})",
                "diet": stored.get("diet_or_soil"),
                "primary_habitat": stored.get("habitat"),
                "migration_profile": "Refer to regional migration registry",
                "status": "Documented in Open Biodiversity Index",
                "behavioral_notes": stored.get("summary"),
                "textbook_citation": citation
            }

        matched_animal = None
        for name, data in self.FAUNA_KNOWLEDGE_BASE.items():
            if contains_term(species, name) or contains_term(query, name):
                matched_animal = (name, data)
                break

        if not matched_animal:
            return {
                "relevant": False,
                "message": "Subject is not an animal/insect or not currently in wildlife registry."
            }

        name, info = matched_animal
        return {
            "relevant": True,
            "animal_name": name,
            "biological_class": info["class"],
            "diet": info["diet"],
            "primary_habitat": info["habitat"],
            "migration_profile": info["migration"],
            "status": info["conservation_status"],
            "behavioral_notes": info["behavior"],
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
WildlifeExpert = WildlifeReferenceLookup
