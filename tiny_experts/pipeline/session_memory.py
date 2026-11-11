from typing import Dict, Any, List, Optional
import re

class SessionMemory:
    """
    Lightweight Conversational Session Memory.
    Maintains multi-turn context, previous subjects, and resolves pronouns ('it', 'this', 'they')
    without adding memory bloat.
    """

    def __init__(self, max_history: int = 5):
        if not isinstance(max_history, int) or max_history < 1:
            raise ValueError("max_history must be a positive integer.")
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.last_species: Optional[str] = None
        self.last_category: Optional[str] = None

    def record_turn(self, query: str, response: str, meta: Dict[str, Any]):
        """Records a completed conversation turn."""
        species = meta.get("species")
        category = meta.get("category")
        # A completed turn with no identified subject must not silently inherit
        # an earlier one. The orchestrator supplies a resolved subject for an
        # actual follow-up; an unrelated turn clears the referent.
        self.last_species = species or None
        self.last_category = category if species else None

        self.history.append({
            "query": query,
            "response": response,
            "species": species,
            "category": category
        })

        if len(self.history) > self.max_history:
            self.history.pop(0)

    def resolve_context(self, query: str) -> Dict[str, Any]:
        """
        Resolves pronouns like 'it', 'this plant', 'the bird', 'is it safe'
        against the active conversation memory.
        If the query explicitly introduces a new entity, memory does not override it.
        """
        q_lower = query.lower()
        resolved_species = None

        # Check if query introduces a specific target (e.g. "tell me about red panda")
        has_new_target = any(
            phrase in q_lower for phrase in ["tell me about", "what about", "who is", "explain"]
        ) and not any(q_lower.strip().startswith(p) for p in ["is it", "can it", "will it", "does it"])

        # Check for pronoun or referential indicators
        pronoun_patterns = [
            r"\bis it\b", r"\bcan it\b", r"\bdoes it\b", r"\bwill it\b",
            r"\bthis plant\b", r"\bthe plant\b", r"\bthis bird\b",
            r"\bthe insect\b", r"\bthis animal\b", r"\bthe tree\b",
            r"\bfor it\b", r"\binto it\b", r"\bwith it\b"
        ]

        has_referential = any(re.search(pat, q_lower) for pat in pronoun_patterns)
        
        # Only resolve to previous species if referential and not explicitly introducing a new topic
        if has_referential and not has_new_target and self.last_species:
            resolved_species = self.last_species

        return {
            "resolved_species": resolved_species,
            "has_context": self.last_species is not None,
            "history_turns": len(self.history)
        }

    def clear(self):
        self.history.clear()
        self.last_species = None
        self.last_category = None
