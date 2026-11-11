"""CLI plumbing shared by the legacy pathology and router entry points."""

import argparse
import json
from pathlib import Path


def subject_main(expert_id, config_path, legacy_records, argv=None):
    parser = argparse.ArgumentParser(
        description=f"Train the {expert_id} classifier. No --data means an unreviewed demo, disabled by default."
    )
    parser.add_argument("--data", type=Path, help="Reviewed JSONL; without it, use legacy demo fixtures")
    parser.add_argument("--config", type=Path, default=Path(config_path))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--export-demo", type=Path, help="Export unreviewed legacy examples and exit without training")
    parser.add_argument("--demo", action="store_true", help="Allow unreviewed input and mark the resulting model experimental")
    parser.add_argument("--split-by", choices=("source", "case"), default=None)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--threads", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.export_demo:
            if args.export_demo.exists() and not args.overwrite:
                raise ValueError("Export already exists; choose a new path or --overwrite")
            rows = legacy_records()
            args.export_demo.parent.mkdir(parents=True, exist_ok=True)
            args.export_demo.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8",
            )
            print(f"Exported {len(rows)} unreviewed demo records to {args.export_demo}. They are not gold training data.")
            return
        from .training import TrainingConfig, train_expert
        from .training_data import read_jsonl
        values = json.loads(args.config.read_text(encoding="utf-8"))
        for name in ("epochs", "batch_size", "learning_rate", "seed", "threads"):
            override = getattr(args, name)
            if override is not None:
                values[name] = override
        config = TrainingConfig.from_dict(values)
        if config.expert_id != expert_id:
            raise ValueError("Configuration belongs to a different expert")
        use_legacy = args.data is None
        demo = use_legacy or args.demo
        if use_legacy:
            records = legacy_records()
            print(f"Using {len(records)} unreviewed legacy demo queries. Results are execution checks, not quality claims.")
        else:
            records = read_jsonl(args.data, config.heads, demo=demo)
        models_dir = Path(__file__).resolve().parents[1] / "data" / "models"
        output = args.output or models_dir / (f"{expert_id}-demo" if demo else expert_id)
        return train_expert(
            config, records, output, demo=demo,
            split_by=args.split_by or ("case" if use_legacy else "source"),
            overwrite=args.overwrite,
        )
    except (ValueError, OSError, ImportError, json.JSONDecodeError) as error:
        parser.error(str(error))
