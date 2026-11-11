"""Reviewed JSONL input and source/case-separated splits, without ML dependencies."""

from collections import defaultdict
import json
from pathlib import Path
import random

from .text_features import canonical_hash


SPLITS = ("train", "validation", "test")


def validate_records(records: list[dict], heads: dict[str, list[str]], *, demo: bool = False) -> list[dict]:
    if not records:
        raise ValueError("Dataset is empty")
    seen_ids = set()
    text_labels = {}
    cleaned = []
    for index, row in enumerate(records, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Record {index}: expected a JSON object")
        for field in ("id", "case_id", "source_id", "text"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Record {index}: nonempty {field!r} is required")
        if row["id"] in seen_ids:
            raise ValueError(f"Duplicate example id: {row['id']}")
        seen_ids.add(row["id"])
        labels = row.get("labels")
        if not isinstance(labels, dict) or set(labels) != set(heads):
            raise ValueError(f"{row['id']}: labels must contain exactly {sorted(heads)}")
        for head, label in labels.items():
            if label not in heads[head]:
                raise ValueError(f"{row['id']}: unknown {head} label {label!r}")
        normalized_text = " ".join(row["text"].casefold().split())
        if normalized_text in text_labels and text_labels[normalized_text] != labels:
            raise ValueError(f"{row['id']}: identical text has contradictory target labels")
        text_labels[normalized_text] = labels
        if not demo and (
            row.get("reviewed") is not True
            or not isinstance(row.get("reviewer"), str)
            or not row["reviewer"].strip()
        ):
            raise ValueError(f"{row['id']}: reviewed=true and a reviewer are required; use demo mode only for experiments")
        split = row.get("split")
        if split == "val":
            split = "validation"
        if split is not None and split not in SPLITS:
            raise ValueError(f"{row['id']}: split must be train, validation, or test")
        item = dict(row)
        item["split"] = split
        cleaned.append(item)
    if any(row["split"] is not None for row in cleaned) and not all(row["split"] is not None for row in cleaned):
        raise ValueError("Provide a split for every example or for none of them")
    return cleaned


def read_jsonl(path, heads: dict[str, list[str]], *, demo: bool = False) -> list[dict]:
    records = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from error
    return validate_records(records, heads, demo=demo)


def connected_groups(records: list[dict], *, split_by: str = "source") -> list[list[dict]]:
    """Keep related sources, cases and exact normalized duplicates together.

    Source separation is the default. Case-only separation is available for
    explicit demo runs; it must never be reported as unseen-source evaluation.
    """
    if split_by not in ("source", "case"):
        raise ValueError("split_by must be source or case")
    parents = list(range(len(records)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left, right):
        parents[find(left)] = find(right)

    owners = {}
    for index, row in enumerate(records):
        keys = [
            ("case", row["case_id"]),
            ("text", " ".join(row["text"].casefold().split())),
        ]
        if split_by == "source":
            keys.append(("source", row["source_id"]))
            for field in ("source_family_id", "source_revision"):
                value = row.get(field)
                if value is not None:
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"{field} must be a nonempty string when supplied")
                    keys.append((field, value))
        for key in keys:
            if key in owners:
                union(index, owners[key])
            else:
                owners[key] = index
    groups = defaultdict(list)
    for index, row in enumerate(records):
        groups[find(index)].append(row)
    return [sorted(group, key=lambda row: row["id"]) for group in groups.values()]


def _label_pairs(rows):
    return {(head, value) for row in rows for head, value in row["labels"].items()}


def split_records(
    records: list[dict], *, seed: int = 42, validation_fraction: float = 0.15,
    test_fraction: float = 0.15, split_by: str = "source", demo: bool = False,
) -> dict[str, list[dict]]:
    if split_by == "case" and not demo:
        raise ValueError("Case-only splitting is experimental; reviewed training requires source separation")
    if not (0 < validation_fraction < 1 and 0 < test_fraction < 1 and validation_fraction + test_fraction < 1):
        raise ValueError("Validation and test fractions must be positive and sum to less than one")
    groups = connected_groups(records, split_by=split_by)
    result = {name: [] for name in SPLITS}
    if records[0].get("split") is not None:
        for group in groups:
            assigned = {row["split"] for row in group}
            if len(assigned) != 1:
                raise ValueError("Source, case, or duplicate text crosses explicit dataset splits")
            result[assigned.pop()].extend(group)
    else:
        if len(groups) < 3:
            raise ValueError("Need at least three independent source/case groups for train, validation, and test")
        n_validation = max(1, round(len(groups) * validation_fraction))
        n_test = max(1, round(len(groups) * test_fraction))
        n_train = len(groups) - n_validation - n_test
        if n_train < 1:
            raise ValueError("Split fractions leave no training groups")
        observed = _label_pairs(records)
        # Group shuffling never uses validation/test text to build features.
        # Retrying only ensures each observed target exists in the training set.
        for attempt in range(256):
            order = list(groups)
            random.Random(seed + attempt).shuffle(order)
            candidate = {
                "train": [row for group in order[:n_train] for row in group],
                "validation": [row for group in order[n_train:n_train + n_validation] for row in group],
                "test": [row for group in order[n_train + n_validation:] for row in group],
            }
            if _label_pairs(candidate["train"]) == observed:
                result = candidate
                break
        else:
            raise ValueError("Cannot retain all observed labels in training; add independent examples/sources or supply valid explicit splits")
    if any(not result[name] for name in SPLITS):
        raise ValueError("Train, validation, and test must each contain examples")
    missing = _label_pairs(records) - _label_pairs(result["train"])
    if missing:
        raise ValueError(f"Labels occur outside training only: {sorted(missing)}")
    return {name: sorted(rows, key=lambda row: row["id"]) for name, rows in result.items()}


def split_manifest(splits: dict[str, list[dict]], *, split_by: str) -> dict:
    result = {"split_by": split_by, "source_separated": split_by == "source", "splits": {}}
    for name, rows in splits.items():
        details = {
            "example_ids": [row["id"] for row in rows],
            "case_ids": sorted({row["case_id"] for row in rows}),
            "source_ids": sorted({row["source_id"] for row in rows}),
            "count": len(rows),
        }
        details["sha256"] = canonical_hash(details)
        result["splits"][name] = details
    return result
