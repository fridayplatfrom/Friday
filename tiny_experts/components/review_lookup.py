from typing import Dict, Any, List, Optional
from ..pipeline.review_engine import EpistemicReviewEngine

class ReviewRecordLookup:
    """Retrieves stored reviews and applies explicit comparison rules; does not establish scientific consensus."""
    name = 'Review Record Lookup'
    description = 'Retrieves stored reviews and applies explicit comparison rules; does not establish scientific consensus.'
    component_kind = 'catalog_lookup'
    uses_neural_model = False
    updates_parameters_at_inference = False

    def __init__(self, review_engine: Optional[EpistemicReviewEngine] = None):
        self.review_engine = review_engine or EpistemicReviewEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "")
        book_id = context.get("book_id", "")
        vernacular_meta = context.get("vernacular_meta", {})
        norm_query = vernacular_meta.get("normalized_query") or query

        # 1. Search by exact book_id if available
        review_doc = None
        if book_id:
            review_doc = self.review_engine.get_review_by_book_id(book_id)

        # 2. Search by query tokens
        matching_reviews = []
        if review_doc:
            matching_reviews = [review_doc]
        else:
            matching_reviews = self.review_engine.search_reviews(norm_query, limit=3)

        # 3. Search relevant debates
        debates = self.review_engine.get_debates_for_topic(norm_query)

        if not matching_reviews and not debates:
            return {
                "matched": False,
                "reviews": [],
                "debates": [],
                "consensus_level": "UNREVIEWED_OR_COMMUNITY_SOURCE",
                "message": "No specific peer reviews or academic debates cataloged for this query."
            }

        top_rev = matching_reviews[0] if matching_reviews else {}
        consensus_score = top_rev.get("scholarly_consensus_score", 0.90)
        consensus_status = top_rev.get("consensus_status", "ACTIVE_SCHOLARLY_DEBATE")

        return {
            "matched": True,
            "book_id": top_rev.get("book_id"),
            "book_title": top_rev.get("title"),
            "scholarly_consensus_score": consensus_score,
            "consensus_status": consensus_status,
            "peer_reviews": top_rev.get("peer_reviews", []),
            "debates_and_critiques": top_rev.get("debates_and_critiques", []) or debates,
            "errata_and_revisions": top_rev.get("errata_and_revisions", []),
            "all_matching_books": [r.get("title") for r in matching_reviews]
        }


# Compatibility for existing integrations and model-training imports.
ReviewExpert = ReviewRecordLookup
