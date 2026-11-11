"""Train an extractive passage reader on case-labelled book passages.

The model remains experimental, even when labels are reviewed; use an
independent evaluation and deliberate promotion step before normal inference.
"""
import argparse
import json
from pathlib import Path

from tiny_experts.pipeline.book_workflow import BookWorkflow
from tiny_experts.neural.passage_reader import train_reader


def prepare_rows(rows, workflow, *, demo=False, reviewed_sources=None):
    if not isinstance(rows, list) or not rows:
        raise ValueError("No training examples supplied")
    sources = workflow.export_sources()
    assembled = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each example must be an object")
        pid = row.get("passage_id")
        if not isinstance(pid, str) or not pid:
            raise ValueError("passage_id is required")
        passage = workflow.engine.get_passage(pid)
        if not passage or passage.get("document_id") != row.get("source_id"):
            raise ValueError("Missing or stale passage/source reference")
        sid = passage["document_id"]
        source = sources.get(sid)
        if not source or source.get("sha256") != row.get("source_revision"):
            raise ValueError("Source revision mismatch")
        answer = row.get("answer_text")
        if answer is None:
            workflow.evidence(pid)
        else:
            workflow.evidence(pid, quote=answer)
        review = (reviewed_sources or {}).get(sid)
        if not demo and (
            row.get("reviewed") is not True or
            not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip() or
            not isinstance(review, dict) or review.get("review_status") != "reviewed" or
            review.get("sha256") != source["sha256"] or
            not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip() or
            not isinstance(review.get("license"), str) or not review["license"].strip()
        ):
            raise ValueError("Independent annotation review and matching reviewed-source manifest are required")
        cleaned = {k: row[k] for k in ("id", "case_id", "source_id", "question", "split")}
        cleaned.update(answer_text=answer, answer_start=row.get("answer_start"),
                       source_family_id=(review or {}).get("source_family_id") or source.get("source_family_id"),
                       passage=passage["text"])
        assembled.append(cleaned)
    return assembled


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books-dir", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=90)
    parser.add_argument("--review-manifest", type=Path)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    book = None
    try:
        rows = [json.loads(x) for x in args.data.read_text(encoding="utf-8").splitlines() if x.strip()]
        book = BookWorkflow(args.books_dir)
        reviewed = json.loads(args.review_manifest.read_text(encoding="utf-8")) if args.review_manifest else None
        clean = prepare_rows(rows, book, demo=args.demo, reviewed_sources=reviewed)
        report = train_reader(clean, args.output, epochs=args.epochs, demo=args.demo)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as e:
        print(json.dumps({"status": "failed", "error": str(e)}))
        return 1
    finally:
        if book is not None:
            book.close()


if __name__ == "__main__":
    raise SystemExit(main())
