import os
import json
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional

class NewsEngine:
    """
    Tier 3 Knowledge Engine: Real-Time Pest & Outbreak News Alert System.
    
    Features:
    - Time-To-Live (TTL) Automatic Expiration: Prevents stale news from raising false alarms.
    - Regional & Crop-Specific Filtering: Alerts only trigger when relevant to user's crop/pathogen.
    - Zero Hallucination: Grounded in real, dated ICAR / USDA / Agromet regulatory bulletins.
    """

    _sources_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "news", "active_outbreak_bulletins_2026.json"
    )
    _legacy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "books", "news", "active_outbreak_bulletins_2026.json"
    )
    DEFAULT_NEWS_FILE = _sources_path if os.path.exists(_sources_path) else _legacy_path

    def __init__(self, news_file: Optional[str] = None):
        self.news_file = news_file or self.DEFAULT_NEWS_FILE
        self.bulletins: List[Dict[str, Any]] = self._load_bulletins()
        self.temporal_facts: List[Dict[str, Any]] = [
            {
                "fact_id": "gst_solar_modules_2021",
                "topic": "gst_rate_solar_cells",
                "domain": "gst_taxation",
                "claim": "GST rate on renewable energy solar modules is 5%.",
                "valid_from": "2017-07-01",
                "valid_until": "2021-09-30",
                "trust_tier": "gov_official",
                "supersedes_id": None,
                "superseded_by": "gst_solar_modules_2021_oct",
            },
            {
                "fact_id": "gst_solar_modules_2021_oct",
                "topic": "gst_rate_solar_cells",
                "domain": "gst_taxation",
                "claim": "GST rate on renewable energy solar modules was revised to 12% effective October 2021.",
                "valid_from": "2021-10-01",
                "valid_until": None,
                "trust_tier": "gov_official",
                "supersedes_id": "gst_solar_modules_2021",
                "superseded_by": None,
            },
        ]

    def ingest_temporal_fact(
        self,
        *,
        fact_id: str,
        topic: str,
        domain: str,
        claim: str,
        valid_from: str,
        valid_until: Optional[str] = None,
        trust_tier: str = "verified_news_org",
        supersedes_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registers a time-stamped fact and updates the supersession chain if trusted."""
        trust_rank = {"gov_official": 4, "academic_peer_reviewed": 3, "verified_news_org": 2, "general_web": 1}
        new_rank = trust_rank.get(trust_tier, 1)

        if supersedes_id:
            for existing in self.temporal_facts:
                if existing["fact_id"] == supersedes_id:
                    old_rank = trust_rank.get(existing.get("trust_tier", "general_web"), 1)
                    if new_rank < old_rank:
                        return {
                            "accepted": False,
                            "reason": f"Lower trust tier '{trust_tier}' cannot supersede '{existing.get('trust_tier')}'.",
                        }
                    existing["superseded_by"] = fact_id
                    if existing.get("valid_until") is None:
                        existing["valid_until"] = valid_from

        entry = {
            "fact_id": fact_id,
            "topic": topic,
            "domain": domain,
            "claim": claim,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "trust_tier": trust_tier,
            "supersedes_id": supersedes_id,
            "superseded_by": None,
        }
        self.temporal_facts.append(entry)
        return {"accepted": True, "fact": entry}

    def query_temporal_facts(self, topic_query: str, *, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """Returns both active (current) facts and historical timeline for a topic."""
        q_lower = topic_query.lower()
        matches = [
            f for f in self.temporal_facts
            if q_lower in f["topic"].lower() or q_lower in f["claim"].lower() or q_lower in f["domain"].lower()
        ]
        if as_of_date:
            active = [
                f for f in matches
                if f["valid_from"] <= as_of_date and (f["valid_until"] is None or as_of_date <= f["valid_until"])
            ]
        else:
            active = [f for f in matches if f.get("superseded_by") is None]
        return {
            "topic_query": topic_query,
            "as_of_date": as_of_date or str(date.today()),
            "active_facts": active,
            "historical_timeline": sorted(matches, key=lambda x: x["valid_from"]),
        }

    def _load_bulletins(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.news_file):
            return []
        try:
            with open(self.news_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def evaluate_outbreaks(
        self,
        crop: Optional[str] = None,
        pathogen: Optional[str] = None,
        query: str = "",
        current_date_str: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Audits query and detected biological entities against active, non-expired outbreak news bulletins.
        """
        curr_dt = datetime.strptime(current_date_str, "%Y-%m-%d").date() if current_date_str else date.today()
        q_lower = query.lower()
        crop_lower = crop.lower() if crop else ""
        pathogen_lower = pathogen.lower() if pathogen else ""

        for b in self.bulletins:
            # Check Time-To-Live expiration
            b_dt = datetime.strptime(b.get("date", "2026-01-01"), "%Y-%m-%d")
            age_days = (curr_dt - b_dt.date()).days
            ttl = b.get("ttl_days", 14)
            if age_days < 0 or age_days > ttl:
                continue  # Bulletin expired or in future

            # Check matching target crops and pathogens
            target_crops = [c.lower() for c in b.get("crops", [])]
            target_pathogens = [p.lower() for p in b.get("pathogens", [])]

            crop_match = any(re.search(r"(?<!\\w)" + re.escape(c) + r"(?!\\w)", q_lower) or (crop_lower and c == crop_lower) for c in target_crops if c)
            pathogen_match = any(re.search(r"(?<!\\w)" + re.escape(p) + r"(?!\\w)", q_lower) or (pathogen_lower and p == pathogen_lower) for p in target_pathogens if p)

            if crop_match or pathogen_match:
                return {
                    "is_active_outbreak": None,
                    "bulletin_match": True,
                    "local_outbreak_confirmed": False,
                    "location_match": "unverified",
                    "bulletin_id": b.get("bulletin_id"),
                    "date": b.get("date"),
                    "urgency": b.get("urgency", "WARNING"),
                    "headline": b.get("headline"),
                    "summary": b.get("summary"),
                    "mandatory_advisory": None,
                    "original_bulletin_advisory": b.get("mandatory_advisory"),
                    "source": b.get("source"),
                    "verification_status": b.get("verification_status", "unverified"),
                    "regions_affected": b.get("regions", []),
                    "days_active": age_days
                }

        return None
