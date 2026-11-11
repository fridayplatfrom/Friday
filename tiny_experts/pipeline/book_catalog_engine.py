"""A bibliographic catalog. A catalog entry does not imply full-text access or verification."""

import json
import os
import re
import tempfile
from typing import Any, Dict, List, Optional


class BookCatalogEngine:
    _sources_catalog_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "catalog", "universal_book_catalog.json"
    )
    _legacy_catalog_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "catalog", "universal_book_catalog.json"
    )
    DEFAULT_CATALOG_FILE = _sources_catalog_file if os.path.exists(_sources_catalog_file) else _legacy_catalog_file
    QUERY_STOPWORDS = {
        "a", "an", "the", "and", "or", "of", "on", "in", "to", "for", "about", "with",
        "what", "which", "who", "is", "are", "do", "we", "have", "me", "please", "tell",
        "show", "find", "list", "all", "books", "book", "textbooks", "textbook", "author",
        "authors", "wrote", "written", "by", "reference", "references", "catalog", "library",
    }

    def __init__(self, catalog_file: Optional[str] = None):
        state_dir = os.environ.get("TINY_EXPERT_STATE_DIR") or os.path.join(
            os.path.expanduser("~"), ".local", "share", "tiny-expert-system"
        )
        self.catalog_file = os.fspath(catalog_file) if catalog_file is not None else os.path.join(state_dir, "books", "catalog.json")
        self._include_bundled = catalog_file is None
        self._local_ids = set()
        self.catalog: List[Dict[str, Any]] = self._load_catalog()

    @staticmethod
    def _read_entries(path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise ValueError(f"Catalog {path!r} must contain a list of records.")
        return entries

    @staticmethod
    def _normalise_entry(entry: Dict[str, Any], demo: bool = False):
        book = dict(entry)
        fabricated = "Verified Contributor / Academic Faculty" in (book.get("authors") or [])
        if fabricated:
            book.update(authors=[], year=None, publisher=None, edition=None, isbn=None, translations={})
        book.setdefault("authors", [])
        if book.get("isbn") == "ISBN-PENDING":
            book["isbn"] = None
        if demo or fabricated or not book.get("verification_status"):
            if book.get("authority_tier") not in (None, "UNVERIFIED"):
                book["claimed_authority_tier"] = book["authority_tier"]
            book["authority_tier"] = "UNVERIFIED"
            book["verification_status"] = "unverified"
            book["review_status"] = "unreviewed"
        book.setdefault("source_type", "demo_catalog" if demo else "local_catalog")
        book.setdefault("content_available", False)
        return book

    def _load_catalog(self) -> List[Dict[str, Any]]:
        by_id = {}
        if self._include_bundled:
            for entry in self._read_entries(self.DEFAULT_CATALOG_FILE):
                by_id[entry.get("book_id")] = self._normalise_entry(entry, demo=True)
        for entry in self._read_entries(self.catalog_file):
            book_id = entry.get("book_id")
            self._local_ids.add(book_id)
            by_id[book_id] = self._normalise_entry(entry)
        return list(by_id.values())

    def save_catalog(self) -> bool:
        """Atomically persist local registrations without rewriting bundled metadata."""
        directory = os.path.dirname(os.path.abspath(self.catalog_file))
        os.makedirs(directory, exist_ok=True)
        entries = [b for b in self.catalog if not self._include_bundled or b.get("book_id") in self._local_ids]
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=directory, suffix=".tmp", encoding="utf-8", delete=False) as f:
                temporary_path = f.name
                json.dump(entries, f, indent=2, ensure_ascii=False)
            os.replace(temporary_path, self.catalog_file)
            return True
        except OSError:
            return False
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)

    @classmethod
    def query_tokens(cls, query: str):
        return {t for t in re.findall(r"\w+", query.casefold()) if t not in cls.QUERY_STOPWORDS}

    @staticmethod
    def _translated_entry(book: Dict[str, Any], lang: str):
        entry = dict(book)
        translation = (book.get("translations") or {}).get(lang, {})
        entry["translated_title"] = translation.get("title") or book.get("title")
        entry["translated_summary"] = translation.get("summary") or book.get("subtitle")
        return entry

    def search_books(self, query: Optional[str] = None, faculty: Optional[str] = None,
                     discipline: Optional[str] = None, author: Optional[str] = None,
                     year: Optional[int] = None, lang: str = "en", limit: int = 10) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        q_tokens = self.query_tokens(query or "")
        # None/empty query is an explicit browse operation. A nonempty query with
        # no meaningful terms is not evidence that every book matches.
        if query and query.strip() and not q_tokens:
            return []
        results = []
        for book in self.catalog:
            if faculty and book.get("faculty") != faculty:
                continue
            if discipline and book.get("discipline") != discipline:
                continue
            if year is not None and book.get("year") != year:
                continue
            if author and not any(author.casefold() in a.casefold() for a in book.get("authors", []) if isinstance(a, str)):
                continue
            fields = [book.get(k) or "" for k in ("title", "subtitle", "publisher", "faculty_label", "discipline_label")]
            fields.extend(book.get("authors") or [])
            fields.extend(book.get("epistemic_hallmarks") or [])
            for chapter in book.get("canonical_chapters") or []:
                fields.append(chapter.get("title") or "")
                fields.extend(chapter.get("keywords") or [])
            for translation in (book.get("translations") or {}).values():
                fields.extend([translation.get("title") or "", translation.get("summary") or ""])
            tokens = set(re.findall(r"\w+", " ".join(str(f) for f in fields).casefold()))
            score = len(q_tokens & tokens) if q_tokens else 1
            if not score:
                continue
            entry = self._translated_entry(book, lang)
            entry["match_score"] = score
            results.append(entry)
        results.sort(key=lambda x: (-x["match_score"], str(x.get("book_id", ""))))
        return results[:limit]

    def get_book_by_id(self, book_id: str, lang: str = "en") -> Optional[Dict[str, Any]]:
        for book in self.catalog:
            if book.get("book_id") == book_id:
                return self._translated_entry(book, lang)
        return None

    def list_faculties_and_disciplines(self) -> Dict[str, Dict[str, Any]]:
        faculties = {}
        for book in self.catalog:
            faculty = book.get("faculty") or "general"
            discipline = book.get("discipline") or "general"
            entry = faculties.setdefault(faculty, {
                "label": book.get("faculty_label") or faculty.title(), "disciplines": {},
            })
            details = entry["disciplines"].setdefault(discipline, {
                "label": book.get("discipline_label") or discipline.title(), "books_count": 0,
            })
            details["books_count"] += 1
        return faculties

    def register_book(self, book_id: str, title: str, authors: Optional[List[str]] = None,
                      year: Optional[int] = None, faculty: str = "general", discipline: str = "general",
                      edition: Optional[str] = None, subtitle: str = "", publisher: Optional[str] = None,
                      isbn: Optional[str] = None, authority_tier: str = "UNVERIFIED",
                      translations: Optional[Dict[str, Dict[str, str]]] = None,
                      canonical_chapters: Optional[List[Dict[str, Any]]] = None,
                      epistemic_hallmarks: Optional[List[str]] = None,
                      associated_shelf: Optional[str] = None, source_url: Optional[str] = None,
                      license: Optional[str] = None, content_available: bool = False,
                      document_id: Optional[str] = None, content_hash: Optional[str] = None) -> Dict[str, Any]:
        """Register supplied metadata; registration is never factual verification."""
        if not book_id or not title or not title.strip():
            raise ValueError("A book_id and non-empty title are required.")
        if authors is not None and (not isinstance(authors, list) or not all(isinstance(a, str) for a in authors)):
            raise ValueError("authors must be a list of names.")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            raise ValueError("year must be an integer or None.")
        entry = {
            "book_id": book_id, "title": title, "subtitle": subtitle, "edition": edition,
            "year": year, "authors": list(authors or []), "publisher": publisher, "isbn": isbn,
            "faculty": faculty, "faculty_label": faculty.replace("_", " ").title(),
            "discipline": discipline, "discipline_label": discipline.replace("_", " ").title(),
            "authority_tier": "UNVERIFIED", "verification_status": "unverified", "review_status": "unreviewed",
            "source_type": "local_catalog", "source_url": source_url, "license": license,
            "translations": translations or {}, "canonical_chapters": canonical_chapters or [],
            "epistemic_hallmarks": epistemic_hallmarks or [], "associated_shelf": associated_shelf or discipline,
            "figure_plates": [], "content_available": bool(content_available),
            "document_id": document_id, "content_hash": content_hash,
        }
        if authority_tier != "UNVERIFIED":
            entry["claimed_authority_tier"] = authority_tier
        old_catalog, old_ids = list(self.catalog), set(self._local_ids)
        existing = next((i for i, b in enumerate(self.catalog) if b.get("book_id") == book_id), None)
        if existing is None:
            self.catalog.append(entry)
        else:
            self.catalog[existing] = entry
        self._local_ids.add(book_id)
        if not self.save_catalog():
            self.catalog, self._local_ids = old_catalog, old_ids
            raise OSError(f"Could not persist catalog to {self.catalog_file}")
        return {
            "status": "success", "action": "registered" if existing is None else "updated",
            "book_id": book_id, "title": title, "total_books_in_catalog": len(self.catalog),
        }
