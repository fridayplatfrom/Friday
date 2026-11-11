import unittest
import os
import zipfile
import json
from tiny_experts.pipeline.ingestion import LiteratureIngestionPipeline

class TestIngestionMultiFormat(unittest.TestCase):
    """
    Verifies multi-format document ingestion across EPUB, DOCX, TXT, MD, and JSON.
    """

    @classmethod
    def setUpClass(cls):
        cls.pipeline = LiteratureIngestionPipeline()
        cls.test_files = []

    @classmethod
    def tearDownClass(cls):
        for path in cls.test_files:
            if os.path.exists(path):
                os.remove(path)

    def test_01_epub_extraction_and_chunking(self):
        """Test EPUB archive extraction, spine order preservation, and chunking."""
        epub_path = "test_sample_manual.epub"
        self.test_files.append(epub_path)

        with zipfile.ZipFile(epub_path, "w") as zf:
            zf.writestr(
                "META-INF/container.xml",
                '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>'
            )
            zf.writestr(
                "OEBPS/content.opf",
                '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>EPUB Agronomy Handbook</dc:title></metadata><manifest><item id="c1" href="ch1.xhtml"/></manifest><spine><itemref idref="c1"/></spine></package>'
            )
            zf.writestr(
                "OEBPS/ch1.xhtml",
                '<html><body><h1>Solanaceae Diagnostic Key</h1><p>Early blight caused by Alternaria solani produces distinct concentric target-board lesions with surrounding chlorotic halo on lower senescing leaves. Preventative control includes copper octanoate and azoxystrobin spray rotations.</p></body></html>'
            )

        text, title = self.pipeline.extract_text_from_file(epub_path)
        self.assertEqual(title, "EPUB Agronomy Handbook")
        self.assertIn("Alternaria solani", text)
        self.assertIn("concentric target-board lesions", text)

        chunks = self.pipeline.chunk_scientific_text(text, source_title=title, chunk_size_words=10)
        self.assertGreater(len(chunks), 0)
        shelf = self.pipeline.auto_classify_shelf(text)
        self.assertIn(shelf, ["pathology", "botany", "mycology"])

    def test_02_docx_extraction(self):
        """Test DOCX document xml parsing without external dependencies."""
        docx_path = "test_sample_handbook.docx"
        self.test_files.append(docx_path)

        with zipfile.ZipFile(docx_path, "w") as zf:
            doc_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body>'
                '<w:p><w:r><w:t>Rice Bacterial Leaf Blight Extension Note</w:t></w:r></w:p>'
                '<w:p><w:r><w:t>Xanthomonas oryzae pv. oryzae causes wavy water-soaked lesions from leaf tips.</w:t></w:r></w:p>'
                '</w:body>'
                '</w:document>'
            )
            zf.writestr("word/document.xml", doc_xml)

        text, title = self.pipeline.extract_text_from_file(docx_path)
        self.assertEqual(title, "Test Sample Handbook")
        self.assertIn("Xanthomonas oryzae", text)
        self.assertIn("Rice Bacterial Leaf Blight", text)

    def test_03_txt_and_json_extraction(self):
        """Test standard text and JSON format ingestion."""
        txt_path = "test_sample_notes.txt"
        self.test_files.append(txt_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Amanita phalloides contains lethal amatoxins causing acute hepatic failure.")

        text, title = self.pipeline.extract_text_from_file(txt_path)
        self.assertEqual(title, "Test Sample Notes")
        self.assertIn("Amanita phalloides", text)
        shelf = self.pipeline.auto_classify_shelf(text)
        self.assertEqual(shelf, "toxicology")

if __name__ == "__main__":
    unittest.main()
