"""Train a small subject classifier from reviewed JSONL; no generative LLM."""

import argparse
import json
from pathlib import Path


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="JSON configuration with expert_id, heads, and primary_head")
    parser.add_argument("--data", required=True, type=Path, help="Reviewed labeled JSONL with source_id and case_id")
    parser.add_argument("--output", required=True, type=Path, help="Directory for a complete model bundle")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--allow-unreviewed-demo", action="store_true", help="Mark the bundle experimental; it stays disabled by default")
    parser.add_argument("--split-by", choices=("source", "case"), default="source", help="Source+case separation by default; case-only requires demo mode")
    parser.add_argument("--overwrite", action="store_true", help="Intentionally replace an existing bundle")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        from tiny_experts.neural.training import TrainingConfig, train_expert
        from tiny_experts.neural.training_data import read_jsonl
        values = json.loads(args.config.read_text(encoding="utf-8"))
        for name in ("epochs", "batch_size", "learning_rate", "seed", "threads"):
            override = getattr(args, name)
            if override is not None:
                values[name] = override
        config = TrainingConfig.from_dict(values)
        records = read_jsonl(args.data, config.heads, demo=args.allow_unreviewed_demo)
        train_expert(
            config, records, args.output, demo=args.allow_unreviewed_demo,
            split_by=args.split_by, overwrite=args.overwrite,
        )
    except (ValueError, OSError, ImportError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
