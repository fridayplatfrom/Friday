"""Small, explicit lexical matching helpers; these are not semantic inference."""
import re


def contains_term(text: str, term: str) -> bool:
    """Match a whole term/phrase, never 'ant' in 'quantum' or 'sea' in 'research'."""
    pattern = r"\s+".join(re.escape(part) for part in term.casefold().split())
    if not pattern:
        return False
    return re.search(r"(?<!\w)" + pattern + r"(?!\w)", text.casefold()) is not None


def contains_any(text: str, terms) -> bool:
    return any(contains_term(text, term) for term in terms)
