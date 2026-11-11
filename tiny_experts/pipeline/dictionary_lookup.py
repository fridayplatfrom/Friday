import os
import json
import re
from typing import List, Dict, Any, Optional

class DictionaryLookupService:
    """Static dictionary lookup and token-overlap ranking; no neural training."""
    name = "Dictionary Lookup Service"
    component_kind = "lexical_lookup"
    uses_neural_model = False
    updates_parameters_at_inference = False

    _default_lexicon_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "catalog", "multilingual_lexicon_dictionary.json"
    )

    def __init__(self, lexicon_file: Optional[str] = None):
        self.lexicon_file = lexicon_file or self._default_lexicon_file
        self.dictionary: List[Dict[str, Any]] = self._load_dictionary()

    def _load_dictionary(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.lexicon_file):
            return []
        try:
            with open(self.lexicon_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def lookup_term(self, term: str, lang: str = "en") -> Optional[Dict[str, Any]]:
        """Finds dictionary entry by exact term or substring match."""
        term_norm = term.lower().strip()
        for item in self.dictionary:
            if item.get("term") == term_norm or term_norm in item.get("term", ""):
                res = dict(item)
                res["localized_term"] = item.get("multilingual_translations", {}).get(lang) or item.get("term")
                return res

            # Also check if query matches vernacular translation
            for l_code, v_trans in item.get("multilingual_translations", {}).items():
                if term_norm in v_trans.lower():
                    res = dict(item)
                    res["localized_term"] = v_trans
                    return res
        return None

    def search_dictionary(self, query: str, lang: str = "en", limit: int = 3) -> List[Dict[str, Any]]:
        """Multilingual token-overlap search across terms, definitions, and etymologies."""
        tokens = set(re.findall(r"\w+", query.lower()))
        matched = []

        for item in self.dictionary:
            corpus = f"{item.get('term', '')} {item.get('etymology', '')} {str(item.get('definitions', {}))} {str(item.get('multilingual_translations', {}))}".lower()
            score = sum(1 for t in tokens if t in corpus)
            if any(t in item.get("term", "").lower() for t in tokens):
                score += 5

            if score > 0:
                item_copy = dict(item)
                item_copy["localized_term"] = item.get("multilingual_translations", {}).get(lang) or item.get("term")
                matched.append((score, item_copy))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matched[:limit]]


LexiconEngine = DictionaryLookupService  # Legacy import alias.
