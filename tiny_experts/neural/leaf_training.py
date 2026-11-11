"""Leaf-image training with separate transforms and source/case provenance."""

import json
import math
import os
from pathlib import Path
import random
import tempfile
import time

from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import datasets, models, transforms

from .text_features import canonical_hash, file_hash
from .training_data import split_manifest, split_records, validate_records


PREPROCESSING = {"size": 224, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}
LEAF_LABELS = ["bacterial_spot", "early_blight", "healthy", "late_blight", "powdery_mildew"]
MODELS_DIR = Path(__file__).resolve().parents[1] / "data" / "models"
DATASET_DIR = Path(__file__).resolve().parents[1] / "data" / "images" / "leaf_benchmark"


class LeafVisionNet(nn.Module):
    """MobileNetV3-small initialized locally, without pretrained downloads."""

    def __init__(self, num_classes=5):
        super().__init__()
        backbone = models.mobilenet_v3_small(weights=None)
        # Keep BatchNorm's normal training/evaluation running-statistics behavior,
        # using standard momentum so running_var converges within small CPU epoch budgets.
        for module in backbone.features.modules():
            if isinstance(module, nn.BatchNorm2d):
                module.momentum = 0.3
        self.features = backbone.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Linear(576, 128), nn.Hardswish(), nn.Dropout(0.1), nn.Linear(128, num_classes),
        )

    def forward(self, images):
        return self.classifier(self.pool(self.features(images)).flatten(1))


def image_transforms(training=False):
    operations = [transforms.Resize((224, 224))]
    if training:
        operations.append(transforms.RandomHorizontalFlip(p=0.5))
    operations.extend([
        transforms.ToTensor(),
        transforms.Normalize(mean=PREPROCESSING["mean"], std=PREPROCESSING["std"]),
    ])
    return transforms.Compose(operations)


class ImageRecords(Dataset):
    def __init__(self, rows, data_dir, *, training=False):
        self.rows = rows
        self.data_dir = Path(data_dir)
        self.transform = image_transforms(training)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(self.data_dir / row["path"]) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, LEAF_LABELS.index(row["labels"]["condition"])


def load_image_records(data_dir, manifest_path=None, *, demo=False):
    data_dir = Path(data_dir).resolve()
    if manifest_path is None:
        if not demo:
            raise ValueError("Supply reviewed --manifest JSONL, or explicitly use --demo for unreviewed image fixtures")
        folder = datasets.ImageFolder(data_dir)
        raw = [{
            "id": f"legacy-leaf-{index:05d}", "case_id": f"legacy-leaf-{index:05d}",
            "source_id": "bundled_unreviewed_leaf_demo",
            "path": str(Path(path).resolve().relative_to(data_dir)),
            "label": folder.classes[label], "reviewed": False,
            "provenance_note": "Unreviewed mixed image fixtures, predominantly synthetic; not a field-image benchmark.",
        } for index, (path, label) in enumerate(folder.samples)]
    else:
        with Path(manifest_path).open(encoding="utf-8") as stream:
            raw = [json.loads(line) for line in stream if line.strip()]
    prepared = []
    for row in raw:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise ValueError("Image records need a relative path")
        path = (data_dir / row["path"]).resolve()
        try:
            relative = path.relative_to(data_dir)
        except ValueError as error:
            raise ValueError("Image paths must stay within --data-dir") from error
        if not path.is_file():
            raise ValueError(f"Image file does not exist: {relative}")
        if not demo and row.get("synthetic") is not False:
            raise ValueError("Reviewed image records must explicitly declare synthetic=false")
        digest = file_hash(path)
        item = dict(row)
        item.update({
            "path": relative.as_posix(), "image_sha256": digest,
            # Exact duplicate images participate in the same leakage grouping.
            "text": digest, "labels": {"condition": row.get("label")},
        })
        prepared.append(item)
    return validate_records(prepared, {"condition": LEAF_LABELS}, demo=demo)


def evaluate_images(model, loader, *, threshold):
    model.eval()
    matrix = [[0] * len(LEAF_LABELS) for _ in LEAF_LABELS]
    total = correct = accepted = accepted_correct = 0
    total_loss = 0.0
    with torch.inference_mode():
        for images, labels in loader:
            logits = model(images)
            if not torch.isfinite(logits).all().item():
                raise ValueError("Image model returned non-finite logits")
            total_loss += float(nn.functional.cross_entropy(logits, labels).item()) * len(labels)
            score, prediction = torch.softmax(logits, dim=1).max(dim=1)
            matches = prediction == labels
            selected = score >= threshold
            total += len(labels)
            correct += int(matches.sum().item())
            accepted += int(selected.sum().item())
            accepted_correct += int((matches & selected).sum().item())
            for expected, predicted in zip(labels.tolist(), prediction.tolist()):
                matrix[expected][predicted] += 1
    if not total:
        raise ValueError("Evaluation split is empty")
    per_class = {}
    for index, label in enumerate(LEAF_LABELS):
        support = sum(matrix[index])
        predicted_count = sum(row[index] for row in matrix)
        true_positive = matrix[index][index]
        precision = true_positive / predicted_count if predicted_count else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"support": support, "precision": precision, "recall": recall, "f1": f1}
    return {
        "count": total, "loss": total_loss / total, "accuracy": correct / total,
        "macro_f1": sum(row["f1"] for row in per_class.values()) / len(LEAF_LABELS),
        "per_class": per_class, "confusion_matrix": matrix,
        "coverage_at_threshold": accepted / total,
        "accuracy_when_accepted": accepted_correct / accepted if accepted else None,
        "score_type": "uncalibrated_softmax",
    }


def train_leaf_vision(
    epochs=10, batch_size=16, lr=0.003, *, data_dir=DATASET_DIR,
    manifest_path=None, output_dir=None, demo=False, seed=42, patience=5,
    threshold=0.8, threads=1, overwrite=False,
):
    if any(type(value) is not int or value < 1 for value in (epochs, batch_size, patience, threads)):
        raise ValueError("Epochs, batch size, patience, and threads must be positive integers")
    if not math.isfinite(lr) or lr <= 0 or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid learning rate or threshold")
    output = Path(output_dir) if output_dir else MODELS_DIR / "leaf-demo" if demo else MODELS_DIR
    filenames = ("leaf_vision_mobilenet.pt", "leaf_vision_splits.json", "leaf_vision_manifest.json")
    if any((output / name).exists() for name in filenames) and not overwrite:
        raise ValueError("A leaf model output already exists; choose --output or intentionally use --overwrite")
    rows = load_image_records(data_dir, manifest_path, demo=demo)
    split_by = "case" if demo else "source"
    splits = split_records(rows, seed=seed, split_by=split_by, demo=demo)
    missing = set(LEAF_LABELS) - {row["labels"]["condition"] for row in splits["train"]}
    if missing:
        raise ValueError(f"Leaf classes have no training images: {sorted(missing)}")
    torch.set_num_threads(threads)
    random.seed(seed)
    torch.manual_seed(seed)
    datasets_by_split = {
        name: ImageRecords(part, data_dir, training=name == "train") for name, part in splits.items()
    }
    loaders = {
        name: DataLoader(
            dataset, batch_size=batch_size, shuffle=name == "train", num_workers=0,
            generator=torch.Generator().manual_seed(seed),
        )
        for name, dataset in datasets_by_split.items()
    }
    model = LeafVisionNet(len(LEAF_LABELS))
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0001)
    best_loss, best_epoch, stale = float("inf"), 0, 0
    best_state = None
    history = []
    started = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for images, labels in loaders["train"]:
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(images), labels)
            if not torch.isfinite(loss).item():
                raise ValueError("Image training produced non-finite loss")
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * len(labels)
        validation = evaluate_images(model, loaders["validation"], threshold=threshold)
        history.append({
            "epoch": epoch, "training_loss": total_loss / len(splits["train"]),
            "validation_loss": validation["loss"],
        })
        if validation["loss"] < best_loss:
            best_loss, best_epoch, stale = validation["loss"], epoch, 0
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
        else:
            stale += 1
        print(f"Epoch {epoch}/{epochs}: training loss {history[-1]['training_loss']:.4f}; validation loss {validation['loss']:.4f}", flush=True)
        if stale >= patience:
            break
    if best_state is None:
        raise ValueError("No valid image checkpoint was selected")
    model.load_state_dict(best_state, strict=True)
    metrics = {
        "best_epoch": best_epoch, "epochs_run": len(history), "history": history,
        "elapsed_seconds": time.perf_counter() - started,
        "interpretation": "Unreviewed demo only; no field-image accuracy claim." if demo else "Held-out source/case evaluation; inspect per-class support.",
        "validation": evaluate_images(model, loaders["validation"], threshold=threshold),
        "test": evaluate_images(model, loaders["test"], threshold=threshold),
    }
    split_info = split_manifest(splits, split_by=split_by)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".leaf-", dir=output.parent) as temporary:
        staging = Path(temporary)
        torch.save(best_state, staging / filenames[0])
        (staging / filenames[1]).write_text(json.dumps(split_info, indent=2) + "\n", encoding="utf-8")
        manifest = {
            "schema_version": 1, "status": "experimental" if demo else "reviewed_data",
            "architecture": "leaf_mobilenet_v3_small", "labels": LEAF_LABELS,
            "weights_sha256": file_hash(staging / filenames[0]),
            "preprocessing": PREPROCESSING, "metrics": metrics, "threshold": threshold,
            "score_type": "uncalibrated_softmax",
            "dataset_sha256": canonical_hash(sorted(rows, key=lambda row: row["id"])),
            "group_split_sha256": canonical_hash(split_info),
            "splits_file_sha256": file_hash(staging / filenames[1]),
            "training": {
                "seed": seed, "batch_size": batch_size, "learning_rate": lr,
                "best_epoch": best_epoch, "selection_metric": "validation_cross_entropy",
                "source_separated": not demo, "pretrained_weights": None,
                "torch_version": str(torch.__version__),
            },
            "limitations": [
                "Scores are uncalibrated; a reviewed-data marker does not establish deployment quality.",
            ] + (["The bundled images are predominantly synthetic unreviewed fixtures."] if demo else []),
        }
        (staging / filenames[2]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        for name in filenames:  # Manifest last; interrupted replacement fails its checksum.
            os.replace(staging / name, output / name)
    print(f"Saved {manifest['status']} leaf model to {output}; selected epoch {best_epoch}.", flush=True)
    return manifest
