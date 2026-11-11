"""Regression gates for leakage, artifact integrity, and real CPU train/load."""

import copy
import json
from pathlib import Path
import shutil

import pytest
import torch

from tiny_experts.neural.text_expert import NeuralTextClassifier
from tiny_experts.neural.text_features import build_vocabulary, file_hash
from tiny_experts.neural.training import TrainingConfig, train_expert
from tiny_experts.neural.training_data import split_records, validate_records


def toy_records():
    # Deliberately tiny synthetic test fixtures, not an external quality benchmark.
    texts = {
        "train": [
            ("plant green leaf grows", "plant", "growth"),
            ("plant roots leaf growth", "plant", "growth"),
            ("bird wings fly flight", "bird", "flight"),
            ("bird feathers wing flight", "bird", "flight"),
        ],
        "validation": [
            ("plant leaf validationsecret", "plant", "growth"),
            ("bird flight validationsecret", "bird", "flight"),
        ],
        "test": [
            ("plant green testsecret", "plant", "growth"),
            ("bird wing testsecret", "bird", "flight"),
        ],
    }
    return [
        {
            "id": f"{split}-{index}", "case_id": f"{split}-case-{index}",
            "source_id": f"synthetic-{split}", "text": text,
            "labels": {"topic": topic, "process": process},
            "reviewed": True, "reviewer": "unit-test-fixture", "split": split,
        }
        for split, rows in texts.items() for index, (text, topic, process) in enumerate(rows)
    ]


def toy_config(**overrides):
    values = {
        "expert_id": "fixture", "heads": {"topic": ["plant", "bird"], "process": ["growth", "flight"]},
        "primary_head": "topic", "vocab_size": 80, "hidden_dim": 12, "representation_dim": 8,
        "epochs": 2, "batch_size": 4, "patience": 2, "min_score": 0.0, "dropout": 0.0,
    }
    values.update(overrides)
    return TrainingConfig.from_dict(values)


@pytest.fixture(scope="module")
def trained_bundle(tmp_path_factory):
    output = tmp_path_factory.mktemp("text-training") / "fixture"
    result = train_expert(toy_config(), toy_records(), output)
    return output, result


def test_review_and_consistent_labels_are_required():
    rows = toy_records()
    rows[0]["reviewed"] = False
    with pytest.raises(ValueError, match="reviewed"):
        validate_records(rows, toy_config().heads)
    rows = toy_records()
    rows[1]["text"] = rows[2]["text"]
    with pytest.raises(ValueError, match="contradictory"):
        validate_records(rows, toy_config().heads)


@pytest.mark.parametrize("shared", ["source_id", "case_id", "text"])
def test_explicit_split_leakage_is_rejected(shared):
    rows = toy_records()
    rows[4][shared] = rows[0][shared]
    # Row four is also a plant, so the duplicate remains a legitimate same-label
    # example; its placement across the split, rather than its label, is rejected.
    with pytest.raises(ValueError, match="crosses explicit"):
        split_records(validate_records(rows, toy_config().heads))


def test_training_only_features_and_all_heads_are_reported(trained_bundle):
    output, result = trained_bundle
    vocabulary = json.loads((output / "vocab.json").read_text())
    assert "validationsecret" not in vocabulary
    assert "testsecret" not in vocabulary
    split_file = json.loads((output / "splits.json").read_text())
    sources = [set(part["source_ids"]) for part in split_file["splits"].values()]
    assert all(not left.intersection(right) for i, left in enumerate(sources) for right in sources[i + 1:])
    assert set(result["metrics"]["splits"]["test"]["heads"]) == {"topic", "process"}
    assert result["metrics"]["splits"]["test"]["count"] == 2
    assert result["manifest"]["status"] == "reviewed_data"
    assert result["manifest"]["training"]["augmentation"] == "none"


def test_negation_tokens_are_not_discarded():
    vocabulary = build_vocabulary(["no lesions and not sick", "café healthy"])
    assert "no" in vocabulary and "not" in vocabulary and "no_lesions" in vocabulary
    assert "café" in vocabulary


def test_absent_or_legacy_checkpoint_never_makes_a_prediction(tmp_path):
    torch.save({"weight": torch.ones(2)}, tmp_path / "expert_pathology.pt")
    classifier = NeuralTextClassifier(tmp_path)
    result = classifier.predict("plant leaf")
    assert not classifier.is_trained and classifier.model is None
    assert result["abstained"] and result["predictions"] == {}


def test_real_bundle_load_and_zero_features_abstention(trained_bundle, monkeypatch):
    output, _ = trained_bundle
    classifier = NeuralTextClassifier(output, expected_expert_id="fixture")
    assert classifier.is_trained
    result = classifier.predict("plant leaf")
    assert not result["abstained"]
    assert set(result["predictions"]) == {"topic", "process"}
    assert result["score_type"] == "uncalibrated_softmax"

    def forbidden_forward(*args):
        raise AssertionError("Zero features must be rejected before inference")

    monkeypatch.setattr(classifier.model, "forward", forbidden_forward)
    rejected = classifier.predict("zzzzquuxxyz")
    assert rejected["abstained"] and rejected["predictions"] == {}
    assert "recognized features" in rejected["reason"]


@pytest.mark.parametrize("tamper", ["labels", "vocabulary", "nonfinite_weights"])
def test_mismatched_bundle_is_disabled(trained_bundle, tmp_path, tamper):
    source, _ = trained_bundle
    bundle = tmp_path / "modified"
    shutil.copytree(source, bundle)
    manifest = json.loads((bundle / "manifest.json").read_text())
    if tamper == "labels":
        manifest["heads"]["topic"].reverse()
    elif tamper == "vocabulary":
        vocabulary = json.loads((bundle / "vocab.json").read_text())
        keys = list(vocabulary)[:2]
        vocabulary[keys[0]], vocabulary[keys[1]] = vocabulary[keys[1]], vocabulary[keys[0]]
        (bundle / "vocab.json").write_text(json.dumps(vocabulary))
        # Even if the outer file hash is updated, the checkpoint binds its vocab.
        manifest["artifacts"]["vocab.json"] = file_hash(bundle / "vocab.json")
    else:
        checkpoint = torch.load(bundle / "model.pt", weights_only=True)
        next(iter(checkpoint["state_dict"].values())).flatten()[0] = float("nan")
        torch.save(checkpoint, bundle / "model.pt")
        manifest["artifacts"]["model.pt"] = file_hash(bundle / "model.pt")
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    classifier = NeuralTextClassifier(bundle)
    assert not classifier.available and classifier.model is None
    assert classifier.predict("plant leaf")["predictions"] == {}


def test_experimental_bundle_requires_explicit_opt_in(trained_bundle, tmp_path):
    source, _ = trained_bundle
    bundle = tmp_path / "demo"
    shutil.copytree(source, bundle)
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["status"] = "experimental"
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    assert not NeuralTextClassifier(bundle).available
    opted_in = NeuralTextClassifier(bundle, allow_experimental=True)
    assert opted_in.available
    assert opted_in.predict("plant leaf")["experimental"] is True


def test_best_checkpoint_is_saved_instead_of_final_epoch(tmp_path, monkeypatch):
    import tiny_experts.neural.training as training
    original = training.evaluate
    snapshots = []

    def scripted_validation(model, features, labels, config):
        report = original(model, features, labels, config)
        if len(snapshots) < 2:
            snapshots.append({key: value.clone() for key, value in model.state_dict().items()})
            report["weighted_cross_entropy"] = 0.1 if len(snapshots) == 1 else 0.9
        return report

    monkeypatch.setattr(training, "evaluate", scripted_validation)
    result = train_expert(toy_config(epochs=4, patience=1), toy_records(), tmp_path / "best")
    checkpoint = torch.load(tmp_path / "best" / "model.pt", weights_only=True)
    assert result["metrics"]["best_epoch"] == 1
    assert result["metrics"]["epochs_run"] == 2
    assert all(torch.equal(checkpoint["state_dict"][key], value) for key, value in snapshots[0].items())
    assert any(not torch.equal(snapshots[0][key], value) for key, value in snapshots[1].items())


def test_router_uses_bundle_dimension_and_never_forces_a_choice(tmp_path):
    from tiny_experts.neural.neural_router import NeuralMoERouter
    rows = toy_records()
    for row in rows:
        row["labels"] = {"expert": "botany" if row["labels"]["topic"] == "plant" else "ornithology"}
    config = toy_config(expert_id="router", heads={"expert": ["botany", "ornithology"]}, primary_head="expert", epochs=1)
    train_expert(config, rows, tmp_path / "router")
    router = NeuralMoERouter(bundle_dir=tmp_path / "router")
    assert router.is_trained
    assert router.vocab_size < 500  # No hard-coded 400/500 feature mismatch.
    assert router.predict_active_experts("plant leaf", threshold=1.0) == []
    assert router.predict_active_experts("zzzzquuxxyz") == []
    assert router.predict_active_experts("plant leaf")
    assert not NeuralMoERouter(bundle_dir=tmp_path / "missing").is_trained


def test_legacy_pathology_export_is_unreviewed_demo_only():
    from train_pathology_expert import legacy_records
    rows = legacy_records()
    assert len(rows) == 165
    assert all(row["reviewed"] is False for row in rows)
    assert len({row["source_id"] for row in rows}) == 1


def test_leaf_batchnorm_tracks_statistics_and_evaluation_is_deterministic():
    from tiny_experts.neural.leaf_training import LeafVisionNet
    torch.set_num_threads(1)
    model = LeafVisionNet()
    model.train()
    images = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        model(images)
    layers = [module for module in model.modules() if isinstance(module, torch.nn.BatchNorm2d)]
    assert layers and all(layer.track_running_stats for layer in layers)
    assert all(int(layer.num_batches_tracked.item()) == 1 for layer in layers)
    assert any(torch.count_nonzero(layer.running_mean).item() for layer in layers)
    model.eval()
    with torch.no_grad():
        assert torch.equal(model(images), model(images))


def test_leaf_duplicate_images_cannot_cross_source_splits(tmp_path):
    from PIL import Image
    from tiny_experts.neural.leaf_training import load_image_records
    rows = []
    for index, split in enumerate(("train", "validation", "test")):
        # The first two files have different names, but identical contents.
        image = Image.new("RGB", (12, 12), (10, 30, 10 if index < 2 else 80))
        image.save(tmp_path / f"{index}.png")
        rows.append({
            "id": f"photo-{index}", "case_id": f"case-{index}", "source_id": f"source-{index}",
            "path": f"{index}.png", "label": "healthy", "reviewed": True,
            "reviewer": "unit-test-fixture", "synthetic": False, "split": split,
        })
    manifest = tmp_path / "images.jsonl"
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    records = load_image_records(tmp_path, manifest)
    with pytest.raises(ValueError, match="crosses explicit"):
        split_records(records)


def test_leaf_validation_transform_has_no_random_augmentation(tmp_path):
    from PIL import Image
    from tiny_experts.neural.leaf_training import ImageRecords
    from torchvision import transforms
    image = Image.new("RGB", (16, 16), (30, 100, 50))
    image.paste((200, 0, 0), (0, 0, 8, 16))
    image.save(tmp_path / "leaf.png")
    row = {"path": "leaf.png", "labels": {"condition": "healthy"}}
    training = ImageRecords([row], tmp_path, training=True)
    validation = ImageRecords([row], tmp_path, training=False)
    assert training.transform is not validation.transform
    assert any(isinstance(step, transforms.RandomHorizontalFlip) for step in training.transform.transforms)
    assert not any(isinstance(step, transforms.RandomHorizontalFlip) for step in validation.transform.transforms)
    assert torch.equal(validation[0][0], validation[0][0])
