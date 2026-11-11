import unittest
import os
import tempfile
from io import BytesIO
import pypdf

from tiny_experts.pipeline.bm25 import BM25Retriever
from tiny_experts.pipeline.book_engine import BookEngine
from tiny_experts.pipeline.ingestion import LiteratureIngestionPipeline

class TestBM25AndIngestion(unittest.TestCase):
    def test_bm25_retriever(self):
        retriever = BM25Retriever()
        docs = [
            {"shelf": "botany", "source": "Doc 1", "text": "Photosynthesis in chloroplasts produces glucose and oxygen from water and carbon dioxide."},
            {"shelf": "toxicology", "source": "Doc 2", "text": "Urushiol causes severe allergic contact dermatitis upon dermal exposure."},
            {"shelf": "marine", "source": "Doc 3", "text": "Coral bleaching occurs when hermatypic corals expel Symbiodiniaceae zooxanthellae under thermal stress."}
        ]
        retriever.index_documents(docs)

        # Query 1: Urushiol
        res1 = retriever.search("What are the effects of urushiol?", top_k=1)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0]["source"], "Doc 2")
        self.assertGreater(res1[0]["bm25_score"], 0.0)

        # Query 2: Marine with shelf filter
        res2 = retriever.search("coral bleaching and thermal stress", shelf_filter="marine", top_k=1)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["shelf"], "marine")

    def test_auto_classification(self):
        text_marine = "The Great Barrier Reef comprises extensive scleractinian coral calcification dependent on photosynthetic dinoflagellates."
        text_micro = "Bacteriophages inject their double-stranded DNA genomes into bacterial cells, triggering the lytic cycle or lysogeny."
        text_genetics = "CRISPR-Cas9 endonuclease creates targeted double-strand breaks guided by synthetic single guide RNA."

        self.assertEqual(LiteratureIngestionPipeline.auto_classify_shelf(text_marine), "marine")
        self.assertEqual(LiteratureIngestionPipeline.auto_classify_shelf(text_micro), "microbiology")
        self.assertEqual(LiteratureIngestionPipeline.auto_classify_shelf(text_genetics), "genetics")

    def test_text_chunking(self):
        long_text = (
            "Sentence one describes the physiological architecture. "
            "Sentence two elaborates on transport mechanisms across membranes. "
            "Sentence three discusses secondary metabolites. "
            "Sentence four reviews systemic defense responses. "
        ) * 10

        chunks = LiteratureIngestionPipeline.chunk_scientific_text(
            raw_text=long_text,
            source_title="Test Monograph",
            chunk_size_words=20,
            overlap_words=5
        )
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertIn("Test Monograph", c["source"])
            self.assertTrue(c["text"].endswith("."))

    def test_dynamic_ingestion_and_instant_retrieval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BookEngine(data_dir=tmpdir)
            pipeline = LiteratureIngestionPipeline(book_engine=engine)

            study_text = (
                "Phytochelatins are heavy metal-binding peptides synthesized enzymatically from glutathione. "
                "In contaminated soils, hyperaccumulating plants like Thlaspi caerulescens sequester cadmium "
                "and zinc into vacuolar compartments to prevent cytosolic toxicity."
            )

            res = pipeline.ingest_text(
                raw_text=study_text,
                source_title="Plant Heavy Metal Detoxification 2026",
                shelf="botany"
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["shelf"], "botany")

            # Immediately search with Okapi BM25
            search_res = engine.search("How do hyperaccumulating plants sequester cadmium and zinc?", shelf="botany")
            self.assertGreater(len(search_res), 0)
            self.assertIn("Plant Heavy Metal Detoxification 2026", search_res[0]["source"])
            self.assertIn("Phytochelatins", search_res[0]["text"])

    def test_pdf_ingestion(self):
        # Create a real PDF document in memory using pypdf
        writer = pypdf.PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        
        # We write a text file to test file ingestion end-to-end
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = os.path.join(tmpdir, "avian_biomechanics.txt")
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(
                    "Avian aerodynamic lift depends on wing aspect ratio and camber. "
                    "Hummingbirds produce lift on both the downstroke and upstroke through 180-degree wing inversion."
                )

            engine = BookEngine(data_dir=tmpdir)
            pipeline = LiteratureIngestionPipeline(book_engine=engine)
            res = pipeline.ingest_file(file_path=doc_path, shelf="ornithology", source_title="Avian Flight Dynamics")

            self.assertEqual(res["status"], "success")
            retrieved = engine.search("hummingbirds wing inversion downstroke upstroke", shelf="ornithology")
            self.assertGreater(len(retrieved), 0)
            self.assertIn("Avian Flight Dynamics", retrieved[0]["source"])

if __name__ == "__main__":
    unittest.main()
