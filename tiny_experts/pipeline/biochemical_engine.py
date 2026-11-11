import re
from typing import Dict, Any, List, Optional

class BiochemicalEngine:
    """
    Biochemical Metabolic Pathway & Drug Interaction Engine.
    Maps active biological toxins and phytochemicals to cellular enzymes,
    receptors, and clinical pharmacological drug interactions.
    """

    PATHWAYS = {
        "salicin_cox_inhibition": {
            "name": "Cyclooxygenase (COX-1 / COX-2) Inhibition Pathway",
            "trigger_keywords": ["salicin", "salicylic acid", "willow", "salix", "aspirin", "nsaid"],
            "target_enzyme": "Cyclooxygenase-1 (COX-1) and Cyclooxygenase-2 (COX-2)",
            "mechanism": "Inhibits conversion of arachidonic acid into pro-inflammatory prostaglandins and pro-aggregatory thromboxane A2.",
            "cellular_effect": "Suppresses inflammatory platelet aggregation and gastric mucosal bicarbonate barrier secretion.",
            "drug_interactions": [
                {
                    "class": "Synthetic NSAIDs (e.g. Carprofen, Meloxicam, Ibuprofen, Ketoprofen)",
                    "severity": "CRITICAL / SEVERE",
                    "advisory": "Additive non-selective COX blockade completely strips gastric mucosal protective mucus. Extreme risk of acute gastric perforation, ulceration, and renal papillary necrosis."
                },
                {
                    "class": "Anticoagulants (e.g. Warfarin, Heparin, Clopidogrel)",
                    "severity": "HIGH",
                    "advisory": "Compounded anti-platelet and anti-thrombotic action exponentially raises risk of spontaneous systemic hemorrhage."
                }
            ]
        },
        "anticholinergic_blockade": {
            "name": "Muscarinic Acetylcholine Receptor (mAChR) Antagonism",
            "trigger_keywords": ["atropine", "scopolamine", "hyoscyamine", "nightshade", "belladonna", "datura", "jimsonweed"],
            "target_enzyme": "Muscarinic Acetylcholine Receptors (M1 through M5)",
            "mechanism": "Competitive post-synaptic antagonism of parasympathetic cholinergic neurotransmission.",
            "cellular_effect": "Blocks vagal parasympathetic tone, halts secretory glandular function, dilates pupils (mydriasis), and induces sinus tachycardia.",
            "antidote_protocol": "Physostigmine salicylate (tertiary amine that crosses the blood-brain barrier to reverse central and peripheral delirium)."
        },
        "cardiac_glycoside_arrest": {
            "name": "Cellular Na+/K+-ATPase Pump Disruption",
            "trigger_keywords": ["cardenolide", "glycoside", "milkweed", "foxglove", "digitalis", "oleander", "oleandrin"],
            "target_enzyme": "Plasma membrane Na+/K+-ATPase Sodium Pump",
            "mechanism": "Direct extracellular binding inhibits active sodium extrusion, raising intracellular Na+ and reversing Na+/Ca2+ exchange (NCX).",
            "cellular_effect": "Pathological intracellular calcium overload triggers delayed afterdepolarizations, fatal ventricular arrhythmias, and AV block.",
            "antidote_protocol": "Digoxin-specific Fab antibody fragments (DigiFab) and intravenous potassium correction."
        },
        "amatoxin_rna_pol_ii_arrest": {
            "name": "Eukaryotic RNA Polymerase II Transcriptional Arrest",
            "trigger_keywords": ["amatoxin", "alpha-amanitin", "amanita", "death cap", "destroying angel"],
            "target_enzyme": "Nuclear RNA Polymerase II",
            "mechanism": "Binds with sub-nanomolar affinity to the bridge helix of RNA Polymerase II, physically halting translocation along DNA templates.",
            "cellular_effect": "Total shutdown of cellular mRNA synthesis and protein translation; hepatocytes undergo massive apoptosis and centrilobular liver necrosis.",
            "antidote_protocol": "Intravenous silibinin (inhibits hepatic OATP1B3 amatoxin uptake transporter) and high-dose Penicillin G."
        },
        "urushiol_immune_lysis": {
            "name": "Type IV Cell-Mediated Dendritic Hypersensitivity",
            "trigger_keywords": ["urushiol", "poison ivy", "toxicodendron", "catechol", "sumac"],
            "target_enzyme": "Epidermal CD1a Receptors & Keratinocyte Membranes",
            "mechanism": "Lipophilic pentadecylcatechol haptens penetrate stratum corneum, oxidizing into reactive quinones that covalently bond to dendritic surface proteins.",
            "cellular_effect": "Sensitized CD4+ and CD8+ T-lymphocytes infiltrate dermal tissue, releasing interferon-gamma and perforin, causing vesicular lysis.",
            "antidote_protocol": "Immediate surfactant/alcohol degreasing within 20 minutes; high-potency topical or systemic corticosteroids."
        }
    }

    @staticmethod
    def _mentioned(term: str, text: str) -> bool:
        for match in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text):
            before = text[max(0, match.start() - 32):match.start()]
            if not re.search(r"\b(?:not|no|without|avoid(?:ing)?)\s+(?:\w+\s+){0,3}$", before):
                return True
        return False

    @classmethod
    def evaluate(cls, query: str, species_name: str = "", chemical_name: str = "") -> Optional[Dict[str, Any]]:
        """Find curated pathway references and explicit potential interaction pairs.

        Mentioning a chemical is not evidence of exposure. No antidote or
        treatment protocol is selected from this lookup.
        """
        combined = f"{query} {species_name} {chemical_name}".lower()
        matches = [(key, path) for key, path in cls.PATHWAYS.items()
                   if any(cls._mentioned(term, combined) for term in path["trigger_keywords"])]
        if not matches:
            return None
        key, pathway = matches[0]
        interactions = []
        if key == "salicin_cox_inhibition":
            bases = [term for term in ["salicin", "salicylic acid", "willow", "salix", "aspirin"]
                     if cls._mentioned(term, combined)]
            drug_groups = [
                ["aspirin", "ibuprofen", "carprofen", "meloxicam", "ketoprofen", "nsaid"],
                ["warfarin", "heparin", "clopidogrel", "blood thinner", "anticoagulant"],
            ]
            for reference, terms in zip(pathway.get("drug_interactions", []), drug_groups):
                drugs = [term for term in terms if cls._mentioned(term, combined)]
                pairs = [(base, drug) for base in bases for drug in drugs if base != drug]
                if pairs:
                    interactions.append({"class": reference["class"], "severity": "REQUIRES VERIFICATION",
                        "status": "potential_interaction", "matched_pairs": pairs,
                        "advisory": "The query mentions a pair with a possible interaction. Confirm substances, actual exposure and an authoritative interaction reference before drawing a clinical conclusion."})
        return {"pathway_key": key, "pathway_name": pathway["name"], "target": pathway["target_enzyme"],
                "biochemical_mechanism": pathway["mechanism"], "cellular_effect": pathway["cellular_effect"],
                "status": "curated_reference", "reference_only": True, "source_validation": "not_verified",
                "antidote_protocol": None, "detected_drug_interactions": interactions,
                "has_potential_interaction": bool(interactions), "has_severe_drug_interaction": False,
                "matched_pathways": [{"key": k, "name": p["name"]} for k, p in matches]}
