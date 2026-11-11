from ..matching import contains_any, contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.knowledge_store import KnowledgeStore
from ..pipeline.book_engine import BookEngine

class BotanyReferenceLookup(BaseComponent):
    """Matches plant records and reference passages using explicit rules."""
    name = 'Botany Reference Lookup'
    description = 'Matches plant records and reference passages using explicit rules.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    PLANT_KNOWLEDGE_BASE = {
        "Common Sunflower": {
            "type": "Annual flowering plant",
            "sunlight": "Full sun (6-8 hours daily)",
            "water": "Deep watering once a week; drought-tolerant once established",
            "soil": "Well-draining, nutrient-rich soil (pH 6.0 - 7.5)",
            "spacing_cm": 45,
            "height_m": 2.5,
            "bloom_season": "Mid-summer to early autumn",
            "care_tips": "Supports pollinators, requires staking if exposed to high winds."
        },
        "White Oak Tree": {
            "type": "Deciduous hardwood tree",
            "sunlight": "Full sun to partial shade",
            "water": "Moderate; deep taproot provides high drought resistance",
            "soil": "Deep, moist, well-drained acidic to neutral soil",
            "spacing_cm": 600,
            "height_m": 25.0,
            "bloom_season": "Spring (catkins)",
            "care_tips": "Critical keystone species supporting hundreds of moth and butterfly species."
        },
        "Poison Ivy": {
            "type": "Deciduous woody vine or shrub",
            "sunlight": "Adaptable: full sun to deep shade",
            "water": "Moderate moisture; highly adaptable",
            "soil": "Tolerates disturbed, moist, or dry soils",
            "spacing_cm": 0,
            "height_m": 1.2,
            "bloom_season": "Late spring",
            "care_tips": "Contains urushiol oil. Do not handle without protective equipment."
        },
        "Deadly Nightshade": {
            "type": "Perennial herbaceous plant",
            "sunlight": "Partial shade to light shade",
            "water": "Moist, calcareous soil",
            "soil": "Chalky, limestone-rich soils",
            "spacing_cm": 60,
            "height_m": 1.5,
            "bloom_season": "June to September",
            "care_tips": "Contains tropane alkaloids (atropine, scopolamine). Highly hazardous."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Botany Reference Lookup',
            description='Matches plant records and reference passages using explicit rules.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        species = context.get("species", "")
        query = context.get("query", "").lower()
        target_name = species or query

        # Query BookEngine for botanical field guides / manuals
        book_citations = self.book_engine.search(query=target_name, shelf="botany", top_k=1)
        citation = book_citations[0] if book_citations else None

        # 1. Check local dynamic knowledge store first
        stored = KnowledgeStore.find(target_name)
        if stored and stored.get("category") == "plant":
            return {
                "relevant": True,
            "reference_review_status": "unreviewed",
                "plant_name": stored.get("common_name"),
                "botanical_type": f"Plant ({stored.get('scientific_name')})",
                "sunlight_requirement": "Full sun to partial sun",
                "watering_schedule": "Standard moderate hydration",
                "soil_profile": stored.get("diet_or_soil"),
                "spacing_cm": 40,
                "height_meters": 1.0,
                "bloom_period": "Seasonal bloom",
                "recommendation": stored.get("summary"),
                "textbook_citation": citation
            }

        # 2. Check built-in baseline catalog
        matched_plant = None
        for name, data in self.PLANT_KNOWLEDGE_BASE.items():
            if contains_term(species, name) or contains_term(query, name):
                matched_plant = (name, data)
                break

        if not matched_plant:
            return {
                "relevant": False,
                "message": "Subject is not a plant or not currently in botanical registry."
            }

        name, info = matched_plant
        return {
            "relevant": True,
            "plant_name": name,
            "botanical_type": info["type"],
            "sunlight_requirement": info["sunlight"],
            "watering_schedule": info["water"],
            "soil_profile": info["soil"],
            "spacing_cm": info["spacing_cm"],
            "height_meters": info["height_m"],
            "bloom_period": info["bloom_season"],
            "recommendation": info["care_tips"],
            "textbook_citation": citation
        }


# Compatibility for existing integrations and model-training imports.
BotanyExpert = BotanyReferenceLookup
