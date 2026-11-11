import os
import json
import re
from typing import List, Dict, Any, Optional

class EpistemicReviewEngine:
    """
    Tier 3 Epistemic Discourse & Review Engine.
    Tracks peer reviews, academic critiques, scholarly consensus scores,
    dialectical debates, counter-theories, and official errata for canonical works.
    
    Prevents single-author dogma and equips the system with scientific critical awareness.
    """

    _default_review_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "catalog", "book_reviews_and_debates.json"
    )

    def __init__(self, review_file: Optional[str] = None):
        self.review_file = review_file or self._default_review_file
        self.reviews: List[Dict[str, Any]] = self._load_reviews()

    def _load_reviews(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.review_file):
            return []
        try:
            with open(self.review_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_reviews(self) -> bool:
        """Persists reviews to disk."""
        try:
            os.makedirs(os.path.dirname(self.review_file), exist_ok=True)
            with open(self.review_file, "w", encoding="utf-8") as f:
                json.dump(self.reviews, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get_review_by_book_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete review dossier by exact or partial book_id."""
        b_id_norm = book_id.lower().strip()
        for rev in self.reviews:
            if rev.get("book_id", "").lower() == b_id_norm or b_id_norm in rev.get("book_id", "").lower():
                return rev
        return None

    def search_reviews(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Multilingual/Keyword search across book titles, authors, debate topics,
        peer reviews, and critiques.
        """
        if not query:
            return self.reviews[:limit]

        tokens = set(re.findall(r"\w+", query.lower()))
        matched = []

        for rev in self.reviews:
            searchable_corpus = (
                f"{rev.get('title', '')} "
                f"{rev.get('book_id', '')} "
                f"{' '.join(rev.get('authors', []))} "
                f"{rev.get('consensus_status', '')} "
            ).lower()

            # Add debate topics and critiques
            for d in rev.get("debates_and_critiques", []):
                searchable_corpus += f" {d.get('topic', '')} {d.get('canonical_view', '')} {d.get('critique_and_counterview', '')}"

            # Add peer review sources
            for pr in rev.get("peer_reviews", []):
                searchable_corpus += f" {pr.get('source', '')} {pr.get('verdict', '')} {pr.get('key_strengths', '')} {pr.get('identified_limitations', '')}"

            score = sum(1 for t in tokens if t in searchable_corpus)
            if score > 0 or any(t in rev.get("book_id", "").lower() for t in tokens):
                matched.append((score, rev))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matched[:limit]]

    def get_debates_for_topic(self, topic_query: str) -> List[Dict[str, Any]]:
        """Finds specific debates and counterarguments relevant to a topic."""
        results = []
        tokens = set(re.findall(r"\w+", topic_query.lower()))
        for rev in self.reviews:
            for d in rev.get("debates_and_critiques", []):
                d_text = f"{d.get('topic', '')} {d.get('canonical_view', '')} {d.get('critique_and_counterview', '')}".lower()
                if any(t in d_text for t in tokens):
                    results.append({
                        "book_title": rev.get("title"),
                        "book_id": rev.get("book_id"),
                        "consensus_status": rev.get("consensus_status"),
                        "debate": d
                    })
        return results

    def add_peer_review(
        self,
        book_id: str,
        source: str,
        rating: float,
        verdict: str,
        strengths: str,
        limitations: str
    ) -> bool:
        """Appends a new verified academic review to a cataloged book."""
        rev = self.get_review_by_book_id(book_id)
        if not rev:
            return False
        rev.setdefault("peer_reviews", []).append({
            "source": source,
            "rating": rating,
            "verdict": verdict,
            "key_strengths": strengths,
            "identified_limitations": limitations
        })
        return self.save_reviews()
