"""Index supplied document text with explicit source metadata; no model is trained."""

import argparse
import sys

from tiny_experts.pipeline.book_engine import BookEngine
from tiny_experts.pipeline.ingestion import LiteratureIngestionPipeline


def main():
    parser = argparse.ArgumentParser(description="Index local literature as unreviewed source passages.")
    parser.add_argument("file_path", nargs="?", help="Local EPUB, DOCX, PDF, TXT, Markdown or JSON document")
    parser.add_argument("--shelf", "-s", choices=BookEngine.DEFAULT_SHELVES, help="Target shelf; required if automatic classification is unknown or ambiguous")
    parser.add_argument("--title", "-t", help="Document title, if known")
    parser.add_argument("--text", help="Import raw text instead of a file")
    parser.add_argument("--data-dir", help="Writable document directory; defaults to TINY_EXPERT_STATE_DIR/books")
    parser.add_argument("--document-id", help="Stable ID for replacing a document, including across title/shelf changes")
    parser.add_argument("--book-id", help="Known bibliographic catalog ID")
    parser.add_argument("--author", action="append", default=[], help="Known author; may be repeated")
    parser.add_argument("--year", type=int, help="Known publication year")
    parser.add_argument("--publisher", help="Known publisher")
    parser.add_argument("--edition", help="Known edition")
    parser.add_argument("--source-url", help="Actual source URL, if available")
    parser.add_argument("--license", help="Document license or permission information, if available")
    parser.add_argument("--pages", help="Actual page range covered by the supplied text, if known")
    args = parser.parse_args()
    if bool(args.file_path) == (args.text is not None):
        parser.error("Provide exactly one file_path or --text.")
    metadata = {
        "authors": args.author, "year": args.year, "publisher": args.publisher,
        "edition": args.edition, "source_url": args.source_url, "license": args.license,
        "book_id": args.book_id, "page_range": args.pages,
    }
    engine = None
    try:
        engine = BookEngine(data_dir=args.data_dir)
        pipeline = LiteratureIngestionPipeline(book_engine=engine)
        if args.text is not None:
            result = pipeline.ingest_text(args.text, args.title or "Untitled CLI excerpt", args.shelf,
                                          metadata=metadata, document_id=args.document_id)
        else:
            result = pipeline.ingest_file(args.file_path, args.shelf, args.title,
                                          metadata=metadata, document_id=args.document_id)
    except (OSError, ValueError, ImportError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.close()
    if result.get("status") != "success":
        print(f"[WARNING] {result.get('message', 'No passages imported.')}")
        return 1
    print(f"[OK] Indexed {result['chunks_count']} passages from {result['source_title']!r}.")
    print(f"  Document ID: {result['document_id']}")
    print(f"  Shelf: {result['shelf']}")
    print(f"  Source words: {result['total_words']}")
    print(f"  Stored revision: {result['file_saved']}")
    print("  Review status: unreviewed; source accuracy has not been verified.")
    print("The text is available for retrieval. Model parameters have not changed.")
    for warning in result.get("warnings", []):
        print(f"[WARNING] {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
