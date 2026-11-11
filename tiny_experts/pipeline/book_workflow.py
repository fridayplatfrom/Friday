"""Book -> indexed passages -> evidence -> unreviewed annotations.

Answers are not generated; importing a source never trains a neural model.
"""
import hashlib
from pathlib import Path

from .book_engine import BookEngine
from .ingestion import LiteratureIngestionPipeline
from .source_fetch import fetch_public_text


class BookWorkflow:
    def __init__(self, data_dir=None):
        self.engine = BookEngine(data_dir=data_dir, include_demo_seeds=False)
        self.importer = LiteratureIngestionPipeline(book_engine=self.engine)

    def close(self):
        self.engine.close()

    def import_file(self, path, *, title, shelf="literature", metadata=None, document_id=None):
        metadata = {**(metadata or {}), "ingestion_method": "local_file"}
        return self.importer.ingest_file(path, shelf, title, metadata, document_id)

    def import_url(self, url, *, title, shelf="literature", license_note, authors=None):
        if not isinstance(license_note, str) or not license_note.strip():
            raise ValueError("Record a real license/permission note; do not infer rights from accessibility")
        self.engine.validate_shelf(shelf)
        fetched = fetch_public_text(url)
        if fetched["status"] != "downloaded":
            return {"status": "source_failed", "indexed": False, "fetch_receipt": fetched["receipt"]}
        if fetched["receipt"]["content_type"] not in {"text/plain", "text/markdown"}:
            return {"status": "unsupported_book_format", "indexed": False, "fetch_receipt": fetched["receipt"]}
        document_id = "url_" + hashlib.sha256(url.encode()).hexdigest()
        metadata = {"authors": list(authors or []), "source_url": url, "license": license_note,
                    "ingestion_method": "https_download", "fetch_receipt": fetched["receipt"]}
        result = self.importer.ingest_text(fetched["text"], title, shelf, metadata, document_id)
        return {**result, "indexed": result["status"] == "success", "fetch_receipt": fetched["receipt"]}

    def query(self, document_id, question, top_k=3):
        return self.engine.lookup_document(document_id, question, top_k)

    def evidence(self, passage_id, quote=None):
        """Check source snapshot hash and offsets, not semantic entailment."""
        passage = self.engine.get_passage(passage_id)
        if passage is None:
            raise ValueError("Unknown or stale passage ID")
        metadata = passage.get("source_metadata") or {}
        relative = metadata.get("raw_text_relative_path")
        expected_hash = metadata.get("raw_text_sha256")
        if not relative or expected_hash != passage.get("content_hash"):
            raise ValueError("Passage has no matching immutable extracted-text snapshot")
        root = Path(self.engine.data_dir).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Missing or invalid extracted-text snapshot path")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError("Extracted-text snapshot hash mismatch")
        text = raw.decode("utf-8")
        start, end = passage.get("text_char_start"), passage.get("text_char_end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("Invalid passage offsets")
        if text[start:end] != passage["text"]:
            raise ValueError("Passage does not match its stored text offsets")
        if quote is not None and (not isinstance(quote, str) or not quote or quote not in passage["text"]):
            raise ValueError("Evidence quote does not occur in this passage")
        return {"source_id": passage["document_id"], "source_revision": expected_hash,
                "passage_id": passage_id, "quote": quote,
                "text_char_start": start, "text_char_end": end,
                "structural_support": True, "semantic_support": "not_evaluated"}

    def annotation(self, *, example_id, case_id, text, labels, passage_id, quote):
        for name, value in (("id", example_id), ("case_id", case_id), ("text", text)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(labels, dict) or not labels or not all(isinstance(k, str) and k and isinstance(v, str) and v for k, v in labels.items()):
            raise ValueError("Nonempty categorical labels are required")
        evidence = self.evidence(passage_id, quote)
        return {"id": example_id, "case_id": case_id, "source_id": evidence["source_id"],
                "source_revision": evidence["source_revision"], "text": text, "labels": labels,
                "evidence": [evidence], "reviewed": False, "reviewer": None}

    def export_sources(self):
        sources = {}
        for passage in self.engine.index:
            metadata = passage.get("source_metadata") or {}
            relative = metadata.get("raw_text_relative_path")
            if not relative:
                continue
            sid = passage["document_id"]
            if sid not in sources:
                sources[sid] = {
                    "title": passage["source"].rsplit(" (Section ", 1)[0],
                    "sha256": passage["content_hash"], "text_path": relative,
                    "license": metadata.get("license"), "source_url": metadata.get("source_url"),
                    "review_status": "unreviewed", "reviewer": None,
                    "source_family_id": metadata.get("source_family_id") or sid,
                    "passages": [],
                }
            sources[sid]["passages"].append({"passage_id": passage["passage_id"], "text": passage["text"],
                                            "start": passage.get("text_char_start"), "end": passage.get("text_char_end")})
        return sources
