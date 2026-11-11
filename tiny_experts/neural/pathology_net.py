import os
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Any
from .text_expert import NeuralTextClassifier
from .text_features import tokenize, vectorize

class PathologyExpertNet(nn.Module):
    """
    Legacy multi-head plant-condition classifier architecture.
    Spans all 6 Specialized Clinical Divisions:
    1. Fungi & Oomycete Blights/Rusts
    2. Agricultural Bacteriology & Vascular Cankers
    3. Plant Virology, Tobamoviruses & Vector Biology
    4. Plant Nematology & Soil Disease Complexes
    5. Abiotic Disorders & Nutritional Deficiencies (Differential Diagnosis)
    6. Clinical Laboratory Diagnostic Assays & Molecular Primers

    Its original checkpoint is retained only for inspection, not enabled inference.
    The new trainer saves versioned bundles using MultiHeadTextNet. Original heads:
    1. Clinical Diagnostic Entity
    2. Exact Causal Pathogen / Stressor (Latin Binomial / Viral Code / Abiotic Deficit)
    3. Causal Biological Kingdom / Class
    4. Recommended Clinical Laboratory Verification Assay
    5. Rational IPM / Therapeutic Action Strategy
    """

    DISEASES = [
        # Fungi & Oomycetes
        "Early Blight",
        "Late Blight",
        "Powdery Mildew",
        "Downy Mildew",
        "Fusarium Wilt",
        "Grey Mold",
        "Black Spot",
        "Apple Scab",
        "Wheat Stem Rust",
        "Rice Blast",
        "Fusarium Head Blight",
        # Bacteria
        "Bacterial Spot",
        "Bacterial Wilt",
        "Fire Blight",
        "Bacterial Speck",
        "Bacterial Soft Rot",
        "Crown Gall",
        # Viruses & Viroids
        "Tomato Brown Rugose Fruit Virus",
        "Tobacco Mosaic Virus",
        "Tomato Yellow Leaf Curl Virus",
        "Tomato Spotted Wilt Virus",
        "Potato Spindle Tuber Viroid",
        # Nematodes & Soil Complexes
        "Root Knot Nematode",
        "Nematode Fusarium Wilt Complex",
        # Abiotic Lookalike Disorders
        "Blossom End Rot",
        "Herbicide Drift Injury",
        "Iron Deficiency Chlorosis",
        "Nitrogen Deficiency",
        "Sunscald Injury",
        "Catfacing Malformation",
        # Indian Agricultural & Tropical Staple Diseases (ICAR / TNAU)
        "Rice Bacterial Leaf Blight",
        "Rice Sheath Blight",
        "Cotton Leaf Curl Virus",
        "Cotton Bacterial Blight",
        "Chickpea Fusarium Wilt",
        "Pigeonpea Sterility Mosaic",
        "Sugarcane Red Rot",
        "Citrus Greening Huanglongbing",
        "Mango Malformation",
        # Defense & Assays
        "Systemic Acquired Resistance",
        "Clinical Laboratory Diagnostic Protocol",
        "General Phytopathology"
    ]

    PATHOGENS = [
        # Fungi & Oomycetes
        "Alternaria solani",
        "Phytophthora infestans",
        "Podosphaera xanthii",
        "Pseudoperonospora cubensis",
        "Fusarium oxysporum",
        "Botrytis cinerea",
        "Diplocarpon rosae",
        "Venturia inaequalis",
        "Puccinia graminis",
        "Magnaporthe oryzae",
        "Fusarium graminearum",
        # Bacteria
        "Xanthomonas campestris",
        "Ralstonia solanacearum",
        "Erwinia amylovora",
        "Pseudomonas syringae",
        "Pectobacterium carotovorum",
        "Agrobacterium tumefaciens",
        # Viruses & Viroids
        "Tomato Brown Rugose Fruit Virus (ToBRFV)",
        "Tobacco Mosaic Virus (TMV)",
        "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "Tomato Spotted Wilt Virus (TSWV)",
        "Potato Spindle Tuber Viroid (PSTVd)",
        # Nematodes & Soil Complexes
        "Meloidogyne incognita",
        "Meloidogyne Fusarium Synergistic Complex",
        # Abiotic Stressors
        "Abiotic Calcium Transport Deficiency",
        "Synthetic Auxin Herbicide 2,4-D Drift",
        "Alkaline Soil Insoluble Iron Deficiency",
        "Soil Available Nitrogen Depletion",
        "Solar Radiation Thermal Shock",
        "Cold Temperature Flower Bud Shock",
        # Indian Agricultural & Tropical Pathogens (ICAR / TNAU)
        "Xanthomonas oryzae pv. oryzae",
        "Rhizoctonia solani",
        "Cotton Leaf Curl Virus (CLCuV)",
        "Xanthomonas citri pv. malvacearum",
        "Fusarium oxysporum f. sp. ciceri",
        "Pigeonpea Sterility Mosaic Virus (PSMV)",
        "Colletotrichum falcatum",
        "Candidatus Liberibacter asiaticus",
        "Fusarium mangiferae",
        # Defense & General
        "Host Plant Innate Immune System",
        "Diagnostic Assay Protocol",
        "Unspecified Plant Pathogen"
    ]

    KINGDOMS = [
        "Fungus",
        "Oomycete",
        "Bacterium",
        "Virus",
        "Viroid",
        "Nematode",
        "Abiotic / Physiological Stress",
        "Host Immune Response"
    ]

    LAB_ASSAYS = [
        "KOH_String_Test_3Percent",
        "Vascular_Stem_Streaming_Assay",
        "Lateral_Flow_ImmunoStrip",
        "PCR_ITS_Fungal_Barcoding",
        "PCR_16S_Bacterial_Sequencing",
        "RT_qPCR_Viral_Amplification",
        "PARP_Selective_Media",
        "Kings_B_UV_Fluorescence",
        "Microscopic_Root_Gall_Index",
        "Soil_Moisture_And_Tissue_Ca_Assay",
        "General_Symptom_Triangulation"
    ]

    STRATEGIES = [
        "FRAC_M01_Copper_Protectant",
        "FRAC_M02_Sulfur_Protectant",
        "FRAC_07_SDHI_Respiration_Blocker",
        "FRAC_03_DMI_Sterol_Inhibitor",
        "FRAC_40_CAA_Oomycete_Specific",
        "Potassium_Bicarbonate_Shock",
        "Biofungicide_Bacillus_Lipopeptides",
        "Sanitation_Pruning_Debris_Removal",
        "Vector_Control_Thrips_Whitefly",
        "Biofumigation_Soil_Solarization",
        "Calcium_Moisture_Stabilization",
        "Herbicide_Decontamination_Buffer",
        "Systemic_Acquired_Resistance_Elicitation"
    ]

    def __init__(self, vocab_size: int = 1000, hidden_dim: int = 160, rep_dim: int = 112):
        super().__init__()
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim
        self.rep_dim = rep_dim

        # Representation backbone with LayerNorm, SiLU, and Dropout
        self.backbone = nn.Sequential(
            nn.Linear(vocab_size, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Dropout(p=0.1),
            nn.Linear(hidden_dim, rep_dim),
            nn.LayerNorm(rep_dim),
            nn.SiLU()
        )

        # 5 Multi-task diagnostic heads
        self.head_disease = nn.Linear(rep_dim, len(self.DISEASES))
        self.head_pathogen = nn.Linear(rep_dim, len(self.PATHOGENS))
        self.head_kingdom = nn.Linear(rep_dim, len(self.KINGDOMS))
        self.head_assay = nn.Linear(rep_dim, len(self.LAB_ASSAYS))
        self.head_strategy = nn.Linear(rep_dim, len(self.STRATEGIES))

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        rep = self.backbone(x)
        logits_disease = self.head_disease(rep)
        logits_pathogen = self.head_pathogen(rep)
        logits_kingdom = self.head_kingdom(rep)
        logits_assay = self.head_assay(rep)
        logits_strategy = self.head_strategy(rep)

        return {
            "disease_logits": logits_disease,
            "pathogen_logits": logits_pathogen,
            "kingdom_logits": logits_kingdom,
            "assay_logits": logits_assay,
            "strategy_logits": logits_strategy,
            "disease_probs": F.softmax(logits_disease, dim=-1),
            "pathogen_probs": F.softmax(logits_pathogen, dim=-1),
            "kingdom_probs": F.softmax(logits_kingdom, dim=-1),
            "assay_probs": F.softmax(logits_assay, dim=-1),
            "strategy_probs": F.softmax(logits_strategy, dim=-1)
        }

class NeuralPathologyClassifier(NeuralTextClassifier):
    """Pathology adapter for a verified classifier bundle, with explicit abstention."""

    BUNDLE_DIR = Path(__file__).resolve().parents[1] / "data" / "models" / "pathology"
    # Retained as legacy locations for inspection; never loaded as trained bundles.
    VOCAB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models", "pathology_vocab.json")
    WEIGHTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models", "expert_pathology.pt")

    def __init__(self, vocab_size: Optional[int] = None, *, bundle_dir=None, allow_experimental: bool = False):
        super().__init__(
            bundle_dir if bundle_dir is not None else self.BUNDLE_DIR,
            expected_expert_id="pathology", allow_experimental=allow_experimental,
        )
        if self.available and (
            self.manifest.get("primary_head") != "disease"
            or (vocab_size is not None and vocab_size != len(self.vocab))
        ):
            self.model, self.vocab, self.manifest = None, {}, {}
            self.available = False
            self.load_error = "Incompatible pathology head or requested feature dimension"

    @property
    def vocab_size(self):
        return len(self.vocab)

    tokenize = staticmethod(tokenize)

    def text_to_tensor(self, text: str) -> torch.Tensor:
        return torch.tensor([vectorize(text, self.vocab)], dtype=torch.float32)

    def predict(self, text: str, *, min_score: Optional[float] = None) -> Dict[str, Any]:
        result = super().predict(text, min_score=min_score)
        if not result["abstained"]:
            for name in ("disease", "pathogen", "kingdom", "assay", "strategy"):
                prediction = result["predictions"].get(name)
                if prediction is not None:
                    result[name] = prediction["label"]
                    # Kept for the application interface; explicitly uncalibrated.
                    result[f"{name}_confidence"] = prediction["score"]
        return result
