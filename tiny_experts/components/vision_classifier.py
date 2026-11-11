from typing import Any, Dict, Optional, List
import os
import json
import hashlib
from pathlib import Path
from ..matching import contains_term
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from .base_component import BaseComponent
from ..pipeline.knowledge_store import KnowledgeStore

class TinyVisionNet(nn.Module):
    """
    Ultra-lightweight species classifier (~2.5M params).
    Uses a MobileNetV3-Small backbone with a custom nature classification head.
    """
    def __init__(self, num_classes: int = 10):
        super().__init__()
        backbone = models.mobilenet_v3_small(weights=None)
        self.features = backbone.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Linear(576, 128),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(128, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.features(x)
        feat = self.pool(feat).flatten(1)
        return self.classifier(feat)

class LeafVisionNet(nn.Module):
    """
    Lightweight MobileNetV3-Small based classifier for Agricultural Leaf Pathology.
    Runtime performance must be measured on the deployment hardware.
    """
    def __init__(self, num_classes: int = 5):
        super().__init__()
        backbone = models.mobilenet_v3_small(weights=None)
        self.features = backbone.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Linear(576, 128),
            nn.Hardswish(),
            nn.Dropout(p=0.1),
            nn.Linear(128, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.features(x)
        feat = self.pool(feat).flatten(1)
        return self.classifier(feat)

class VisionClassifierAdapter(BaseComponent):
    """Loads optional neural image classifiers and performs explicit text entity lookup."""
    name = 'Vision Classifier Adapter'
    description = 'Loads optional neural image classifiers and performs explicit text entity lookup.'
    component_kind = 'neural_adapter'
    uses_neural_model = True
    updates_parameters_at_inference = False

    SPECIES_CATALOG = [
        {
            "id": "monarch_butterfly", "name": "Monarch Butterfly", "category": "insect", "scientific": "Danaus plexippus",
            "aliases": ["monarch butterfly", "orange and black wings", "monarch"]
        },
        {
            "id": "honeybee", "name": "European Honeybee", "category": "insect", "scientific": "Apis mellifera",
            "aliases": ["honeybee", "honey bee", "worker bee"]
        },
        {
            "id": "sunflower", "name": "Common Sunflower", "category": "plant", "scientific": "Helianthus annuus",
            "aliases": ["sunflower", "large yellow petals", "sun flower"]
        },
        {
            "id": "house_sparrow", "name": "House Sparrow", "category": "bird", "scientific": "Passer domesticus",
            "aliases": ["house sparrow", "small brown sparrow"]
        },
        {
            "id": "bald_eagle", "name": "Bald Eagle", "category": "bird", "scientific": "Haliaeetus leucocephalus",
            "aliases": ["bald eagle", "white head raptor", "eagle"]
        },
        {
            "id": "poison_ivy", "name": "Poison Ivy", "category": "plant", "scientific": "Toxicodendron radicans",
            "aliases": ["poison ivy", "three shiny leaves", "leaves of three", "three leaves", "shiny leaves"]
        },
        {
            "id": "deadly_nightshade", "name": "Deadly Nightshade", "category": "plant", "scientific": "Atropa belladonna",
            "aliases": ["deadly nightshade", "belladonna", "purple bell-shaped flower"]
        },
        {
            "id": "red_fox", "name": "Red Fox", "category": "animal", "scientific": "Vulpes vulpes",
            "aliases": ["red fox", "bushy tail fox", "vulpes"]
        },
        {
            "id": "white_oak", "name": "White Oak Tree", "category": "plant", "scientific": "Quercus alba",
            "aliases": ["white oak", "white oak tree", "oak tree"]
        },
        {
            "id": "monarch_caterpillar", "name": "Monarch Caterpillar", "category": "insect", "scientific": "Danaus plexippus larva",
            "aliases": ["monarch caterpillar", "striped caterpillar"]
        }
    ]

    LEAF_CLASSES = [
        {"id": "bacterial_spot", "name": "Bacterial Spot", "scientific": "Xanthomonas campestris", "category": "plant_pathology"},
        {"id": "early_blight", "name": "Early Blight", "scientific": "Alternaria solani", "category": "plant_pathology"},
        {"id": "healthy", "name": "Healthy Plant Leaf", "scientific": "Solanaceae", "category": "plant"},
        {"id": "late_blight", "name": "Late Blight", "scientific": "Phytophthora infestans", "category": "plant_pathology"},
        {"id": "powdery_mildew", "name": "Powdery Mildew", "scientific": "Podosphaera xanthii", "category": "plant_pathology"}
    ]

    PHYSICS_DIAGRAM_CLASSES = [
        {"id": "carnot_pv_cycle", "name": "Carnot P-V Thermodynamic Cycle", "scientific": "thermodynamics_stat_mech", "category": "physics_diagram"},
        {"id": "inclined_plane", "name": "Inclined Plane Free-Body Diagram", "scientific": "classical_mechanics", "category": "physics_diagram"},
        {"id": "parallel_circuit", "name": "Parallel Resistor Network Schematic", "scientific": "electromagnetism", "category": "physics_diagram"},
        {"id": "quantum_energy_levels", "name": "Quantum Energy Level Transition Diagram", "scientific": "quantum_mechanics", "category": "physics_diagram"},
        {"id": "snell_refraction", "name": "Snell's Law Optical Refraction Diagram", "scientific": "optics_waves", "category": "physics_diagram"},
    ]

    def __init__(self, model_dir=None, allow_experimental=False):
        super().__init__(name='Vision Classifier Adapter', description='Loads optional neural image classifiers and performs explicit text entity lookup.')
        self.leaf_model = None
        self.physics_vision_model = None
        self.physics_manifest = None
        self.vision_bundles: Dict[str, Dict[str, Any]] = {}
        self.load_error = "No compatible, reviewed leaf model bundle is installed."
        self.manifest = None
        model_dir = Path(model_dir) if model_dir else Path(__file__).parents[1] / "data" / "models"
        manifest_file = model_dir / "leaf_vision_manifest.json"
        checkpoint = model_dir / "leaf_vision_mobilenet.pt"
        try:
            if manifest_file.exists():
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                if manifest.get("status") != "reviewed_data" and not allow_experimental:
                    raise ValueError("Experimental image model is disabled by default.")
                if manifest.get("architecture") != "leaf_mobilenet_v3_small":
                    raise ValueError("Unrecognized image model architecture.")
                if manifest.get("labels") != [c["id"] for c in self.LEAF_CLASSES]:
                    raise ValueError("Image label order differs from the runtime catalog.")
                expected = {"size": 224, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}
                if manifest.get("preprocessing") != expected:
                    raise ValueError("Image preprocessing does not match the saved model.")
                if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != manifest.get("weights_sha256"):
                    raise ValueError("Image checkpoint checksum mismatch.")
                candidate = LeafVisionNet(num_classes=len(self.LEAF_CLASSES))
                candidate.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
                if not all(torch.isfinite(t).all() for t in candidate.state_dict().values()):
                    raise ValueError("Image checkpoint contains non-finite parameters.")
                candidate.eval()
                self.leaf_model = candidate
                self.manifest = manifest
                self.load_error = None
                self.vision_bundles["leaf_vision"] = {
                    "model": candidate,
                    "manifest": manifest,
                    "classes": self.LEAF_CLASSES,
                    "source": "leaf_model",
                }
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            self.load_error = str(exc)

        # Dynamically load physics_vision bundle if present
        phys_manifest_file = model_dir / "physics_vision_manifest.json"
        phys_checkpoint = model_dir / "physics_vision_mobilenet.pt"
        try:
            if phys_manifest_file.exists() and phys_checkpoint.exists():
                p_man = json.loads(phys_manifest_file.read_text(encoding="utf-8"))
                if (p_man.get("status") == "reviewed_data" or allow_experimental) and (
                    hashlib.sha256(phys_checkpoint.read_bytes()).hexdigest() == p_man.get("weights_sha256")
                ):
                    p_net = LeafVisionNet(num_classes=len(self.PHYSICS_DIAGRAM_CLASSES))
                    p_net.load_state_dict(torch.load(phys_checkpoint, map_location="cpu", weights_only=True), strict=True)
                    p_net.eval()
                    self.physics_vision_model = p_net
                    self.physics_manifest = p_man
                    self.vision_bundles["physics_vision"] = {
                        "model": p_net,
                        "manifest": p_man,
                        "classes": self.PHYSICS_DIAGRAM_CLASSES,
                        "source": "physics_vision_model",
                    }
        except Exception:
            pass

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)), transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def route_image_bundle(self, pil_image: Image.Image, query: str = "", domain_hint: str = "") -> str:
        """3-Signal Multimodal Image Router (Pixel Statistics + Query Text + Domain Hint)."""
        q_lower = (query + " " + domain_hint).lower()
        physics_terms = ("circuit", "resistor", "carnot", "incline", "ramp", "refraction", "snell", "quantum", "diagram", "physics", "thermodynamic")
        leaf_terms = ("leaf", "blight", "mildew", "plant", "tomato", "potato", "spot", "pathology")

        if any(t in q_lower for t in physics_terms) and "physics_vision" in self.vision_bundles:
            return "physics_vision"
        if any(t in q_lower for t in leaf_terms):
            return "leaf_vision"

        # Signal 1: Raw pixel schematic vs natural leaf photo check
        # Schematic diagrams rendered on dark/white backgrounds have distinct RGB channel balance vs green foliage
        if "physics_vision" in self.vision_bundles:
            small = pil_image.resize((32, 32))
            pixels = list(small.getdata())
            dark_slate_count = sum(1 for r, g, b in pixels if r < 45 and g < 55 and 30 < b < 85)
            if dark_slate_count > len(pixels) * 0.45:
                return "physics_vision"
        return "leaf_vision"

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        image_input = context.get("image")
        hint = str(context.get("hint_species") or "").strip()
        query = str(context.get("query") or "")
        domain_hint = str(context.get("vision_domain") or "").strip()
        if image_input is not None:
            try:
                if isinstance(image_input, (str, os.PathLike)):
                    with Image.open(image_input) as opened:
                        pil_image = opened.convert("RGB")
                elif isinstance(image_input, Image.Image):
                    pil_image = image_input.convert("RGB")
                else:
                    raise ValueError("Image must be a local file or a PIL image.")

                target_bundle_name = self.route_image_bundle(pil_image, query=query, domain_hint=domain_hint)
                bundle = self.vision_bundles.get(target_bundle_name)
                if bundle is None:
                    if self.leaf_model is None:
                        return {"detected": False, "status": "unavailable", "confidence": None,
                                "message": self.load_error, "source": "image_model_unavailable"}
                    bundle = self.vision_bundles["leaf_vision"]

                tensor = self.transform(pil_image).unsqueeze(0)
                with torch.inference_mode():
                    scores = bundle["model"](tensor).softmax(dim=1)[0]
                score, index = scores.max(dim=0)
                score = float(score.item())
                threshold = float(bundle["manifest"].get("threshold", 0.8))
                if score < threshold:
                    return {"detected": False, "status": "abstained", "confidence": score,
                            "score_type": "uncalibrated_softmax", "message": "No candidate exceeds the configured threshold."}
                entry = bundle["classes"][int(index)]
                return {"detected": True, "status": "candidate", "species": entry["name"],
                        "diagram_id": entry["id"],
                        "scientific_name": entry["scientific"], "category": entry["category"],
                        "confidence": score, "score_type": "uncalibrated_softmax",
                        "source": bundle["source"], "bundle": target_bundle_name,
                        "identity_verified": False,
                        "message": f"Candidate from {target_bundle_name}; not a confirmed identification."}
            except (OSError, ValueError, RuntimeError) as exc:
                return {"detected": False, "status": "invalid_input", "confidence": None, "message": str(exc)}
        for entry in self.SPECIES_CATALOG:
            names = [entry["name"], entry["id"].replace("_", " "), entry["scientific"]]
            if any((hint and hint.casefold() == name.casefold()) or contains_term(query, name) for name in names):
                return {"detected": True, "status": "provided_entity", "species": entry["name"],
                        "scientific_name": entry["scientific"], "category": entry["category"],
                        "confidence": None, "identity_verified": False,
                        "source": "user_hint" if hint else "text_entity_linker"}
        return {"detected": False, "status": "no_image", "confidence": None,
                "species": hint or None, "source": "user_hint" if hint else "none",
                "message": "No image inference was performed. Text hints are not visual identification."}


# Compatibility for existing integrations and model-training imports.
VisionExpert = VisionClassifierAdapter
