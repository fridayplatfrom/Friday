from typing import Any, Dict, List, Optional
import re
from .base_component import BaseComponent
from ..pipeline.book_catalog_engine import BookCatalogEngine

class BookCatalogLookup(BaseComponent):
    """Searches bibliographic metadata; catalog membership does not imply full text is available."""
    name = 'Book Catalog Lookup'
    description = 'Searches bibliographic metadata; catalog membership does not imply full text is available.'
    component_kind = 'catalog_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    BIBLIO_KEYWORDS = [
        "book", "books", "textbook", "treatise", "compendium", "author", "written by",
        "published", "publisher", "isbn", "edition", "year", "library", "catalog",
        "bibliography", "literature survey", "reference", "manual",
        # Vernacular keywords (Hindi, Marathi, Bengali, Tamil, Telugu)
        "किताब", "किताबें", "पुस्तक", "ग्रंथ", "लेखक", "प्रकाशन", "संस्करण",
        "বই", "গ্রন্থ", "লেখক", "প্রকাশনা",
        "நூல்", "புத்தகம்", "ஆசிரியர்",
        "పుస్తకం", "గ్రంథం", "రచయిత"
    ]

    def __init__(self, catalog_engine: Optional[BookCatalogEngine] = None):
        super().__init__(
            name='Book Catalog Lookup',
            description='Searches bibliographic metadata; catalog membership does not imply full text is available.'
        )
        self.catalog_engine = catalog_engine or BookCatalogEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = (context.get("query") or "").strip()
        q_lower = query.lower()
        vern = context.get("vernacular_meta", {})
        lang = vern.get("detected_language", "en") if vern else "en"
        species = context.get("species", "")

        is_biblio = any(re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", q_lower) for kw in self.BIBLIO_KEYWORDS)
        browse_requests = {
            "books", "library", "catalog", "show books", "list books", "show all books",
            "list all books", "show catalog", "browse catalog", "show library", "list library",
            "what books do we have", "what books are available", "show available books",
        }
        browse = " ".join(q_lower.strip("?.! ").split()) in browse_requests
        matched_books = self.catalog_engine.search_books(query="" if browse else query, lang=lang, limit=5) if query else []
        # An unmatched subject is never replaced with unrelated catalog entries.
        is_relevant = is_biblio or (bool(matched_books) and any(w in q_lower for w in ["who", "source", "reference"]))
        top_book = matched_books[0] if matched_books else None
        citation_text = ""
        if top_book:
            pieces = []
            authors = top_book.get("authors") or []
            if authors:
                pieces.append(", ".join(authors))
            if top_book.get("year") is not None:
                pieces.append(f"({top_book['year']})")
            title = top_book.get("translated_title") or top_book.get("title")
            if title:
                pieces.append(f"*{title}*")
            for field in ("edition", "publisher"):
                if top_book.get(field):
                    pieces.append(str(top_book[field]))
            citation_text = ". ".join(pieces) + "."
        faculties = self.catalog_engine.list_faculties_and_disciplines()
        return {
            "status": "matched" if matched_books else "no_match",
            "relevant": is_relevant,
            "is_bibliographic_query": is_biblio,
            "is_catalog_browse": browse,
            "total_catalog_size": len(self.catalog_engine.catalog),
            "matched_books": matched_books,
            "top_book": top_book,
            "faculties_represented": list(faculties.keys()),
            "faculties_summary": faculties,
            "citation_text": citation_text,
            "verification_status": top_book.get("verification_status", "unverified") if top_book else "not_applicable",
            "content_available": bool(top_book and top_book.get("content_available")),
        }


# Compatibility for existing integrations and model-training imports.
LibrarianExpert = BookCatalogLookup
