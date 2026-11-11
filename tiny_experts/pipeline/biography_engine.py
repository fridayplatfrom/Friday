import os
import json
import re
from typing import List, Dict, Any, Optional

class BiographyEngine:
    """
    Tier 2 Canonical Epistemic Engine: Universal People & Biographical Registry.
    Tracks foundational thinkers, scientists, jurists, authors, and inventors across human history.
    
    Features:
    - Multilingual name resolution (English, Hindi, Marathi, Bengali, Tamil, Telugu).
    - Bidirectional links: Person <-> Books <-> Theories/Laws <-> Historical Eras.
    - Sub-millisecond local CPU search and dynamic auto-registration.
    """

    _default_registry_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "catalog", "universal_people_registry.json"
    )

    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file or self._default_registry_file
        self.people: List[Dict[str, Any]] = self._load_registry()

    def _load_registry(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.registry_file):
            return []
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_registry(self) -> bool:
        """Persists people database to disk."""
        try:
            os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(self.people, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get_person_by_id(self, person_id: str) -> Optional[Dict[str, Any]]:
        norm_id = person_id.lower().strip()
        for p in self.people:
            if p.get("person_id") == norm_id or norm_id in p.get("person_id", ""):
                return p
        return None

    def search_people(
        self,
        query: str,
        faculty: Optional[str] = None,
        lang: str = "en",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Multilingual search across names, vernacular translations, institutions,
        and major inventions/theories.
        """
        if not query:
            return self.people[:limit]

        STOPWORDS = {"who", "was", "is", "were", "are", "the", "a", "an", "in", "of", "and", "about", "tell", "me", "what", "how", "did"}
        raw_tokens = [t.lower() for t in re.findall(r"\w+", query)]
        tokens = set(t for t in raw_tokens if t not in STOPWORDS and len(t) > 1)
        if not tokens:
            tokens = set(raw_tokens)

        matched = []

        for p in self.people:
            if faculty and faculty.lower() not in p.get("faculty", "").lower():
                continue

            # Build searchable text corpus
            corpus_parts = [
                p.get("name", ""),
                p.get("person_id", ""),
                p.get("nationality", ""),
                p.get("faculty", ""),
                " ".join(p.get("disciplines", [])),
                " ".join(p.get("institutions", [])),
                " ".join(p.get("major_inventions_and_theories", [])),
                " ".join(p.get("landmark_quotes", [])),
                p.get("epistemic_impact", ""),
                p.get("biography_summary", "")
            ]
            # Add vernacular names
            for v_name in p.get("vernacular_names", {}).values():
                corpus_parts.append(v_name)

            full_corpus = " ".join(corpus_parts).lower()
            score = sum(1 for t in tokens if t in full_corpus)

            # Direct name or id word match boost (huge signal)
            p_name_words = set(re.findall(r"\w+", p.get("name", "").lower()))
            p_id_words = set(re.findall(r"\w+", p.get("person_id", "").lower()))
            name_intersection = tokens.intersection(p_name_words.union(p_id_words))
            if name_intersection:
                score += len(name_intersection) * 20

            # Vernacular match boost
            v_match = any(t in str(p.get("vernacular_names", {})).lower() for t in tokens)
            if v_match:
                score += 15

            if score > 0:
                # Attach language-specific localized name
                p_copy = dict(p)
                p_copy["display_name"] = p.get("vernacular_names", {}).get(lang) or p.get("name")
                matched.append((score, p_copy))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matched[:limit]]

    def find_inventor_of(self, theory_query: str) -> List[Dict[str, Any]]:
        """Identifies which scientist or thinker discovered or authored a theory."""
        tokens = set(re.findall(r"\w+", theory_query.lower()))
        results = []
        for p in self.people:
            for inv in p.get("major_inventions_and_theories", []):
                inv_lower = inv.lower()
                if any(t in inv_lower for t in tokens):
                    results.append({
                        "person_name": p.get("name"),
                        "person_id": p.get("person_id"),
                        "matched_theory": inv,
                        "faculty": p.get("faculty")
                    })
        return results
