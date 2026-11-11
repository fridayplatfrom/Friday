"""Offline book/sources integration; no network, no LLM."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tiny_experts.pipeline.book_workflow import BookWorkflow
from tiny_experts.pipeline.corpus_validation import audit_book_corpus
from tiny_experts.pipeline.source_fetch import validate_public_url

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "peter_rabbit.txt"


class BookWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workflow = BookWorkflow(self.temporary.name)

    def tearDown(self):
        self.workflow.close()
        self.temporary.cleanup()

    def import_story(self):
        return self.workflow.import_file(FIXTURE, title="The Tale of Peter Rabbit",
                                         shelf="literature",
                                         metadata={"authors": ["Beatrix Potter"],
                                                   "license": "Public domain in U.S.; check local rights",
                                                   "source_url": "https://www.gutenberg.org/ebooks/14838"})

    def test_import_search_and_reload(self):
        row = self.import_story()
        self.assertEqual(row["status"], "success")
        self.assertEqual(row["total_words"], 966)
        self.assertEqual(row["chunks_count"], 7)
        result = self.workflow.query(row["document_id"], "What did Peter lose among the cabbages?")
        self.assertEqual(result["status"], "retrieved")
        self.assertIsNone(result["answer"])
        passage = next(p for p in result["passages"] if "one of his shoes among the cabbages" in p["text"])
        evidence = self.workflow.evidence(passage["passage_id"], "one of his shoes among the cabbages")
        self.assertTrue(evidence["structural_support"])
        self.assertEqual(evidence["semantic_support"], "not_evaluated")
        self.workflow.close()
        self.workflow = BookWorkflow(self.temporary.name)
        self.assertEqual(self.workflow.query(row["document_id"], "shoes cabbages")["status"], "retrieved")

    def test_unknown_and_stale_document(self):
        row = self.import_story()
        document_id = row["document_id"]
        self.assertEqual(self.workflow.query("no-such-book", "shoes")["status"], "document_not_found")
        self.assertEqual(self.workflow.query(document_id, "antidisestablishmentarianism")["status"], "no_matching_evidence")
        old = self.workflow.query(document_id, "cabbages shoes")["passages"][0]["passage_id"]
        revised = self.workflow.importer.ingest_text("Peter stayed at home and ate apples.",
                                                     "The Tale of Peter Rabbit", shelf="literature",
                                                     document_id=document_id, metadata={"license": "test"})
        self.assertEqual(revised["status"], "success")
        with self.assertRaises(ValueError):
            self.workflow.evidence(old)
        self.assertEqual(self.workflow.query(document_id, "cabbages")["status"], "no_matching_evidence")
        self.assertEqual(self.workflow.query(document_id, "apples")["status"], "retrieved")

    def test_training_annotation_needs_review(self):
        row = self.import_story()
        passage = self.workflow.query(row["document_id"], "shoes cabbages")["passages"][0]
        annotation = self.workflow.annotation(example_id="ex1", case_id="case1",
            text="Where was Peter's shoe?", labels={"topic": "objects"},
            passage_id=passage["passage_id"], quote="one of his shoes among the cabbages")
        self.assertFalse(annotation["reviewed"])
        sources = self.workflow.export_sources()
        report = audit_book_corpus([annotation], sources, self.temporary.name,
                                    require_review=False, current_sources=sources)
        self.assertTrue(report["ready_for_training"], report["errors"])
        report = audit_book_corpus([annotation], sources, self.temporary.name,
                                    require_review=True, current_sources=sources)
        self.assertFalse(report["ready_for_training"])
        with self.assertRaises(ValueError):
            self.workflow.evidence(passage["passage_id"], "Quote not present")

    def test_failed_online_download_does_not_index(self):
        receipt = {"status": "failed", "error_code": "network_unavailable"}
        with patch("tiny_experts.pipeline.book_workflow.fetch_public_text",
                   return_value={"status": "failed", "text": None, "receipt": receipt}):
            result = self.workflow.import_url("https://www.gutenberg.org/cache/epub/14838/pg14838.txt",
                                              title="Peter Rabbit", license_note="Public domain, U.S.")
        self.assertEqual(result["status"], "source_failed")
        self.assertFalse(result["indexed"])
        self.assertFalse(self.workflow.engine.index)

    def test_mocked_online_success_remains_unreviewed(self):
        receipt = {"status": "downloaded", "content_type": "text/plain"}
        with patch("tiny_experts.pipeline.book_workflow.fetch_public_text",
                   return_value={"status": "downloaded",
                                 "text": FIXTURE.read_text(encoding="utf-8"), "receipt": receipt}):
            result = self.workflow.import_url("https://www.gutenberg.org/cache/epub/14838/pg14838.txt",
                                              title="Peter Rabbit", license_note="Public domain, U.S.")
        self.assertTrue(result["indexed"])
        self.assertEqual(result["review_status"], "unreviewed")

    def test_invalid_source_addresses_rejected(self):
        for url in ("http://www.gutenberg.org/a", "https://localhost/a",
                    "https://127.0.0.1/a", "https://www.gutenberg.org:4444/a",
                    "https://www.gutenberg.org@localhost/a"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_public_url(url)


if __name__ == "__main__":
    unittest.main()
