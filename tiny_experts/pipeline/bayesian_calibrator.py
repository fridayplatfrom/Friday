import re
from typing import Dict, Any, List, Optional

class BayesianCalibrator:
    """Pair-specific heuristic evidence scores, not calibrated probabilities.

    The manual priors and multipliers are retained for transparent comparison.
    They cannot establish identification, edibility, or safe handling.
    """

    LOOKALIKE_PAIRS = [
        {
            "id": "amanita_vs_agaricus",
            "trigger_terms": ["mushroom", "white gills", "wild mushroom", "destroying angel", "death cap", "meadow mushroom", "agaricus", "amanita"],
            "candidates": [
                {
                    "name": "Amanita phalloides / Amanita bisporigera (Death Cap / Destroying Angel)",
                    "hazard": "FATAL (Amatoxins)",
                    "prior": 0.40,
                    "diagnostic_markers": {
                        "spore_print": "pure white",
                        "stem_base": "cup-like membranous volva (often buried beneath soil)",
                        "gills": "free pure white lamellae",
                        "annulus": "persistent membranous skirt-like ring"
                    }
                },
                {
                    "name": "Agaricus campestris (Meadow Mushroom)",
                    "hazard": "EDIBLE / NON-TOXIC",
                    "prior": 0.60,
                    "diagnostic_markers": {
                        "spore_print": "deep chocolate-brown",
                        "stem_base": "no volva; tapered clean base",
                        "gills": "pink when young, turning dark chocolate-brown at maturity",
                        "annulus": "delicate single ring, often collapsing"
                    }
                }
            ],
            "critical_differentiator_test": "A qualified identification must consider multiple independent features. Spore color or a single morphological feature cannot establish species or edibility."
        },
        {
            "id": "poison_ivy_vs_virginia_creeper",
            "trigger_terms": ["poison ivy", "virginia creeper", "shiny leaves", "vine", "climbing vine", "three leaves", "five leaves"],
            "candidates": [
                {
                    "name": "Toxicodendron radicans (Poison Ivy)",
                    "hazard": "SEVERE CONTACT DERMATITIS (Urushiol)",
                    "prior": 0.50,
                    "diagnostic_markers": {
                        "leaflets": "strictly 3 leaflets (trifoliate; 'leaves of three, let it be')",
                        "stem_attachment": "middle leaflet has distinctly longer petiolule",
                        "berries": "waxy grayish-white drupes in late summer"
                    }
                },
                {
                    "name": "Parthenocissus quinquefolia (Virginia Creeper)",
                    "hazard": "LOW RISK (Contains minor calcium oxalate raphides; not urushiol)",
                    "prior": 0.50,
                    "diagnostic_markers": {
                        "leaflets": "strictly 5 leaflets radiating palmately from a single central point",
                        "stem_attachment": "all 5 leaflets originate from a common petiole terminus",
                        "berries": "dark blue to purplish berries on red pedicels"
                    }
                }
            ],
            "critical_differentiator_test": "Record leaflet count, leaf arrangement and other independent identifying features. This two-candidate comparison is not a confirmed identification."
        },
        {
            "id": "poison_hemlock_vs_wild_carrot",
            "trigger_terms": ["hemlock", "wild carrot", "queen anne", "white umbrella flower", "umbellifer", "conium"],
            "candidates": [
                {
                    "name": "Conium maculatum (Poison Hemlock)",
                    "hazard": "FATAL (Coniine / Neurotoxic Alkaloids)",
                    "prior": 0.45,
                    "diagnostic_markers": {
                        "stem": "completely hairless, smooth, with prominent purple mottling/blotches",
                        "odor": "musty, parsnip-like, unpleasant mousy odor when bruised",
                        "root": "white taproot; lack of carrot aroma"
                    }
                },
                {
                    "name": "Daucus carota (Queen Anne's Lace / Wild Carrot)",
                    "hazard": "SAFE / NON-TOXIC",
                    "prior": 0.55,
                    "diagnostic_markers": {
                        "stem": "densely hairy (hispid) solid green stem; completely lacking purple spots",
                        "flower_center": "single tiny dark purple or black solitary floret in the center of the umbel",
                        "odor": "distinct sweet carrot aroma when crushed"
                    }
                }
            ],
            "critical_differentiator_test": "STEM PUBESCENCE & FLORET EXAMINATION: Inspect the lower stem with a hand lens. Wild Carrot features dense bristly hairs and solid green coloration with a central dark purple sterile floret. Poison Hemlock features completely hairless (glabrous) hollow stems with conspicuous purple spots and a foul musty smell."
        }
    ]

    EVIDENCE_RULES = {
        "amanita_vs_agaricus": [
            (r"\bwhite\s+gills?\b", 0, 1.4, "white gills"),
            (r"\b(?:brown|chocolate[- ]brown|pink)\s+(?:gills?|spore\s+print)\b", 1, 1.4, "pink/brown gills or spore print"),
        ],
        "poison_ivy_vs_virginia_creeper": [
            (r"\b(?:three|3)\s+(?:leaves|leaflets?)\b", 0, 1.5, "three leaflets"),
            (r"\b(?:five|5)\s+(?:leaves|leaflets?)\b", 1, 1.5, "five leaflets"),
        ],
        "poison_hemlock_vs_wild_carrot": [
            (r"\b(?:hairless|glabrous)\b", 0, 1.6, "hairless stem description"),
            (r"\b(?:hairy|bristly)\b", 1, 1.6, "hairy stem description"),
            (r"\bpurple\s+(?:stem|spots?|mottling|blotches)\b", 0, 1.6, "purple stem markings"),
        ],
    }

    @classmethod
    def evaluate(cls, query: str, detected_species: str = "") -> Optional[Dict[str, Any]]:
        combined = f"{query} {detected_species}".lower()
        pairs = [pair for pair in cls.LOOKALIKE_PAIRS if any(
            re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", combined) for term in pair["trigger_terms"])]
        if not pairs:
            return None
        pair = pairs[0]
        weights = [candidate["prior"] for candidate in pair["candidates"]]
        evidence = []
        for pattern, index, multiplier, label in cls.EVIDENCE_RULES[pair["id"]]:
            for match in re.finditer(pattern, combined):
                before = combined[max(0, match.start() - 24):match.start()]
                if re.search(r"\b(?:not|no|without|lacks?)\s+(?:\w+\s+){0,2}$", before):
                    continue
                weights[index] *= multiplier
                evidence.append({"feature": label, "candidate": pair["candidates"][index]["name"], "multiplier": multiplier})
                break
        scores = [weight / sum(weights) for weight in weights]
        return {
            "pair_id": pair["id"], "status": "heuristic_comparison", "method": "manual_pair_specific_weights",
            "calibrated": False, "ambiguity_detected": True,
            # Legacy container name is retained for callers; no probability is asserted.
            "calibrated_posterior": [
                {"candidate": candidate["name"], "hazard": candidate["hazard"], "probability": None,
                 "evidence_score": round(score, 3)} for candidate, score in zip(pair["candidates"], scores)
            ],
            "probability_gap": None, "evidence_score_gap": round(abs(scores[0] - scores[1]), 3),
            "observed_evidence": evidence, "other_matching_pairs": [p["id"] for p in pairs[1:]],
            "differentiator_test": pair["critical_differentiator_test"],
            "advisory": "These are unvalidated scores for two listed candidates. Other species may match. Identification and safe handling or consumption are not established.",
        }
