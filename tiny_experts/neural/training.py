"""Reusable CPU training for bounded, supervised text classification experts."""

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import shutil
import tempfile
import time

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .text_expert import ARCHITECTURE, SCHEMA_VERSION, MultiHeadTextNet, configuration_hash, validate_heads
from .text_features import FEATURE_VERSION, build_vocabulary, canonical_hash, file_hash, vectorize
from .training_data import split_manifest, split_records, validate_records


@dataclass
class TrainingConfig:
    expert_id: str
    heads: dict[str, list[str]]
    primary_head: str
    vocab_size: int = 1000
    hidden_dim: int = 160
    representation_dim: int = 112
    dropout: float = 0.1
    epochs: int = 50
    batch_size: int = 16
    learning_rate: float = 0.003
    weight_decay: float = 0.0001
    patience: int = 8
    min_delta: float = 0.0001
    seed: int = 42
    threads: int = 1
    validation_fraction: float = 0.15
    test_fraction: float = 0.15
    min_score: float = 0.8
    head_weights: dict[str, float] = field(default_factory=dict)
    abstain_labels: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, values: dict):
        if not isinstance(values, dict):
            raise ValueError("Training configuration must be an object")
        unknown = set(values) - {item.name for item in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown configuration fields: {sorted(unknown)}")
        try:
            config = cls(**values)
        except TypeError as error:
            raise ValueError(f"Invalid training configuration: {error}") from error
        config.validate()
        return config

    def validate(self):
        validate_heads(self.heads)
        if not isinstance(self.expert_id, str) or not self.expert_id.strip():
            raise ValueError("expert_id is required")
        if self.primary_head not in self.heads:
            raise ValueError("primary_head must name a configured head")
        for name in ("vocab_size", "hidden_dim", "representation_dim", "epochs", "batch_size", "patience", "threads"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("dropout", "learning_rate", "weight_decay", "min_delta", "validation_fraction", "test_fraction", "min_score"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0 <= self.dropout < 1 or not 0 <= self.min_score <= 1:
            raise ValueError("Invalid dropout or acceptance score")
        if self.learning_rate <= 0 or self.weight_decay < 0 or self.min_delta < 0:
            raise ValueError("Invalid optimization settings")
        if not isinstance(self.head_weights, dict) or set(self.head_weights) - set(self.heads):
            raise ValueError("head_weights must name configured heads")
        if any(not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight <= 0 for weight in self.head_weights.values()):
            raise ValueError("Head weights must be finite and positive")
        if not isinstance(self.abstain_labels, dict):
            raise ValueError("abstain_labels must be an object")
        for head, labels in self.abstain_labels.items():
            if head not in self.heads or not isinstance(labels, list) or any(label not in self.heads[head] for label in labels):
                raise ValueError("Unknown abstention head or label")


def _encode(rows, vocab, heads):
    features = torch.tensor([vectorize(row["text"], vocab) for row in rows], dtype=torch.float32)
    labels = {
        name: torch.tensor([values.index(row["labels"][name]) for row in rows], dtype=torch.long)
        for name, values in heads.items()
    }
    return features, labels


def _loss(outputs, labels, config):
    return sum(
        config.head_weights.get(name, 1.0) * nn.functional.cross_entropy(outputs[name], labels[name])
        for name in config.heads
    )


def evaluate(model, features, labels, config):
    model.eval()
    with torch.inference_mode():
        outputs = model(features)
        loss = float(_loss(outputs, labels, config).item())
    known = features.abs().sum(dim=1) > 0
    result = {"count": len(features), "zero_feature_inputs": int((~known).sum().item()), "weighted_cross_entropy": loss, "heads": {}}
    for name, names in config.heads.items():
        probabilities = torch.softmax(outputs[name], dim=-1)
        scores, prediction = probabilities.max(dim=1)
        target = labels[name]
        correct = (prediction == target) & known
        accepted = known & (scores >= config.min_score)
        for rejected_label in config.abstain_labels.get(name, []):
            accepted &= prediction != names.index(rejected_label)
        # Last matrix column is explicit abstention for zero-feature examples.
        matrix = [[0] * (len(names) + 1) for _ in names]
        for expected, predicted, valid in zip(target.tolist(), prediction.tolist(), known.tolist()):
            matrix[expected][predicted if valid else len(names)] += 1
        per_class = {}
        f1_values = []
        for index, label in enumerate(names):
            tp = matrix[index][index]
            support = sum(matrix[index])
            predicted_count = sum(row[index] for row in matrix)
            precision = tp / predicted_count if predicted_count else 0.0
            recall = tp / support if support else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            per_class[label] = {"support": support, "precision": precision, "recall": recall, "f1": f1}
            f1_values.append(f1)
        accepted_count = int(accepted.sum().item())
        result["heads"][name] = {
            "accuracy": float(correct.float().mean().item()),
            "macro_f1": sum(f1_values) / len(f1_values),
            "negative_log_likelihood": float(nn.functional.cross_entropy(outputs[name], target).item()),
            "class_coverage": sum(item["support"] > 0 for item in per_class.values()) / len(names),
            "per_class": per_class,
            "confusion_matrix": matrix,
            "confusion_rows": names,
            "confusion_columns": names + [None],
            "acceptance_threshold": config.min_score,
            "accepted_count": accepted_count,
            "coverage_at_threshold": accepted_count / len(features),
            "accuracy_when_accepted": float(correct[accepted].float().mean().item()) if accepted_count else None,
            "score_type": "uncalibrated_softmax",
        }
    return result


def _json_file(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def save_bundle(output, model, vocab, config, metrics, splits, *, dataset_hash, demo, overwrite=False):
    output = Path(output)
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise ValueError(f"Output is not empty: {output}; choose a new directory or --overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        architecture = {
            "name": ARCHITECTURE, "feature_dim": len(vocab), "hidden_dim": config.hidden_dim,
            "representation_dim": config.representation_dim, "dropout": config.dropout,
        }
        _json_file(staging / "vocab.json", vocab)
        _json_file(staging / "metrics.json", metrics)
        _json_file(staging / "splits.json", splits)
        checkpoint = {
            "schema_version": SCHEMA_VERSION,
            "expert_id": config.expert_id,
            "configuration_sha256": configuration_hash(architecture, config.heads),
            "vocabulary_sha256": file_hash(staging / "vocab.json"),
            "state_dict": {name: value.detach().cpu() for name, value in model.state_dict().items()},
        }
        torch.save(checkpoint, staging / "model.pt")
        artifacts = {name: file_hash(staging / name) for name in ("model.pt", "vocab.json", "metrics.json", "splits.json")}
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "expert_id": config.expert_id,
            "status": "experimental" if demo else "reviewed_data",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "architecture": architecture,
            "feature_version": FEATURE_VERSION,
            "heads": config.heads,
            "primary_head": config.primary_head,
            "inference": {
                "score_type": "uncalibrated_softmax", "min_score": config.min_score,
                "abstain_labels": config.abstain_labels, "zero_feature_policy": "abstain",
            },
            "artifacts": artifacts,
            "dataset_sha256": dataset_hash,
            "group_split_sha256": canonical_hash(splits),
            "training_config": asdict(config),
            "training": {
                "best_epoch": metrics["best_epoch"],
                "epochs_run": metrics["epochs_run"],
                "selection_metric": "validation_weighted_cross_entropy",
                "augmentation": "none",
                "reviewed_data_required": not demo,
                "source_separated": splits["source_separated"],
                "torch_version": str(torch.__version__),
            },
            "limitations": [
                "Categorical text classifier; does not read books or generate explanations.",
                "Softmax scores are uncalibrated and do not certify correctness.",
                "Reviewed-data status records the input workflow, not production readiness.",
            ] + (["Unreviewed demo data; results must not be reported as generalization quality."] if demo else []),
        }
        _json_file(staging / "manifest.json", manifest)
        if not output.exists():
            os.replace(staging, output)
        else:
            # Commit the manifest last. During replacement a hash mismatch
            # disables loading; incompatible pairs can never be used silently.
            for filename in ("model.pt", "vocab.json", "metrics.json", "splits.json", "manifest.json"):
                os.replace(staging / filename, output / filename)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def train_expert(config, records, output, *, demo=False, split_by="source", overwrite=False):
    """Train from labeled records; books are not used implicitly."""
    if isinstance(config, dict):
        config = TrainingConfig.from_dict(config)
    config.validate()
    output = Path(output)
    if output.exists() and (not output.is_dir() or (any(output.iterdir()) and not overwrite)):
        raise ValueError(f"Output is not an empty directory: {output}; use --overwrite intentionally")
    records = validate_records(records, config.heads, demo=demo)
    splits = split_records(
        records, seed=config.seed, validation_fraction=config.validation_fraction,
        test_fraction=config.test_fraction, split_by=split_by, demo=demo,
    )
    unsupported = {
        head: [label for label in labels if not any(row["labels"][head] == label for row in splits["train"])]
        for head, labels in config.heads.items()
    }
    unsupported = {head: labels for head, labels in unsupported.items() if labels}
    if unsupported and not demo:
        raise ValueError(f"Configured labels without training examples: {unsupported}")
    vocab = build_vocabulary((row["text"] for row in splits["train"]), config.vocab_size)
    if not vocab:
        raise ValueError("Training text produced an empty vocabulary")
    encoded = {name: _encode(rows, vocab, config.heads) for name, rows in splits.items()}
    torch.set_num_threads(config.threads)
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    model = MultiHeadTextNet(
        len(vocab), config.heads, config.hidden_dim, config.representation_dim, config.dropout,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config.epochs)
    names = list(config.heads)
    train_x, train_y = encoded["train"]
    loader = DataLoader(
        TensorDataset(train_x, *(train_y[name] for name in names)), batch_size=config.batch_size,
        shuffle=True, generator=torch.Generator().manual_seed(config.seed),
    )
    best_loss = float("inf")
    best_state = None
    best_epoch = 0
    stale = 0
    history = []
    started = time.perf_counter()
    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = _loss(model(batch[0]), dict(zip(names, batch[1:])), config)
            if not torch.isfinite(loss).item():
                raise ValueError("Training produced a non-finite loss")
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * len(batch[0])
        scheduler.step()
        validation = evaluate(model, *encoded["validation"], config)
        validation_loss = validation["weighted_cross_entropy"]
        if not math.isfinite(validation_loss):
            raise ValueError("Validation produced a non-finite loss")
        history.append({
            "epoch": epoch, "training_weighted_cross_entropy": total_loss / len(train_x),
            "validation_weighted_cross_entropy": validation_loss,
        })
        meaningful_improvement = validation_loss < best_loss - config.min_delta
        if validation_loss < best_loss:
            best_loss, best_epoch = validation_loss, epoch
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
        stale = 0 if meaningful_improvement else stale + 1
        print(f"Epoch {epoch}/{config.epochs}: train loss {total_loss / len(train_x):.4f}; validation loss {validation_loss:.4f}", flush=True)
        if stale >= config.patience:
            break
    if best_state is None:
        raise ValueError("No finite validation checkpoint was produced")
    model.load_state_dict(best_state, strict=True)
    model.eval()
    metrics = {
        "best_epoch": best_epoch, "epochs_run": len(history), "history": history,
        "elapsed_seconds": time.perf_counter() - started,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "unsupported_training_labels": unsupported,
        "interpretation": "Demo execution only; not an accuracy claim." if demo else "Held-out source/case evaluation; inspect class coverage and sample counts.",
        "splits": {name: evaluate(model, *tensors, config) for name, tensors in encoded.items()},
    }
    manifest = save_bundle(
        output, model, vocab, config, metrics, split_manifest(splits, split_by=split_by),
        dataset_hash=canonical_hash(sorted(records, key=lambda row: row["id"])),
        demo=demo, overwrite=overwrite,
    )
    print(f"Saved {manifest['status']} bundle to {output}; selected epoch {best_epoch}.", flush=True)
    return {"manifest": manifest, "metrics": metrics, "output": str(output)}
