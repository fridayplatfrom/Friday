"""Wikipedia discovery only; extracted summaries are not safety determinations."""
import re
import urllib.parse
import urllib.request
import json
from typing import Optional, Dict, Any
from .schema import OrganismDataRecord

class ScientificDataHarvester:
    USER_AGENT = "TinyExpertSystem/0.3 (research prototype; no safety claims)"

    @classmethod
    def fetch_wikipedia_summary(cls, topic: str) -> Optional[Dict[str, Any]]:
        topic = topic.strip()
        if not topic or len(topic) > 160 or any(ord(c) < 32 for c in topic):
            return None
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(topic.replace(" ", "_"), safe="")
        req = urllib.request.Request(url, headers={"User-Agent": cls.USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    return None
                value = json.loads(response.read(1_000_000).decode("utf-8"))
                return value if isinstance(value, dict) else None
        except (OSError, ValueError, UnicodeError):
            return None

    @classmethod
    def harvest(cls, query: str) -> Optional[OrganismDataRecord]:
        raw = cls.fetch_wikipedia_summary(query)
        if not raw or not isinstance(raw.get("extract"), str) or not raw["extract"].strip():
            return None
        title = str(raw.get("title") or query)
        extract = raw["extract"]
        description = str(raw.get("description") or "")
        words = set(re.findall(r"[a-z]+", (description + " " + extract).lower()))
        if words & {"plant", "flower", "tree", "shrub", "botany"}:
            category = "plant"
        elif words & {"bird", "avian", "feather"}:
            category = "bird"
        elif words & {"insect", "butterfly", "moth", "beetle"}:
            category = "insect"
        elif words & {"fungus", "mushroom", "mycelium"}:
            category = "fungi"
        else:
            category = "unclassified"
        # A summary mentioning the words 'safe', 'toxic' or 'deadly' cannot
        # establish species identity, dose, part, route, pet safety, or hazard.
        # Never turn absence of a keyword into a negative toxicity finding.
        match = re.search(r"\(([A-Z][a-z]+ [a-z]+)\)", extract)
        urls = raw.get("content_urls") or {}
        source_url = ((urls.get("desktop") or {}).get("page") if isinstance(urls, dict) else None) or ""
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            source_url = ""
        return OrganismDataRecord(
            common_name=title, scientific_name=match.group(1) if match else "",
            category=category, summary=extract[:280] + ("..." if len(extract) > 280 else ""),
            habitat="Not established by this importer",
            diet_or_soil="Not established by this importer",
            care_or_behavior="Not established by this importer",
            hazard_level="UNKNOWN",
            toxin_notes="Not assessed. Encyclopedic summaries are not evidence of safety or edibility.",
            source_url=source_url, source_type="wikipedia_summary",
            verification_status="unverified", review_status="unreviewed",
            source_metadata={"query": query, "extraction_method": "unreviewed_summary"}
        )
