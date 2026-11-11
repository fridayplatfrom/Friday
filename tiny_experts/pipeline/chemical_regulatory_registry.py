from typing import Dict, Any, List, Optional
import re

class ChemicalRegulatoryRegistry:
    """
    CIBRC (India) and US EPA Legal Agrochemical & Safety Registry.
    Audits chemical prescriptions, enforces statutory bans (e.g. Endosulfan, Monocrotophos),
    computes mandatory Pre-Harvest Intervals (PHI in days), and recommends safe legal alternatives.
    """

    BANNED_PESTICIDES: Dict[str, Dict[str, Any]] = {
        "endosulfan": {
            "name": "Endosulfan",
            "regulatory_status": "BANNED (Supreme Court of India & CIBRC Gazette 2011 / Stockholm Convention)",
            "statutory_order": "Supreme Court Order W.P. (C) No. 213 of 2011 & Gazette Notification S.O. 1482(E)",
            "hazard_classification": "Extremely Hazardous Organochlorine (Endocrine Disruptor, Teratogen, Neurotoxin)",
            "statutory_warning": "CRITICAL VIOLATION: Manufacture, sale, and use of Endosulfan is completely illegal and punishable under the Insecticides Act, 1968.",
            "approved_legal_alternative": "Chlorantraniliprole 18.5% SC, Spinosad 45% SC, or Azadirachtin (Neem oil 10,000 ppm)"
        },
        "monocrotophos": {
            "name": "Monocrotophos",
            "regulatory_status": "BANNED ON VEGETABLES & FRUITS (CIBRC Order S.O. 1482(E) / WHO Class Ib)",
            "statutory_order": "Government of India Notification S.O. 1482(E) under Insecticides Act, 1968",
            "hazard_classification": "Highly Hazardous Organophosphate (Severe Cholinesterase Inhibitor, High Avian Lethality)",
            "statutory_warning": "LEGAL VIOLATION: Monocrotophos is strictly prohibited on all vegetable crops, fruits, and legumes due to extreme acute residue toxicity.",
            "approved_legal_alternative": "Flubendiamide 39.35% SC, Emamectin Benzoate 5% SG, or Bacillus thuringiensis (Bt)"
        },
        "paraquat": {
            "name": "Paraquat Dichloride",
            "regulatory_status": "SEVERELY RESTRICTED / BANNED IN MULTIPLE STATES (Kerala, Odisha, Maharashtra)",
            "statutory_order": "CIBRC Restricted Use Directive & State Government Gazettes",
            "hazard_classification": "Fatal Pulmonary Fibrosis Agent (Extremely toxic; no known clinical antidote)",
            "statutory_warning": "HIGH RISK: Paraquat ingestion or inhalation causes irreversible progressive pulmonary necrosis.",
            "approved_legal_alternative": "Glufosinate Ammonium 13.5% SL or mechanical cover cropping / mulch"
        },
        "aldicarb": {
            "name": "Aldicarb (Temik)",
            "regulatory_status": "BANNED WORLDWIDE (CIBRC Gazette / US EPA Complete Phaseout)",
            "statutory_order": "EPA Registration Cancellation & CIBRC Prohibited List",
            "hazard_classification": "WHO Class Ia Extremely Hazardous Carbamate Neurotoxin",
            "statutory_warning": "CRITICAL VIOLATION: Completely banned worldwide for all agricultural and horticultural applications.",
            "approved_legal_alternative": "Biological nematicide: Purpureocillium lilacinum (syn. Paecilomyces lilacinus) or Neem cake"
        },
        "chlorpyrifos": {
            "name": "Chlorpyrifos",
            "regulatory_status": "BANNED ON FOOD CROPS (US EPA 2021 / CIBRC Restricted)",
            "statutory_order": "EPA 40 CFR Part 180 Revocation & CIBRC Notification",
            "hazard_classification": "Organophosphate Neurodevelopmental Toxicant in Children",
            "statutory_warning": "RESTRICTION: Food tolerances revoked by EPA. Banned on vegetables and home gardens.",
            "approved_legal_alternative": "Bio-insecticide Beauveria bassiana, Spinetoram, or Neem azadirachtin"
        },
        "methyl parathion": {
            "name": "Methyl Parathion",
            "regulatory_status": "BANNED COMPLETELY (CIBRC S.O. 682(E) / Rotterdam Convention)",
            "statutory_order": "Gazette of India S.O. 682(E)",
            "hazard_classification": "WHO Class Ia Extremely Toxic Organophosphate",
            "statutory_warning": "CRITICAL VIOLATION: Possession, sale, and use is a criminal offense under the Insecticides Act.",
            "approved_legal_alternative": "Spinosad or Pheromone IPM mass-trapping"
        }
    }

    APPROVED_ACTIVES: Dict[str, Dict[str, Any]] = {
        "copper hydroxide": {
            "name": "Copper Hydroxide (Kocide / Champ)",
            "frac_group": "FRAC M01 (Multi-site inorganic copper)",
            "legal_status": "CIBRC & EPA Fully Approved (Registered for Fungal & Bacterial Blights)",
            "phi_days": 0,
            "dosage": "2.0 - 2.5 g/L water (foliar spray)",
            "safety_profile": "Safe up to harvest; non-systemic protective barrier preventing zoospore penetration.",
            "organic_certified": True
        },
        "copper oxychloride": {
            "name": "Copper Oxychloride 50% WP (Blitox)",
            "frac_group": "FRAC M01 (Multi-site contact protectant)",
            "legal_status": "CIBRC Registered for Cereals, Vegetables, Plantation Crops",
            "phi_days": 3,
            "dosage": "2.5 - 3.0 g/L water",
            "safety_profile": "Standard broad-spectrum protectant. Avoid mixing with acidic agrochemicals.",
            "organic_certified": True
        },
        "mancozeb": {
            "name": "Mancozeb 75% WP (Dithane M-45)",
            "frac_group": "FRAC M03 (Dithiocarbamate multi-site)",
            "legal_status": "CIBRC Registered (Subject to strict Pre-Harvest Interval enforcement)",
            "phi_days": 7,
            "dosage": "2.0 - 2.5 g/L water",
            "safety_profile": "Mandatory 7-day waiting period before harvest. Never spray directly before picking.",
            "organic_certified": False
        },
        "azoxystrobin": {
            "name": "Azoxystrobin 23% SC (Amistar)",
            "frac_group": "FRAC 11 (QoI Strobilurin - Mitochondrial Complex III inhibitor)",
            "legal_status": "CIBRC & EPA Approved",
            "phi_days": 3,
            "dosage": "1.0 ml/L water",
            "safety_profile": "Translaminar systemic action. Maximum 2 consecutive sprays to avoid fungal resistance.",
            "organic_certified": False
        },
        "mandipropamid": {
            "name": "Mandipropamid 23.4% SC (Revus)",
            "frac_group": "FRAC 40 (CAA - Cellulose Synthase inhibitor)",
            "legal_status": "CIBRC & EPA Approved for Late Blight & Downy Mildew",
            "phi_days": 1,
            "dosage": "0.8 - 1.0 ml/L water",
            "safety_profile": "Rain-fast translaminar protectant with 1-day pre-harvest interval.",
            "organic_certified": False
        },
        "potassium bicarbonate": {
            "name": "Potassium Bicarbonate (Armicarb / MilStop)",
            "frac_group": "FRAC NC (Osmotic physical disruptor)",
            "legal_status": "OMRI & EPA Certified Organic / CIBRC Exempt",
            "phi_days": 0,
            "dosage": "3.0 - 5.0 g/L water",
            "safety_profile": "Zero PHI. Causes instantaneous osmotic collapse of powdery mildew mycelium.",
            "organic_certified": True
        },
        "streptocycline": {
            "name": "Streptocycline (Streptomycin sulphate 90% + Tetracycline HCl 10%)",
            "frac_group": "Agricultural Antibiotic (CIBRC Regulated)",
            "legal_status": "CIBRC Permitted on Prescription for Bacterial Diseases only",
            "phi_days": 15,
            "dosage": "50 - 100 ppm (0.1 g/L water) strictly limited to 2 sprays",
            "safety_profile": "Mandatory 15-day PHI. Strictly prohibited for prophylactic misuse to prevent antimicrobial resistance.",
            "organic_certified": False
        },
        "bacillus amyloliquefaciens": {
            "name": "Bacillus amyloliquefaciens strain D747 / B. subtilis",
            "frac_group": "FRAC BM02 (Microbial biofungicide)",
            "legal_status": "CIBRC & EPA Bio-Pesticide Registered / OMRI Listed",
            "phi_days": 0,
            "dosage": "2.5 - 5.0 ml/L water",
            "safety_profile": "Safe up to day of harvest. Produces lipopeptide iturins and surfactins.",
            "organic_certified": True
        }
    }

    @classmethod
    def audit_chemical(cls, chemical_name: str) -> Dict[str, Any]:
        """Audits a chemical compound against statutory CIBRC and EPA registries."""
        clean = chemical_name.lower().strip()

        # 1. Check Banned List
        for key, record in cls.BANNED_PESTICIDES.items():
            if key in clean or clean in key:
                return {
                    "is_legal": False,
                    "is_banned": True,
                    "compound": record["name"],
                    "status": record["regulatory_status"],
                    "statutory_order": record["statutory_order"],
                    "hazard": record["hazard_classification"],
                    "legal_alert": f"[LEGAL & SAFETY ALERT: BANNED PESTICIDE] {record['statutory_warning']}",
                    "recommended_substitute": record["approved_legal_alternative"]
                }

        # 2. Check Approved List
        for key, record in cls.APPROVED_ACTIVES.items():
            if key in clean or clean in key:
                return {
                    "is_legal": True,
                    "is_banned": False,
                    "compound": record["name"],
                    "status": record["legal_status"],
                    "frac_group": record["frac_group"],
                    "phi_days": record["phi_days"],
                    "dosage": record["dosage"],
                    "safety_guideline": record["safety_profile"],
                    "organic_compliant": record["organic_certified"]
                }

        return {
            "is_legal": True,
            "is_banned": False,
            "compound": chemical_name,
            "status": "Unclassified / General Agricultural Input",
            "phi_days": 7,
            "safety_guideline": "Follow local manufacturer label and state agronomist advisory."
        }

    @classmethod
    def scan_for_regulatory_violations(cls, text: str) -> Optional[Dict[str, Any]]:
        """Scans arbitrary text (query or prescription) for banned chemical substances."""
        text_lower = text.lower()
        for key, record in cls.BANNED_PESTICIDES.items():
            if re.search(r"\b" + re.escape(key) + r"\b", text_lower):
                return {
                    "violation_detected": True,
                    "banned_chemical": record["name"],
                    "statutory_order": record["statutory_order"],
                    "hazard_class": record["hazard_classification"],
                    "statutory_warning": record["statutory_warning"],
                    "legal_alternative": record["approved_legal_alternative"]
                }
        return None
