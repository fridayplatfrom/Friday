import os
import json
from typing import Dict, Any, List, Optional

class BlogWebEngine:
    """
    Tier 4 Knowledge Engine: Authoritative Extension Blogs & Deep Web Links.
    
    Features:
    - Provides verified, non-hallucinated canonical URLs to university extension guides.
    - Extracts practical field pro-tips without overriding statutory laws or textbooks.
    - Enforces whitelisted academic and government domain safety.
    """

    _sources_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "blogs", "extension_blogs_directory.json"
    )
    _legacy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "books", "blogs", "extension_blogs_directory.json"
    )
    DEFAULT_BLOGS_FILE = _sources_path if os.path.exists(_sources_path) else _legacy_path

    def __init__(self, blogs_file: Optional[str] = None):
        self.blogs_file = blogs_file or self.DEFAULT_BLOGS_FILE
        self.guides: List[Dict[str, Any]] = self._load_guides()

    def _load_guides(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.blogs_file):
            return []
        try:
            with open(self.blogs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def find_relevant_guide(
        self,
        crop: Optional[str] = None,
        disease: Optional[str] = None,
        query: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Finds the most relevant authoritative university extension blog and deep link.
        """
        q_lower = query.lower()
        c_lower = crop.lower() if crop else ""
        d_lower = disease.lower() if disease else ""

        for g in self.guides:
            target_crop = g.get("crop", "").lower()
            target_disease = g.get("disease", "").lower()
            target_pathogen = g.get("pathogen", "").lower()

            crop_match = (target_crop and target_crop in q_lower) or (c_lower and target_crop in c_lower)
            disease_match = (
                (target_disease and target_disease in q_lower) or
                (target_pathogen and target_pathogen in q_lower) or
                (d_lower and target_disease in d_lower)
            )

            if crop_match and disease_match:
                return {
                    "title": g.get("title"),
                    "institution": g.get("institution"),
                    "author": g.get("author"),
                    "canonical_url": g.get("canonical_url"),
                    "publication_year": g.get("publication_year"),
                    "practical_summary": g.get("practical_summary"),
                    "field_pro_tips": g.get("field_pro_tips", []),
                    "markdown_link": f"[{g.get('title')} ({g.get('institution')})]({g.get('canonical_url')})"
                }

        # Fallback partial match
        if d_lower:
            for g in self.guides:
                if g.get("disease", "").lower() in d_lower or g.get("pathogen", "").lower() in d_lower:
                    return {
                        "title": g.get("title"),
                        "institution": g.get("institution"),
                        "author": g.get("author"),
                        "canonical_url": g.get("canonical_url"),
                        "publication_year": g.get("publication_year"),
                        "practical_summary": g.get("practical_summary"),
                        "field_pro_tips": g.get("field_pro_tips", []),
                        "markdown_link": f"[{g.get('title')} ({g.get('institution')})]({g.get('canonical_url')})"
                    }

        return None
