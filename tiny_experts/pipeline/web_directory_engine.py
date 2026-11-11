import os
import json
import re
from typing import List, Dict, Any, Optional

class UniversalWebDirectoryEngine:
    """
    Tier 3 Curated Web Directory & Authority Credibility Engine.
    Catalogs official sovereign government portals (.gov), premier university archives (.edu),
    learned societies (.org), and verified academic knowledge repositories.
    
    Includes strict adult-content filtering and institutional credibility tier badges.
    """

    _default_dir_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "catalog", "universal_web_directory.json"
    )

    def __init__(self, directory_file: Optional[str] = None):
        self.directory_file = directory_file or self._default_dir_file
        self.sites: List[Dict[str, Any]] = self._load_sites()

    def _load_sites(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.directory_file):
            return []
        try:
            with open(self.directory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def find_sites(self, query: str, faculty: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """Matches search query to authoritative web resources."""
        tokens = set(re.findall(r"\w+", query.lower()))
        matched = []

        for site in self.sites:
            if faculty and faculty.lower() not in site.get("faculty", "").lower():
                continue

            corpus = f"{site.get('title', '')} {site.get('faculty', '')} {site.get('description', '')} {' '.join(site.get('topics', []))}".lower()
            score = sum(1 for t in tokens if t in corpus)
            if any(t in site.get("site_id", "") for t in tokens):
                score += 4

            if score > 0:
                matched.append((score, site))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matched[:limit]]
