import os
import json
import re
from typing import List, Dict, Any, Optional

class ConsensusRankingEngine:
    """
    Tier 3 Curated Consensus & Procedural Knowledge Engine.
    Powers multi-source consensus-ranked Top-10 lists, procedural How-To guides,
    and axiomatic 1-page What-Is primers.
    """

    _default_collections_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "catalog", "curated_collections.json"
    )

    def __init__(self, collections_file: Optional[str] = None):
        self.collections_file = collections_file or self._default_collections_file
        self.data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        if not os.path.exists(self.collections_file):
            return {"curated_top_10_lists": [], "how_to_guides": [], "what_is_primers": []}
        try:
            with open(self.collections_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"curated_top_10_lists": [], "how_to_guides": [], "what_is_primers": []}

    def find_top_10(self, query: str) -> Optional[Dict[str, Any]]:
        """Matches user query to authoritative top 10 consensus lists."""
        q_lower = query.lower()
        tokens = set(re.findall(r"\w+", q_lower))

        lists = self.data.get("curated_top_10_lists", [])
        for c in lists:
            c_text = f"{c.get('collection_id', '')} {c.get('title', '')} {c.get('faculty', '')}".lower()
            if any(k in q_lower for k in ["literature", "books", "साहित्य", "किताबें", "उपन्यास"]) and "literature" in c_text:
                return c
            if any(k in q_lower for k in ["physics", "discoveries", "breakthroughs", "भौतिकी", "खोज"]) and "physics" in c_text:
                return c

            score = sum(1 for t in tokens if t in c_text)
            if score >= 2:
                return c
        return None

    def find_how_to(self, query: str) -> Optional[Dict[str, Any]]:
        """Matches user query to step-by-step How-To manuals."""
        q_lower = query.lower()
        guides = self.data.get("how_to_guides", [])
        for g in guides:
            g_text = f"{g.get('guide_id', '')} {g.get('title', '')}".lower()
            if any(k in q_lower for k in ["diagnose", "plant disease", "रोग पहचान", "निदान"]) and "diagnose" in g_text:
                return g
            if any(k in q_lower for k in ["insulation", "heat conduction", "ऊष्मा रोधन", "थर्मल"]) and "insulation" in g_text:
                return g
        return None

    def find_what_is(self, query: str) -> Optional[Dict[str, Any]]:
        """Matches user query to axiomatic 1-page What-Is primers."""
        q_lower = query.lower()
        primers = self.data.get("what_is_primers", [])
        for p in primers:
            p_text = f"{p.get('primer_id', '')} {p.get('title', '')}".lower()
            if any(k in q_lower for k in ["basic structure", "मूल संरचना", "kesavananda", "केशवानंद"]) and "basic_structure" in p_text:
                return p
            if any(k in q_lower for k in ["entanglement", "एंटैंगलमेंट", "क्वांटम"]) and "entanglement" in p_text:
                return p
        return None
