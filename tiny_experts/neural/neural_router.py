from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional
from .text_expert import NeuralTextClassifier
from .text_features import vectorize

class NeuralRouterNet(nn.Module):
    """
    Legacy shallow text-domain classifier architecture.

    This is not a transformer mixture-of-experts implementation. Retained for
    inspection and API compatibility; new training uses the shared text trainer.
    """

    EXPERTS_LIST = [
        "vision", "botany", "wildlife", "toxicity", "biology",
        "genetics", "cell_biology", "mycology", "entomology", "ornithology",
        "ecology", "pathology", "marine", "microbiology", "evolution",
        "math", "format"
    ]

    def __init__(self, vocab_size: int = 500, hidden_dim: int = 128, num_experts: int = 17, top_k: int = 4):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = min(max(1, top_k), num_experts)
        self.vocab_size = vocab_size

        self.net = nn.Sequential(
            nn.Linear(vocab_size, hidden_dim),
            nn.SiLU(),
            nn.Dropout(p=0.1),
            nn.Linear(hidden_dim, 64),
            nn.SiLU(),
            nn.Linear(64, num_experts)
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        Returns:
        - raw_logits: [batch_size, num_experts]
        - gating_probs: [batch_size, num_experts]
        - top_k_indices: [batch_size, top_k]
        """
        logits = self.net(x)
        probs = F.softmax(logits, dim=-1)
        top_k_probs, top_k_indices = torch.topk(probs, self.top_k, dim=-1)
        return logits, probs, top_k_indices

    @staticmethod
    def compute_auxiliary_load_balancing_loss(gating_probs: torch.Tensor) -> torch.Tensor:
        """
        Calculates standard MoE auxiliary load balancing loss:
        L_balance = N * sum(f_i * P_i)
        where f_i is the fraction of batch routed to expert i, and P_i is the average probability.
        Penalizes uneven load distribution across the 17 micro-experts.
        """
        batch_size, num_experts = gating_probs.shape
        # Average probability per expert across the batch
        p_avg = torch.mean(gating_probs, dim=0)

        # Fraction of routing decisions
        _, top1_idx = torch.topk(gating_probs, 1, dim=-1)
        one_hot = F.one_hot(top1_idx.squeeze(-1), num_classes=num_experts).float()
        f_fraction = torch.mean(one_hot, dim=0)

        # MoE balance loss formula
        loss = num_experts * torch.sum(f_fraction * p_avg)
        return loss

# Compatibility name only; it does not imply DeepSeek architecture or quality.
DeepSeekMoERouterNet = NeuralRouterNet


class NeuralRoutingClassifier(NeuralTextClassifier):
    """Optional verified domain router; an unavailable router returns no choices."""

    BUNDLE_DIR = Path(__file__).resolve().parents[1] / "data" / "models" / "router"

    def __init__(
        self, vocab_size: Optional[int] = None, top_k: int = 4, *,
        bundle_dir=None, allow_experimental: bool = False,
    ):
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.top_k = top_k
        super().__init__(
            bundle_dir if bundle_dir is not None else self.BUNDLE_DIR,
            expected_expert_id="router", allow_experimental=allow_experimental,
        )
        if self.available and (
            self.manifest.get("primary_head") != "expert"
            or (vocab_size is not None and vocab_size != len(self.vocab))
        ):
            self.model, self.vocab, self.manifest = None, {}, {}
            self.available = False
            self.load_error = "Incompatible router head or requested feature dimension"

    @property
    def vocab_size(self):
        return len(self.vocab)

    def text_to_vector(self, text: str) -> torch.Tensor:
        return torch.tensor(vectorize(text, self.vocab), dtype=torch.float32)

    def predict_active_experts(self, query: str, threshold: Optional[float] = None) -> List[str]:
        result = self.predict(query, min_score=threshold)
        if result["abstained"]:
            return []
        minimum = self.manifest["inference"]["min_score"] if threshold is None else threshold
        rejected = self.manifest["inference"].get("abstain_labels", {}).get("expert", [])
        scores = result["predictions"]["expert"]["scores"]
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [name for name, score in ranked[:self.top_k] if score >= minimum and name not in rejected]


NeuralMoERouter = NeuralRoutingClassifier  # Legacy name; this is not a mixture-of-experts model.
