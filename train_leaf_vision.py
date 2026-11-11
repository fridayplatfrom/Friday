"""Train a leaf classifier from reviewed images, or run an explicit demo."""

import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "tiny_experts" / "data" / "images" / "leaf_benchmark")
    parser.add_argument("--manifest", type=Path, help="Reviewed image JSONL with path, label, source_id, case_id, reviewer, and synthetic=false")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--demo", action="store_true", help="Train an experimental model from unreviewed/synthetic fixtures")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        from tiny_experts.neural.leaf_training import train_leaf_vision
        return train_leaf_vision(
            args.epochs, args.batch_size, args.learning_rate, data_dir=args.data_dir,
            manifest_path=args.manifest, output_dir=args.output, demo=args.demo,
            seed=args.seed, patience=args.patience, threshold=args.threshold,
            threads=args.threads, overwrite=args.overwrite,
        )
    except (ValueError, OSError, ImportError) as error:
        parser.error(str(error))


def __getattr__(name):
    # Keep import compatibility while allowing --help without loading PyTorch.
    if name in {"LeafVisionNet", "train_leaf_vision", "DATASET_DIR"}:
        from tiny_experts.neural import leaf_training
        return getattr(leaf_training, name)
    raise AttributeError(name)


if __name__ == "__main__":
    main()
