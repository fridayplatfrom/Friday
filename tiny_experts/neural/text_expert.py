"""Small supervised text experts with verifiable, fail-closed model bundles."""

import json
import math
from pathlib import Path
import re

import torch
from torch import nn

from .text_features import (
    FEATURE_VERSION, canonical_hash, file_hash, validate_vocabulary, vectorize,
)


SCHEMA_VERSION = 1
ARCHITECTURE = "multihead_mlp_v1"


def validate_heads(heads: dict) -> None:
    if not isinstance(heads, dict) or not heads:
        raise ValueError("At least one classification head is required")
    for name, labels in heads.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError("Head names must be lowercase identifiers")
        if hasattr(nn.Module(), name):
            raise ValueError(f"Reserved head name: {name}")
        if not isinstance(labels, list) or not labels or not all(isinstance(label, str) and label for label in labels):
            raise ValueError(f"{name}: labels must be nonempty strings")
        if len(set(labels)) != len(labels):
            raise ValueError(f"{name}: duplicate labels")


def configuration_hash(architecture: dict, heads: dict) -> str:
    return canonical_hash({"architecture": architecture, "heads": heads, "feature_version": FEATURE_VERSION})


class MultiHeadTextNet(nn.Module):
    """Two dense layers over word/bigram counts, with categorical task heads."""

    def __init__(
        self, feature_dim: int, heads: dict[str, list[str]], hidden_dim: int = 160,
        representation_dim: int = 112, dropout: float = 0.1,
    ):
        super().__init__()
        validate_heads(heads)
        if not (1 <= feature_dim <= 100_000 and 1 <= hidden_dim <= 2048 and 1 <= representation_dim <= 2048):
            raise ValueError("Model dimensions are outside supported small-classifier limits")
        if not 0 <= dropout < 1:
            raise ValueError("dropout must be in [0, 1)")
        self.backbone = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.SiLU(),
            nn.Dropout(dropout), nn.Linear(hidden_dim, representation_dim),
            nn.LayerNorm(representation_dim), nn.SiLU(),
        )
        self.heads = nn.ModuleDict({
            name: nn.Linear(representation_dim, len(labels))
            for name, labels in sorted(heads.items())
        })

    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        representation = self.backbone(features)
        return {name: head(representation) for name, head in self.heads.items()}


class NeuralTextClassifier:
    """Load only a complete compatible bundle; otherwise explicitly abstain.

    File hashes and checkpoint metadata detect mismatched artifacts. They do
    not certify training data truth or production accuracy.
    """

    def __init__(
        self, bundle_dir, *, expected_expert_id: str | None = None,
        allow_experimental: bool = False,
    ):
        self.bundle_dir = Path(bundle_dir)
        self.expected_expert_id = expected_expert_id
        self.allow_experimental = allow_experimental
        self.model = None
        self.vocab = {}
        self.manifest = {}
        self.available = False
        self.load_error = None
        self._load()

    @property
    def is_trained(self) -> bool:
        return self.available

    def _load(self) -> None:
        try:
            manifest_path = self.bundle_dir / "manifest.json"
            if not manifest_path.is_file():
                raise ValueError("No verified bundle manifest; legacy raw checkpoints are disabled")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("Unsupported model bundle schema")
            status = manifest.get("status")
            if status != "reviewed_data" and not (status == "experimental" and self.allow_experimental):
                raise ValueError("Experimental or unrecognized model status is not enabled")
            expert_id = manifest.get("expert_id")
            if not isinstance(expert_id, str) or not expert_id:
                raise ValueError("Model has no expert identity")
            if self.expected_expert_id is not None and expert_id != self.expected_expert_id:
                raise ValueError("Model belongs to a different expert")
            if manifest.get("feature_version") != FEATURE_VERSION:
                raise ValueError("Unsupported text preprocessing version")
            architecture = manifest.get("architecture", {})
            if architecture.get("name") != ARCHITECTURE:
                raise ValueError("Unsupported classifier architecture")
            heads = manifest.get("heads")
            validate_heads(heads)
            if manifest.get("primary_head") not in heads:
                raise ValueError("Unknown primary head")
            inference = manifest.get("inference", {})
            threshold = inference.get("min_score")
            if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
                raise ValueError("Invalid inference threshold")
            if inference.get("score_type") != "uncalibrated_softmax":
                raise ValueError("Unsupported score interpretation")
            abstain_labels = inference.get("abstain_labels", {})
            if not isinstance(abstain_labels, dict):
                raise ValueError("Invalid abstention labels")
            for head, labels in abstain_labels.items():
                if head not in heads or not isinstance(labels, list) or any(label not in heads[head] for label in labels):
                    raise ValueError("Unknown abstention label")
            artifacts = manifest.get("artifacts", {})
            for filename in ("model.pt", "vocab.json", "metrics.json", "splits.json"):
                expected_hash = artifacts.get(filename)
                if not isinstance(expected_hash, str) or file_hash(self.bundle_dir / filename) != expected_hash:
                    raise ValueError(f"Missing or mismatched artifact: {filename}")
            vocab = json.loads((self.bundle_dir / "vocab.json").read_text(encoding="utf-8"))
            validate_vocabulary(vocab, architecture["feature_dim"])
            checkpoint = torch.load(self.bundle_dir / "model.pt", map_location="cpu", weights_only=True)
            if not isinstance(checkpoint, dict):
                raise ValueError("Invalid checkpoint")
            expected_metadata = {
                "schema_version": SCHEMA_VERSION,
                "expert_id": expert_id,
                "configuration_sha256": configuration_hash(architecture, heads),
                "vocabulary_sha256": artifacts["vocab.json"],
            }
            if any(checkpoint.get(key) != value for key, value in expected_metadata.items()):
                raise ValueError("Checkpoint configuration, labels, or vocabulary do not match the manifest")
            model = MultiHeadTextNet(
                feature_dim=architecture["feature_dim"], heads=heads,
                hidden_dim=architecture["hidden_dim"],
                representation_dim=architecture["representation_dim"],
                dropout=architecture["dropout"],
            )
            model.load_state_dict(checkpoint["state_dict"], strict=True)
            if any(not torch.isfinite(value).all().item() for value in model.state_dict().values()):
                raise ValueError("Checkpoint contains non-finite parameters")
            model.eval()
            self.model, self.vocab, self.manifest = model, vocab, manifest
            self.available = True
        except Exception as error:
            # Never retain a partly loaded model or continue with random weights.
            self.model, self.vocab, self.manifest = None, {}, {}
            self.available = False
            self.load_error = f"{type(error).__name__}: {error}"

    def _abstain(self, reason: str) -> dict:
        return {
            "available": self.available, "is_trained": self.available,
            "abstained": True, "reason": reason, "predictions": {},
            "score_type": "uncalibrated_softmax",
        }

    def predict(self, text: str, *, min_score: float | None = None) -> dict:
        if not self.available or self.model is None:
            return self._abstain(self.load_error or "Model is unavailable")
        if not isinstance(text, str) or not text.strip():
            return self._abstain("Input text is empty")
        values = vectorize(text, self.vocab)
        if not any(values):
            return self._abstain("Input contains no recognized features")
        threshold = self.manifest["inference"]["min_score"] if min_score is None else min_score
        if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("min_score must be between zero and one")
        with torch.inference_mode():
            outputs = self.model(torch.tensor([values], dtype=torch.float32))
        predictions = {}
        for name, logits in outputs.items():
            if not torch.isfinite(logits).all().item():
                return self._abstain("Model returned non-finite scores")
            probabilities = torch.softmax(logits[0], dim=-1)
            score, index = probabilities.max(dim=0)
            labels = self.manifest["heads"][name]
            predictions[name] = {
                "label": labels[int(index.item())], "score": float(score.item()),
                "scores": dict(zip(labels, probabilities.tolist())),
            }
        primary = self.manifest["primary_head"]
        if predictions[primary]["score"] < threshold:
            return self._abstain("Primary score is below the configured acceptance threshold")
        for name, labels in self.manifest["inference"].get("abstain_labels", {}).items():
            if predictions[name]["label"] in labels:
                return self._abstain(f"{name} predicted an abstention category")
        return {
            "available": True, "is_trained": True, "abstained": False, "reason": None,
            "predictions": predictions, "score_type": "uncalibrated_softmax",
            "experimental": self.manifest["status"] == "experimental",
        }
