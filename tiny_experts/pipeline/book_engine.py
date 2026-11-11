"""Source-backed local passage retrieval; this is indexing, not model training."""

import hashlib
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from .bm25 import BM25Retriever
from .sqlite_fts_engine import SQLiteFTSEngine

logger = logging.getLogger(__name__)


class BookEngine:
    """Search local source files through SQLite FTS5 and an in-memory BM25 fallback.

    Bundled notes are unreviewed demonstration material, not authenticated textbook
    excerpts. The complete source snapshot is read on startup, so this implementation
    does not claim constant memory use or instant startup for arbitrarily large books.
    """

    DEFAULT_SHELVES = [
        "genetics", "cell_biology", "botany", "mycology", "entomology",
        "ornithology", "wildlife", "ecology", "pathology", "toxicology",
        "marine", "microbiology", "evolution", "communication", "biology",
        "thermodynamics", "electronics", "mechanics", "physics", "literature", "grammar",
    ]
    _SNAPSHOT_CACHE: Dict[str, tuple] = {}

    def __init__(self, data_dir: Optional[str] = None, *,
                 db_path: Optional[str] = None, include_demo_seeds: bool = True):
        primary = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sources", "books")
        legacy = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "books")
        bundled = primary if os.path.exists(primary) else legacy
        state_dir = os.environ.get("TINY_EXPERT_STATE_DIR") or os.path.join(
            os.path.expanduser("~"), ".local", "share", "tiny-expert-system"
        )
        self.data_dir = os.path.abspath(os.fspath(data_dir)) if data_dir is not None else os.path.join(state_dir, "books")
        self.catalog_file = os.path.join(self.data_dir, "catalog.json")
        self.include_demo_seeds = include_demo_seeds
        self._source_roots = [(self.data_dir, "local_document")]
        if data_dir is None and os.path.isdir(bundled):
            self._source_roots.insert(0, (bundled, "demo_reference"))
        if db_path is None:
            db_path = os.path.join(self.data_dir, "epistemic_fts.db")

        self.index: List[Dict[str, Any]] = []
        self.bm25 = BM25Retriever(k1=1.5, b=0.75)
        self.fts_engine = SQLiteFTSEngine(db_path=db_path)
        self._ensure_shelves()
        self._load_or_seed_library()

    def close(self):
        self.fts_engine.close()

    def _ensure_shelves(self):
        for shelf in self.DEFAULT_SHELVES:
            os.makedirs(os.path.join(self.data_dir, shelf), exist_ok=True)
        local_raw = os.path.join(self.data_dir, "_raw")
        os.makedirs(local_raw, exist_ok=True)
        bundled_raw = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sources", "_raw")
        if os.path.isdir(bundled_raw):
            import shutil
            for f in os.listdir(bundled_raw):
                target_f = os.path.join(local_raw, f)
                if not os.path.exists(target_f):
                    try:
                        shutil.copy2(os.path.join(bundled_raw, f), target_f)
                    except OSError:
                        pass

    @classmethod
    def validate_shelf(cls, shelf: str):
        if shelf not in cls.DEFAULT_SHELVES:
            raise ValueError(f"Unknown shelf {shelf!r}. Choose one of: {', '.join(cls.DEFAULT_SHELVES)}")

    @staticmethod
    def _normalise_passage(passage: Dict[str, Any], shelf: str,
                           document_id: Optional[str] = None, source_type: str = "local_document"):
        p = dict(passage)
        p["shelf"] = shelf
        p["document_id"] = p.get("document_id") or document_id
        p.setdefault("source_type", source_type)
        p.setdefault("verification_status", "unverified")
        p.setdefault("review_status", "unreviewed")
        if source_type == "demo_reference":
            p["claimed_reference"] = p.get("claimed_reference") or p.get("source")
            p["claimed_citation"] = p.get("claimed_citation") or p.get("citation")
            p["source"] = f"Unverified demo note: {p.get('source', shelf)}"
            p["citation"] = None
            p["source_type"] = "demo_reference"
            p["verification_status"] = "unverified"
            p["review_status"] = "unreviewed"
            p["authority_tier"] = "UNVERIFIED"
        elif p.get("citation") and "Verified Academic Corpus" in p["citation"]:
            p["claimed_citation"] = p.pop("citation")
            p["citation"] = None
            p["verification_status"] = "unverified"
        return SQLiteFTSEngine.prepare_passage(p)

    def _compute_roots_signature(self) -> str:
        sig_parts = [f"demo={self.include_demo_seeds}"]
        for root, source_type in self._source_roots:
            for shelf in self.DEFAULT_SHELVES:
                shelf_path = os.path.join(root, shelf)
                if not os.path.isdir(shelf_path):
                    continue
                for fname in sorted(os.listdir(shelf_path)):
                    if not fname.lower().endswith((".txt", ".md", ".json")):
                        continue
                    fpath = os.path.join(shelf_path, fname)
                    try:
                        st = os.stat(fpath)
                        sig_parts.append(f"{source_type}:{fpath}:{st.st_size}:{st.st_mtime_ns}")
                    except OSError:
                        continue
        return hashlib.sha256("\n".join(sig_parts).encode("utf-8")).hexdigest()

    def _load_or_seed_library(self):
        sig = self._compute_roots_signature()
        cached = self._SNAPSHOT_CACHE.get(sig)
        if cached is not None:
            cached_index, cached_bm25 = cached
            self.index = [dict(p) for p in cached_index]
            self.bm25 = cached_bm25
            self.fts_engine.replace_all_passages(self.index)
            return

        self.index.clear()
        if self.include_demo_seeds:
            self._seed_textbook_excerpts()
        for root, source_type in self._source_roots:
            for shelf in self.DEFAULT_SHELVES:
                shelf_path = os.path.join(root, shelf)
                if not os.path.isdir(shelf_path):
                    continue
                for fname in sorted(os.listdir(shelf_path)):
                    fpath = os.path.join(shelf_path, fname)
                    if not os.path.isfile(fpath) or not fname.lower().endswith((".txt", ".md", ".json")):
                        continue
                    document_id = "file_" + hashlib.sha256(f"{root}/{shelf}/{fname}".encode("utf-8")).hexdigest()
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            if fname.lower().endswith(".json"):
                                items = json.load(f)
                                if not isinstance(items, list):
                                    raise ValueError("Passage JSON must contain a list.")
                            else:
                                items = [
                                    {"source": f"{fname} (Passage {i + 1})", "text": text.strip()}
                                    for i, text in enumerate(f.read().split("\n\n")) if text.strip()
                                ]
                        for item in items:
                            if not isinstance(item, dict) or not item.get("text", "").strip():
                                continue
                            self.index.append(self._normalise_passage(item, shelf, document_id, source_type))
                    except (OSError, ValueError, TypeError) as exc:
                        logger.warning("Could not load source file %s: %s", fpath, exc)

        self.index = list({p["passage_id"]: p for p in self.index}.values())
        # Counts cannot detect changed text or deleted/replaced files. Replace the
        # entire derived snapshot transactionally, even if its row count is unchanged.
        self.fts_engine.replace_all_passages(self.index)
        self.bm25.index_documents(self.index)
        self._SNAPSHOT_CACHE[sig] = ([dict(p) for p in self.index], self.bm25)

    def add_passages(self, shelf: str, passages: List[Dict[str, Any]]):
        """Upsert individual passages. Revisions should use replace_document."""
        self.validate_shelf(shelf)
        prepared = [self._normalise_passage(p, shelf) for p in passages]
        self.fts_engine.index_bulk_passages(prepared)
        by_id = {p["passage_id"]: p for p in self.index}
        by_id.update({p["passage_id"]: p for p in prepared})
        self.index = list(by_id.values())
        self.bm25 = BM25Retriever(k1=1.5, b=0.75)
        self.bm25.index_documents(self.index)

    def replace_document(self, document_id: str, shelf: str, passages: List[Dict[str, Any]]):
        """Replace all passages belonging to one logical document in both indexes."""
        self.validate_shelf(shelf)
        prepared = [self._normalise_passage({**p, "document_id": document_id}, shelf) for p in passages]
        self.fts_engine.replace_document(document_id, prepared)
        self.index = [p for p in self.index if p.get("document_id") != document_id] + prepared
        self.bm25 = BM25Retriever(k1=1.5, b=0.75)
        self.bm25.index_documents(self.index)

    def _seed_textbook_excerpts(self):
        """Load illustrative notes; original reference names are unverified claims."""
        seeds = [
            # 1. Genetics & Genomics
            {
                "shelf": "genetics",
                "source": "OpenStax Biology 2e, Ch. 14 (Genes & Chromosomes)",
                "text": "DNA transcription begins when RNA polymerase binds to a promoter sequence upstream of the coding region. In eukaryotes, pre-mRNA undergoes splicing where spliceosomes excise non-coding introns and ligate coding exons, preceded by 5-prime methylguanosine capping and 3-prime polyadenylation. Epigenetic modifications such as histone acetylation and DNA cytosine methylation regulate transcriptional access without altering nucleotide sequences."
            },
            # 2. Cell Biology & Metabolism
            {
                "shelf": "cell_biology",
                "source": "Alberts Molecular Biology of the Cell, Ch. 12 (Membrane Bioenergetics)",
                "text": "Mitochondrial oxidative phosphorylation couples electron transport down Complexes I through IV to proton translocation from the matrix into the intermembrane space. This creates an electrochemical proton motive force across the cristae membrane. Protons drive the rotary motor of ATP synthase (F0-F1 complex) to synthesize adenosine triphosphate from ADP and inorganic phosphate."
            },
            # 3. Botany & Plant Anatomy
            {
                "shelf": "botany",
                "source": "Raven Biology of Plants, Ch. 23 (Vascular Transport Physiology)",
                "text": "The cohesion-tension theory explains xylem sap ascent through tracheids and vessel elements. Solar radiation drives transpirational water vapor loss through stomata, generating high negative hydrostatic pressures in leaf mesophyll cell walls. Hydrogen-bonded water columns maintain continuous tensile strength from roots to the canopy without cavitation under standard osmotic conditions."
            },
            # 4. Mycology (Fungal Biology)
            {
                "shelf": "mycology",
                "source": "Introduction to Mycology, Ch. 5 (Mycorrhizal Mutualisms & Hyphal Networks)",
                "text": "Arbuscular mycorrhizal fungi (Glomeromycota) penetrate cortical plant root cells to form highly branched arbuscules, establishing high-surface-area nutrient exchange interfaces. Fungal hyphae extend kilometers through soil, solubilizing inorganic phosphorus and nitrogen for the host plant in reciprocal exchange for up to 20 percent of the plant's photosynthetically derived carbon."
            },
            # 5. Entomology (Invertebrate Biology)
            {
                "shelf": "entomology",
                "source": "Borror and DeLong's Study of Insects, Ch. 3 (Morphology & Metamorphosis)",
                "text": "The insect cuticle consists of an epicuticle wax barrier and a structural procuticle composed of chitin microfibrils embedded in a sclerotized protein matrix. Complete metamorphosis (holometabolous development) involves distinct egg, larval, pupal, and imago stages regulated by the endocrine balance between juvenile hormone from the corpora allata and 20-hydroxyecdysone from prothoracic glands."
            },
            # 6. Ornithology (Avian Science)
            {
                "shelf": "ornithology",
                "source": "Gill's Ornithology, Ch. 9 (Avian Respiratory Dynamics & Aerodynamics)",
                "text": "Birds utilize a unidirectional cross-current respiratory system powered by posterior and anterior air sacs, maintaining continuous oxygenation across parabronchi during both inspiration and expiration. Avian flight relies on asymmetric airfoils (asymmetric remiges primary feathers), reduced bone mass via trabecular pneumatic bones, and enlarged supracoracoideus and pectoralis muscles anchored to an osseous keel (carina)."
            },
            # 7. Ecology & Biomes
            {
                "shelf": "ecology",
                "source": "Odum's Fundamentals of Ecology, Ch. 8 (Trophic Cascades & Biogeochemistry)",
                "text": "Top-down trophic cascades demonstrate that apex predators regulate ecosystem biomass and nutrient cycling. Removal of keystone predators triggers hyper-abundance of intermediate mesopredators and primary herbivores, accelerating vegetation decimation and soil erosion. Ecosystem stability correlates with functional redundancy across biological guilds and high trophic link connectance."
            },
            # 8. Pathology & Immunology
            {
                "shelf": "pathology",
                "source": "Agrios' Plant Pathology, Ch. 6 (Host Defense & Systemic Acquired Resistance)",
                "text": "Plant innate immunity initiates with pattern recognition receptors detecting pathogen-associated molecular patterns (PAMPs). In response to virulent biotrophic or necrotrophic fungi, localized hypersensitive response (programmed cell death) limits pathogen spread. Systemic acquired resistance (SAR) is triggered via salicylic acid and pipecolic acid signaling, inducing pathogenesis-related (PR) proteins throughout distal plant tissues."
            },
            # 9. Toxicology & Chemical Defense
            {
                "shelf": "toxicology",
                "source": "Handbook of Botanical Toxicology, Ch. 7 (Urushiol Contact Dermatitis)",
                "text": "Toxicodendron radicans contains the pentadecylcatechol allergen urushiol. Upon dermal penetration, urushiol oxidizes to form reactive quinones that covalently bind to membrane proteins of skin dendritic cells. This induces a classic Type IV cell-mediated (delayed hypersensitivity) immune response, causing acute pruritic erythematous vesicles."
            },
            # 10. Wildlife Ethology
            {
                "shelf": "wildlife",
                "source": "Animal Behavior & Ethology, Ch. 11 (Orientation & Sensory Navigation)",
                "text": "Trans-continental animal navigation integrates celestial polarization patterns, infrasonic ocean acoustic waves, and geomagnetic field inclination detected via cryptochrome-mediated radical pairs in retinal photoreceptors. Animals exhibit calibrated sun-compass compensation adjusted dynamically by internal circadian clock pacemakers."
            },
            # 11. Marine Biology & Oceanography
            {
                "shelf": "marine",
                "source": "Castro & Huber Marine Biology, Ch. 14 (Coral Reef Dynamics & Ocean Primary Production)",
                "text": "Scleractinian hermatypic corals construct massive aragonite calcium carbonate biogenic reefs through obligate mutualistic endosymbiosis with dinoflagellates (Symbiodiniaceae, commonly termed zooxanthellae) residing inside host gastrodermal cells. Elevated sea surface temperatures cause photosynthetic electron transport disruption in zooxanthellae, releasing cytotoxic reactive oxygen species that force coral polyps to expel their symbionts in catastrophic thermal coral bleaching events."
            },
            # 12. Microbiology & Virology
            {
                "shelf": "microbiology",
                "source": "Brock Biology of Microorganisms, Ch. 3 (Diazotrophic Nitrogen Fixation & Bacterial Virology)",
                "text": "Biological nitrogen fixation is catalyzed by the ancient prokaryotic nitrogenase metalloenzyme complex (MoFe protein and Fe protein), which reduces atmospheric N2 into bio-available ammonia. Because nitrogenase is irreversibly denatured by molecular oxygen, symbiotic diazotrophs like Rhizobium utilize leghemoglobin oxygen-buffering proteins within root nodules to maintain micro-aerobic respiration while protecting catalytic nitrogenase active sites."
            },
            # 13. Evolutionary Biology & Paleontology
            {
                "shelf": "evolution",
                "source": "Futuyma Evolutionary Biology, Ch. 7 (Speciation, Phylogenetics & Deep Time)",
                "text": "Allopatric speciation occurs when a geographic vicariance event partitions a contiguous ancestral population, terminating gene flow. Over evolutionary epochs, independent genetic drift and divergent directional selection accumulate pre-zygotic and post-zygotic reproductive barriers. Cladistic phylogenetic analysis reconstructs monophyletic clades based on shared derived homologous characters (synapomorphies), corroborated by transitional fossil stratigraphy."
            }
        ]

        for item in seeds:
            self.index.append(self._normalise_passage(
                item, item["shelf"], f"demo:{item['shelf']}", "demo_reference"
            ))

    def search(self, query: str, shelf: Optional[str] = None, top_k: int = 2, *,
               document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if shelf is not None:
            self.validate_shelf(shelf)
        if not isinstance(query, str) or len(query) > 8192:
            raise ValueError("Query must be text no longer than 8192 characters")
        if type(top_k) is not int or top_k > 1000:
            raise ValueError("top_k must be an integer no greater than 1000")
        tokens = self.fts_engine.query_tokens(query, shelf)[:64]
        if not tokens or top_k <= 0:
            return []
        try:
            return self.fts_engine.search(query=query, shelf=shelf, limit=top_k, document_id=document_id)
        except sqlite3.Error as exc:
            logger.warning("FTS search unavailable; using in-memory BM25: %s", exc)
            results = self.bm25.search(query=" ".join(tokens), shelf_filter=shelf, top_k=len(self.index))
            return [p for p in results if document_id is None or p.get("document_id") == document_id][:top_k]


    def verify_passage(self, passage_id: str) -> Dict[str, Any]:
        """Verify a passage against its immutable extracted source text."""
        from pathlib import Path
        passage = self.get_passage(passage_id)
        if not passage:
            raise ValueError("Unknown or stale passage")
        meta = passage.get("source_metadata") or {}
        rel, digest = meta.get("raw_text_relative_path"), meta.get("raw_text_sha256")
        if not rel or not digest or digest != passage.get("content_hash"):
            raise ValueError("Passage is not backed by a hashed document snapshot")
        root = Path(self.data_dir).resolve()
        path = (root / rel).resolve()
        if not path.is_file():
            # Fallback to bundled sources _raw directory (e.g. for fresh clones)
            bundled_raw = Path(__file__).resolve().parent.parent / "data" / "sources" / rel
            if bundled_raw.is_file():
                path = bundled_raw.resolve()
                root = bundled_raw.parent.parent
            else:
                bundled_books_raw = Path(__file__).resolve().parent.parent / "data" / "sources" / "books" / rel
                if bundled_books_raw.is_file():
                    path = bundled_books_raw.resolve()
                    root = bundled_books_raw.parent.parent
        if not path.is_relative_to(root):
            raise ValueError("Source path outside data root")
        if not path.is_file():
            raise FileNotFoundError(f"Source snapshot file not found: {rel}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Source snapshot digest mismatch")
        source_text = raw.decode("utf-8")
        start, end = passage.get("text_char_start"), passage.get("text_char_end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source_text):
            raise ValueError("Invalid passage offsets")
        if source_text[start:end] != passage.get("text"):
            raise ValueError("Passage content does not match the source snapshot")
        return {"passage_id": passage_id, "document_id": passage.get("document_id"),
                "source_revision": digest, "verified_text_offsets": [start, end],
                "source_consistency": True, "semantic_support": "not_evaluated"}

    def get_passage(self, passage_id: str) -> Optional[Dict[str, Any]]:
        return next((dict(p) for p in self.index if p.get("passage_id") == passage_id), None)

    def lookup_document(self, document_id: str, query: str, top_k: int = 3) -> Dict[str, Any]:
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id is required")
        if not any(p.get("document_id") == document_id for p in self.index):
            return {"status": "document_not_found", "passages": [], "answer": None}
        passages = self.search(query, top_k=top_k, document_id=document_id)
        return {"status": "retrieved" if passages else "no_matching_evidence",
                "passages": passages, "answer": None,
                "limitation": "Lexical retrieval only; passage relevance does not certify an answer or scientific truth."}
