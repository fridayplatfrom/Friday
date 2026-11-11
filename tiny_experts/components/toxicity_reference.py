from ..matching import contains_term
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.knowledge_store import KnowledgeStore
from ..pipeline.toxicology_connector import ToxicologyConnector
from ..pipeline.book_engine import BookEngine
from ..pipeline.chemical_regulatory_registry import ChemicalRegulatoryRegistry

class ToxicityReferenceLookup(BaseComponent):
    """Looks up toxicity references and applies conservative safety rules."""
    name = 'Toxicity Reference Lookup'
    description = 'Looks up toxicity references and applies conservative safety rules.'
    component_kind = 'reference_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    HAZARD_REGISTRY = {
        "Death Cap": {
            "hazard_level": "DEADLY HAZARDOUS",
            "toxin": "Amatoxin / alpha-Amanitin",
            "symptoms": "Severe delayed gastrointestinal distress (6-24 hours), followed by false remission, then irreversible hepatic necrosis (acute liver failure), renal failure, and encephalopathy",
            "first_aid": "EMERGENCY: Immediate hospital emergency transport. Do not induce vomiting. Intravenous silibinin and high-dose penicillin therapy under ICU supervision. Bring mushroom sample for mycology identification.",
            "safety_verdict": "DO NOT CONSUME UNDER ANY CIRCUMSTANCES. A single mushroom cap contains more than a lethal dose of alpha-amanitin for an adult human."
        },
        "Poison Ivy": {
            "hazard_level": "HIGH",
            "toxin": "Urushiol",
            "symptoms": "Severe contact dermatitis, intense itching, redness, fluid-filled blisters within 12-48 hours",
            "first_aid": "Immediately wash affected skin with cool running water and degreasing soap/isopropyl alcohol within 15-30 minutes. Do not burn the plant as smoke causes respiratory damage.",
            "safety_verdict": "DO NOT TOUCH. Wear long sleeves and nitrile gloves if clearing."
        },
        "Deadly Nightshade": {
            "hazard_level": "CRITICAL / FATAL",
            "toxin": "Atropine",
            "symptoms": "Dilated pupils, blurred vision, tachycardia, delirium, convulsions, respiratory failure",
            "first_aid": "Emergency immediate hospitalization. Ingestion of 2-5 sweet-tasting shiny berries can be lethal to children.",
            "safety_verdict": "LETHAL TOXIN. Seek emergency medical care immediately upon ingestion."
        },
        "European Honeybee": {
            "hazard_level": "LOW to SEVERE (Allergy-dependent)",
            "toxin": "Melittin",
            "symptoms": "Localized sharp pain, redness, mild swelling. In allergic individuals: anaphylaxis, hives, airway constriction",
            "first_aid": "Scrape stinger off with a fingernail or flat edge (do not squeeze venom sac). Apply ice pack. If allergic, administer epinephrine immediately.",
            "safety_verdict": "Beneficial pollinator. Only stings defensively if hive or individual is threatened."
        }
    }

    def __init__(self, book_engine: BookEngine = None):
        super().__init__(
            name='Toxicity Reference Lookup',
            description='Looks up toxicity references and applies conservative safety rules.'
        )
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        species = str(context.get("species") or "")
        query = str(context.get("query") or "")
        combined = f"{species} {query}"
        for name, info in self.HAZARD_REGISTRY.items():
            aliases = [name] + info["toxin"].split(" / ")
            if name == "Death Cap":
                aliases.extend(["death cap mushroom", "amanita phalloides"])
            if name == "European Honeybee":
                aliases.extend(["honeybee", "honey bee"])
            if any(contains_term(combined, alias) for alias in aliases):
                citations = self.book_engine.search(query=name, shelf="toxicology", top_k=1)
                return {"status": "hazard_reference", "is_hazardous": True,
                        "hazard_level": info["hazard_level"], "toxic_agent": info["toxin"],
                        "symptoms": info["symptoms"], "advisory": "A hazard record matched the named subject. This does not verify the specimen's identity or exposure.",
                        "emergency_first_aid": "For an actual suspected poisoning or severe reaction, contact emergency services or a poison center.",
                        "source_status": "unreviewed_local_reference", "identity_verified": False,
                        "pubchem": None, "pet_safety": None,
                        "textbook_citation": citations[0] if citations else None}
        return {"status": "unknown", "is_hazardous": None, "hazard_level": "UNKNOWN",
                "advisory": "The local records cannot establish safety for this subject. An unidentified organism must not be treated as edible or non-toxic.",
                "pet_safety": None, "pubchem": None, "textbook_citation": None}


# Compatibility for existing integrations and model-training imports.
ToxicityExpert = ToxicityReferenceLookup
