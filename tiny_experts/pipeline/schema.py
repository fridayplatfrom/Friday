from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any

@dataclass
class OrganismDataRecord:
    """Structured entity data; storing a record does not establish its accuracy."""
    common_name: str
    scientific_name: str
    category: str               # "plant", "bird", "insect", "animal", "fungi"
    summary: str
    habitat: str
    diet_or_soil: str
    care_or_behavior: str
    hazard_level: str           # "NONE DETECTED", "LOW", "MODERATE", "HIGH", "CRITICAL"
    toxin_notes: str
    source_url: str
    source_type: str = "unreviewed_record"
    verification_status: str = "unverified"
    review_status: str = "unreviewed"
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
