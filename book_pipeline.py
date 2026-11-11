"""Local book/source ingestion and evidence lookup without any generative LLM."""
import argparse
import json
from tiny_experts.pipeline.book_workflow import BookWorkflow
from tiny_experts.pipeline.source_fetch import check_sources

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", required=True)
    sub = p.add_subparsers(dest="command", required=True)
    local = sub.add_parser("import-file")
    local.add_argument("path")
    local.add_argument("--title", required=True)
    local.add_argument("--shelf", default="literature")
    local.add_argument("--source-url")
    local.add_argument("--license-note", required=True)
    remote = sub.add_parser("import-url")
    remote.add_argument("url")
    remote.add_argument("--title", required=True)
    remote.add_argument("--shelf", default="literature")
    remote.add_argument("--license-note", required=True)
    q = sub.add_parser("query")
    q.add_argument("document_id")
    q.add_argument("question")
    q.add_argument("--top-k", type=int, default=3)
    sub.add_parser("sources")
    sub.add_parser("check-sources")
    args = p.parse_args(argv)
    workflow = None
    try:
        if args.command == "check-sources":
            result = check_sources({
                "gutenberg": "https://www.gutenberg.org/cache/epub/14838/pg14838.txt",
                "wikipedia": "https://en.wikipedia.org/api/rest_v1/page/summary/Photosynthesis",
                "pubchem": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/water/property/MolecularFormula/JSON",
            })
            code = 0 if all(v["status"] == "downloaded" for v in result.values()) else 1
        else:
            workflow = BookWorkflow(args.data_dir)
            if args.command == "import-file":
                result = workflow.import_file(args.path, title=args.title, shelf=args.shelf,
                    metadata={"source_url": args.source_url, "license": args.license_note})
            elif args.command == "import-url":
                result = workflow.import_url(args.url, title=args.title, shelf=args.shelf,
                                             license_note=args.license_note)
            elif args.command == "query":
                result = workflow.query(args.document_id, args.question, args.top_k)
            else:
                result = workflow.export_sources()
            code = 1 if isinstance(result, dict) and result.get("status") in {
                "source_failed", "unsupported_book_format", "document_not_found"} else 0
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return code
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return 1
    finally:
        if workflow is not None:
            workflow.close()

if __name__ == "__main__":
    raise SystemExit(main())
