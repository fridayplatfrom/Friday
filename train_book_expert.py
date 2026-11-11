"""Train categorical book expert with immutable-source and review preflight."""
import argparse
import json
from pathlib import Path
from tiny_experts.pipeline.book_workflow import BookWorkflow
from tiny_experts.pipeline.corpus_validation import audit_book_corpus

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("data-dir", "data", "sources", "config", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--demo", action="store_true",
                        help="Unreviewed execution test; model stays experimental and disabled by default")
    args = parser.parse_args(argv)
    workflow = None
    try:
        records = [json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        workflow = BookWorkflow(args.data_dir)
        audit = audit_book_corpus(records, sources, args.data_dir, require_review=not args.demo,
                                  current_sources=workflow.export_sources())
        print(json.dumps({"preflight": audit}, indent=2, ensure_ascii=False))
        if not audit["ready_for_training"]:
            return 1
        from tiny_experts.neural.training import TrainingConfig, train_expert
        for row in records:
            row["source_family_id"] = sources[row["source_id"]]["source_family_id"]
        config = TrainingConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))
        train_expert(config, records, args.output, demo=args.demo,
                     split_by="case" if args.demo else "source")
        return 0
    except (OSError, ValueError, ImportError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    finally:
        if workflow is not None:
            workflow.close()

if __name__ == "__main__":
    raise SystemExit(main())
