import os
import re
import json
import hashlib
import tempfile
from typing import List, Dict, Any, Optional

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

from .book_engine import BookEngine
from .book_catalog_engine import BookCatalogEngine

class LiteratureIngestionPipeline:
    """Extract and index local document text without training model parameters.

    The keyword shelf suggestion is a convenience, not a subject classifier with
    calibrated confidence. Supply a shelf when no unique suggestion is available.
    Imported content stays unreviewed until a separate review process approves it.
    """

    SHELF_KEYWORDS = {
        "botany": [
            "chloroplast", "stomata", "xylem", "phloem", "angiosperm", "gymnosperm",
            "flower", "leaf", "root", "stem", "petal", "botany", "plant", "germination",
            "transpiration", "mesophyll", "cambium", "photosynthesis"
        ],
        "genetics": [
            "dna", "rna", "mrna", "trna", "crispr", "chromosome", "intron", "exon",
            "allele", "transcription", "translation", "mutation", "gene", "genomics",
            "nucleotide", "promoter", "epigenetics", "spliceosome"
        ],
        "cell_biology": [
            "mitochondria", "atp", "synthase", "chemiosmosis", "membrane", "organelle",
            "ribosome", "endoplasmic", "lysosome", "phosphorylation", "cytoplasm",
            "cristae", "glycolysis", "citric acid cycle"
        ],
        "toxicology": [
            "toxic", "toxin", "poison", "urushiol", "alkaloid", "ld50", "venom",
            "dermatitis", "lethal", "overdose", "antidote", "pubchem", "adverse",
            "hazard", "irritant", "glycoside", "solanine"
        ],
        "marine": [
            "coral", "ocean", "reef", "marine", "zooxanthellae", "symbiodiniaceae",
            "bleaching", "benthic", "pelagic", "phytoplankton", "salinity",
            "abyssal", "intertidal", "aragonite", "calcification"
        ],
        "microbiology": [
            "bacteria", "bacterial", "bacterium", "virus", "viral", "phage", "bacteriophage",
            "prokaryote", "plasmid", "nitrogenase", "antibiotic", "resistance", "microbial",
            "microbiology", "microbe", "biofilm", "rhizobium", "lytic", "lysogeny",
            "gram-positive", "gram-negative"
        ],
        "entomology": [
            "insect", "beetle", "butterfly", "moth", "larva", "pupa", "imago",
            "ecdysone", "chitin", "exoskeleton", "hymenoptera", "metamorphosis",
            "ant", "bee", "wasp", "cuticle", "instar"
        ],
        "ornithology": [
            "bird", "avian", "feather", "wing", "flight", "air sac", "parabronchi",
            "keel", "beak", "clutch", "passerine", "raptor", "aerodynamics",
            "remiges", "carina", "pneumatic bone"
        ],
        "mycology": [
            "fungi", "fungus", "hyphae", "mycelium", "spore", "basidiomycete",
            "ascomycete", "mycorrhizae", "lichen", "saprotroph", "fruiting body",
            "chitinous", "hyphal", "rhizomorph"
        ],
        "pathology": [
            "pathogen", "disease", "blight", "mildew", "infection", "necrosis",
            "resistance", "hypersensitive", "systemic acquired resistance", "symptom",
            "virulence", "pamp", "phytoncide", "canker", "lesion", "lesions", "fungicide", "rot"
        ],
        "ecology": [
            "ecosystem", "biome", "trophic", "predator", "prey", "biomass",
            "succession", "nutrient cycle", "keystone", "niche", "food web",
            "biogeochemistry", "carrying capacity", "biodiversity"
        ],
        "evolution": [
            "speciation", "selection", "evolution", "darwin", "allopatric",
            "fossil", "lineage", "cladistics", "synapomorphy", "adaptation",
            "phylogeny", "homology", "divergence", "natural selection"
        ],
        "wildlife": [
            "mammal", "carnivore", "herbivore", "behavior", "navigation",
            "habitat", "foraging", "nocturnal", "migration", "territory",
            "ethology", "circadian", "predation", "home range"
        ],
        "communication": [
            "communication", "pedagogy", "extension", "farmer", "rhetoric",
            "honorifics", "counseling", "advisory", "vernacular", "empathy",
            "first aid", "dialogue", "simplification", "de-escalation"
        ]
    }

    def __init__(self, book_engine: Optional[BookEngine] = None,
                 catalog_engine: Optional[BookCatalogEngine] = None):
        self.book_engine = book_engine or BookEngine()
        self.catalog_engine = catalog_engine or BookCatalogEngine(catalog_file=self.book_engine.catalog_file)

    @classmethod
    def auto_classify_shelf(cls, text: str) -> Optional[str]:
        """Return a unique keyword-based shelf suggestion, or None for unknown/tied text."""
        text_lower = text.lower()
        words = set(re.findall(r"\b[a-z0-9_\-]+\b", text_lower))
        scores = {}
        for shelf, keywords in cls.SHELF_KEYWORDS.items():
            overlap = 0
            for kw in set(keywords) | {shelf.replace("_", " ")}:
                if " " in kw:
                    if kw in text_lower:
                        overlap += 2
                elif kw in words:
                    overlap += 1
            scores[shelf] = overlap

        best_shelf = max(scores, key=scores.get)
        best_score = scores[best_shelf]
        if best_score == 0 or sum(score == best_score for score in scores.values()) > 1:
            return None
        return best_shelf

    @staticmethod
    def chunk_scientific_text(
        raw_text: str, source_title: str, chunk_size_words: int = 180,
        overlap_words: int = 30, book_id: Optional[str] = None,
        edition: Optional[str] = None, chapter_num: Optional[int] = None,
        chapter_title: Optional[str] = None, citation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Bounded chunks with exact offsets in extracted text, not printed pages."""
        if type(chunk_size_words) is not int or type(overlap_words) is not int or not 0 <= overlap_words < chunk_size_words:
            raise ValueError("Require chunk_size_words > 0 and 0 <= overlap_words < chunk_size_words.")
        if not isinstance(raw_text, str) or len(raw_text.encode("utf-8")) > 8 * 1024 * 1024:
            raise ValueError("Input must be UTF-8 text no larger than 8 MiB.")
        words = list(re.finditer(r"\S+", raw_text))
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size_words, len(words))
            char_start, char_end = words[start].start(), words[end - 1].end()
            entry = {
                "source": f"{source_title} (Section {len(chunks) + 1})",
                "text": raw_text[char_start:char_end],
                "text_char_start": char_start, "text_char_end": char_end,
                "line_start": raw_text.count("\n", 0, char_start) + 1,
                "line_end": raw_text.count("\n", 0, char_end) + 1,
                "locator_precision": "extracted_text_offsets",
            }
            for name, value in (("book_id", book_id), ("edition", edition), ("chapter_num", chapter_num),
                                ("chapter_title", chapter_title), ("citation", citation)):
                if value is not None:
                    entry[name] = value
            chunks.append(entry)
            if end == len(words):
                break
            start = end - overlap_words
        return chunks

    @staticmethod
    def _extract_epub(file_path: str) -> tuple[str, str]:
        """Extracts title and full chapter text from an EPUB archive using standard library zipfile and XML."""
        import zipfile
        import xml.etree.ElementTree as ET
        from html.parser import HTMLParser

        class HTMLTextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.texts = []
            def handle_data(self, data):
                cleaned = data.strip()
                if cleaned:
                    self.texts.append(cleaned)
            def get_text(self):
                return " ".join(self.texts)

        with zipfile.ZipFile(file_path, "r") as zf:
            # 1. Read container.xml to locate root OPF file
            container_xml = zf.read("META-INF/container.xml")
            c_root = ET.fromstring(container_xml)
            opf_rel = None
            for elem in c_root.iter():
                if elem.tag.endswith("rootfile") and "full-path" in elem.attrib:
                    opf_rel = elem.attrib["full-path"]
                    break
            opf_path = opf_rel or "content.opf"
            opf_dir = os.path.dirname(opf_path)

            # 2. Parse OPF package for metadata and spine
            opf_xml = zf.read(opf_path)
            opf_root = ET.fromstring(opf_xml)

            # Extract title
            title = None
            for elem in opf_root.iter():
                if elem.tag.endswith("title") and elem.text:
                    title = elem.text.strip()
                    break
            if not title:
                title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()

            # Map manifest items by id
            manifest = {}
            for item in opf_root.iter():
                if item.tag.endswith("item") and "id" in item.attrib and "href" in item.attrib:
                    manifest[item.attrib["id"]] = item.attrib["href"]

            # Read reading order from spine
            chapter_texts = []
            for itemref in opf_root.iter():
                if itemref.tag.endswith("itemref") and "idref" in itemref.attrib:
                    item_id = itemref.attrib["idref"]
                    href = manifest.get(item_id)
                    if href:
                        ch_path = os.path.normpath(os.path.join(opf_dir, href)).replace("\\", "/")
                        if ch_path in zf.namelist():
                            try:
                                raw_html = zf.read(ch_path).decode("utf-8", errors="strict")
                                parser = HTMLTextExtractor()
                                parser.feed(raw_html)
                                text = parser.get_text()
                                if text:
                                    chapter_texts.append(text)
                            except Exception:
                                pass

            # Fallback if spine was empty: parse all html/xhtml files in manifest
            if not chapter_texts:
                for name in zf.namelist():
                    if name.endswith((".xhtml", ".html", ".htm")):
                        try:
                            raw_html = zf.read(name).decode("utf-8", errors="strict")
                            parser = HTMLTextExtractor()
                            parser.feed(raw_html)
                            text = parser.get_text()
                            if text:
                                chapter_texts.append(text)
                        except Exception:
                            pass

            full_text = "\n\n".join(chapter_texts)
            return full_text, title

    @staticmethod
    def _extract_docx(file_path: str) -> tuple[str, str]:
        """Extracts plain text and title from DOCX archive using standard library zipfile and XML."""
        import zipfile
        import xml.etree.ElementTree as ET

        paragraphs = []
        with zipfile.ZipFile(file_path, "r") as zf:
            if "word/document.xml" in zf.namelist():
                doc_xml = zf.read("word/document.xml")
                root = ET.fromstring(doc_xml)
                for node in root.iter():
                    if node.tag.rsplit("}", 1)[-1] == "p":
                        texts = [t.text for t in node.iter() if t.tag.rsplit("}", 1)[-1] == "t" and t.text]
                        if texts:
                            paragraphs.append("".join(texts))

        full_text = "\n\n".join(paragraphs)
        title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
        return full_text, title

    def extract_text_from_file(self, file_path: str) -> tuple[str, str]:
        """Extracts plain text and base document title from EPUB, DOCX, PDF, MD, TXT, or JSON."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if os.path.getsize(file_path) > 20 * 1024 * 1024:
            raise ValueError("Source file exceeds the 20 MiB local import limit.")
        if os.path.splitext(file_path)[1].lower() in {".docx", ".epub"}:
            import zipfile
            with zipfile.ZipFile(file_path) as archive:
                entries = archive.infolist()
                if len(entries) > 10000 or sum(e.file_size for e in entries) > 40 * 1024 * 1024:
                    raise ValueError("Document archive exceeds the extraction budget.")
                if any(e.flag_bits & 1 for e in entries):
                    raise ValueError("Encrypted document archives are not supported.")
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        title = base_name.replace("_", " ").replace("-", " ").title()
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".epub":
            raw_text, epub_title = self._extract_epub(file_path)
            if epub_title:
                title = epub_title
        elif ext == ".docx":
            raw_text, docx_title = self._extract_docx(file_path)
            if docx_title:
                title = docx_title
        elif ext == ".pdf":
            if not HAS_PYPDF:
                raise ImportError("pypdf is required for parsing PDF documents. Run: uv pip install pypdf")
            reader = pypdf.PdfReader(file_path)
            extracted_pages = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
            raw_text = "\n\n".join(extracted_pages)
        elif ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8-sig", errors="strict") as f:
                raw_text = f.read()
        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                raw_text = "\n\n".join(item.get("text", "") for item in data if isinstance(item, dict))
            elif isinstance(data, dict):
                raw_text = data.get("text", "") or data.get("content", "")
            else:
                raw_text = str(data)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .epub, .docx, .pdf, .txt, .md, .json")

        return raw_text, title

    def ingest_file(self, file_path: str, shelf: Optional[str] = None,
                    source_title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                    document_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract text and index a revision; page locators are not inferred."""
        file_path = os.fspath(file_path)
        raw_text, detected_title = self.extract_text_from_file(file_path)
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("metadata must be a mapping")
        supplied = dict(metadata or {})
        supplied["source_filename"] = os.path.basename(file_path)
        with open(file_path, "rb") as raw_file:
            supplied["source_file_sha256"] = hashlib.sha256(raw_file.read()).hexdigest()
        return self.ingest_text(raw_text, source_title or detected_title, shelf,
                                metadata=supplied, document_id=document_id)

    def ingest_text(self, raw_text: str, source_title: str, shelf: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    document_id: Optional[str] = None) -> Dict[str, Any]:
        """Persist a document revision and replace its passages in both indexes.

        Metadata records what the caller actually supplied. It never fabricates an
        author, date, publisher, edition or source verification. Use document_id to
        replace a document whose title/shelf changes; otherwise shelf + title define
        its stable identity. Different works with the same title need distinct IDs.
        """
        if not isinstance(raw_text, str) or not isinstance(source_title, str) or not source_title.strip():
            raise ValueError("raw_text must be text and source_title must be non-empty.")
        effective_shelf = shelf if shelf is not None else self.auto_classify_shelf(raw_text)
        if effective_shelf is None:
            raise ValueError("Could not determine a unique shelf. Supply --shelf explicitly.")
        self.book_engine.validate_shelf(effective_shelf)
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("metadata must be a mapping")
        supplied = dict(metadata or {})
        authors = supplied.get("authors") or []
        if not isinstance(authors, list) or not all(isinstance(a, str) for a in authors):
            raise ValueError("metadata.authors must be a list of names.")
        year = supplied.get("year")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            raise ValueError("metadata.year must be an integer or None.")
        document_id = document_id or supplied.get("document_id") or (
            "doc_" + hashlib.sha256(f"{effective_shelf}\n{source_title.strip().casefold()}".encode("utf-8")).hexdigest()
        )
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id must be a non-empty string.")
        book_id = supplied.get("book_id") or document_id
        if not isinstance(book_id, str) or not book_id.strip():
            raise ValueError("book_id must be a non-empty string")
        if "\x00" in raw_text:
            raise ValueError("Binary NUL bytes are not accepted as document text")
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        citation_parts = [", ".join(authors)] if authors else []
        if year is not None:
            citation_parts.append(f"({year})")
        citation_parts.append(source_title.strip())
        for field in ("edition", "publisher"):
            if supplied.get(field):
                citation_parts.append(str(supplied[field]))
        chunks = self.chunk_scientific_text(
            raw_text, source_title, book_id=book_id, edition=supplied.get("edition"),
            chapter_num=supplied.get("chapter_num"), chapter_title=supplied.get("chapter_title"),
            citation=". ".join(citation_parts),
        )
        if not chunks:
            return {"status": "warning", "message": "Text too short or empty; no passages generated.",
                    "shelf": effective_shelf, "chunks_count": 0}
        source_metadata = {key: supplied.get(key) for key in (
            "publisher", "edition", "isbn", "source_url", "license", "source_filename",
            "source_file_sha256", "fetch_receipt", "source_family_id", "ingestion_method",
        )}
        source_metadata.update(authors=authors, year=year)
        raw_dir = os.path.join(self.book_engine.data_dir, "_raw")
        os.makedirs(raw_dir, exist_ok=True)
        raw_relative = os.path.join("_raw", content_hash + ".txt")
        raw_path = os.path.join(self.book_engine.data_dir, raw_relative)
        if os.path.exists(raw_path):
            with open(raw_path, "rb") as stream:
                if hashlib.sha256(stream.read()).hexdigest() != content_hash:
                    raise ValueError("An immutable extracted-text snapshot is corrupted")
        else:
            with tempfile.NamedTemporaryFile("wb", dir=raw_dir, delete=False) as stream:
                temporary_raw = stream.name
                stream.write(raw_text.encode("utf-8"))
            os.replace(temporary_raw, raw_path)
        source_metadata.update(raw_text_sha256=content_hash, raw_text_relative_path=raw_relative)
        for i, chunk in enumerate(chunks):
            chunk.update({
                "document_id": document_id, "content_hash": content_hash,
                "passage_id": hashlib.sha256(f"{document_id}\n{content_hash}\n{i}".encode("utf-8")).hexdigest(),
                "source_type": "imported_document", "verification_status": "unverified",
                "review_status": "unreviewed", "authority_tier": "UNVERIFIED",
                "section_index": i + 1, "source_metadata": source_metadata,
                "page_range": supplied.get("page_range"),
                "locator_precision": "supplied_pages_and_text_offsets" if supplied.get("page_range") else "extracted_text_offsets",
            })
        shelf_dir = os.path.join(self.book_engine.data_dir, effective_shelf)
        os.makedirs(shelf_dir, exist_ok=True)
        filename = "document_" + hashlib.sha256(document_id.encode("utf-8")).hexdigest() + ".json"
        out_file = os.path.join(shelf_dir, filename)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=shelf_dir, suffix=".tmp", encoding="utf-8", delete=False) as f:
                temporary_path = f.name
                json.dump(chunks, f, indent=2, ensure_ascii=False)
            os.replace(temporary_path, out_file)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
        # Moving a known document between shelves must not resurrect its old file.
        for previous_shelf in BookEngine.DEFAULT_SHELVES:
            previous = os.path.join(self.book_engine.data_dir, previous_shelf, filename)
            if previous != out_file and os.path.isfile(previous):
                os.unlink(previous)
        self.book_engine.replace_document(document_id, effective_shelf, chunks)
        warnings = []
        try:
            self.catalog_engine.register_book(
                book_id=book_id, title=source_title.strip(), authors=authors, year=year,
                faculty=supplied.get("faculty") or "general", discipline=effective_shelf,
                edition=supplied.get("edition"), publisher=supplied.get("publisher"),
                isbn=supplied.get("isbn"), source_url=supplied.get("source_url"),
                license=supplied.get("license"), associated_shelf=effective_shelf,
                content_available=True, document_id=document_id, content_hash=content_hash,
            )
        except OSError as exc:
            warnings.append(f"Text was indexed, but catalog registration failed: {exc}")
        return {
            "status": "success", "source_title": source_title.strip(), "document_id": document_id,
            "content_hash": content_hash, "shelf": effective_shelf, "file_saved": out_file,
            "chunks_count": len(chunks), "total_words": len(raw_text.split()),
            "total_indexed_passages": len(self.book_engine.index),
            "verification_status": "unverified", "review_status": "unreviewed", "warnings": warnings,
            "sample_chunk": chunks[0]["text"][:200] + ("..." if len(chunks[0]["text"]) > 200 else ""),
        }
