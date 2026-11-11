"""Conservative candidate checks for comparable temperature claims.

A difference is flagged for review, never automatically reconciled. Discourse
words such as 'however' alone do not establish a contradiction.
"""
import math
import re
from collections import defaultdict
from typing import Any, Dict, List


class AutomatedContradictionEngine:
    TEMPERATURE = re.compile(r"(?<![\w.])([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(°\s*[cf]|deg\s*[cf]|celsius|fahrenheit|kelvin|k\b)", re.I)
    MARKERS = re.compile(r"\b(?:contrary to|disputed by|refuted by|however|whereas|in contrast|controversy|paradox)\b", re.I)

    @staticmethod
    def _celsius(value, unit):
        unit = re.sub(r"[\s°]", "", unit.lower()).replace("deg", "")
        if unit in {"k", "kelvin"}:
            return value - 273.15
        if unit in {"f", "fahrenheit"}:
            return (value - 32) * 5 / 9
        return value

    @classmethod
    def discover_contradictions(cls, passages: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        groups, markers = defaultdict(list), []
        for passage in passages[:32]:
            text = str(passage.get("text") or "")[:8000]
            source = str(passage.get("source") or "Unspecified source")
            matches = list(cls.TEMPERATURE.finditer(text))
            # Multiple temperatures may describe different conditions; leave
            # their comparison to a structured fact extractor.
            if len(matches) == 1:
                match = matches[0]
                value = cls._celsius(float(match.group(1)), match.group(2))
                context = text[:match.start()] + " <temperature> " + text[match.end():]
                context = re.sub(r"[^\w<>]+", " ", context.casefold()).strip()
                if math.isfinite(value) and len(context.replace("<temperature>", "").strip()) >= 8:
                    groups[context].append({"source": source, "temperature_c": value})
            marker = cls.MARKERS.search(text)
            if marker:
                markers.append({"source": source, "marker": marker.group(), "status": "discourse_marker_only"})
        differences, comparisons = [], 0
        for context, claims in groups.items():
            for index, first in enumerate(claims):
                for second in claims[index + 1:]:
                    comparisons += 1
                    if not math.isclose(first["temperature_c"], second["temperature_c"], rel_tol=1e-6, abs_tol=1e-6):
                        differences.append({"type": "POTENTIAL_NUMERICAL_CONFLICT", "parameter": "Temperature (normalized to Celsius)",
                            "claim_context": context, "thesis": f"{first['source']}: {first['temperature_c']:g} C",
                            "antithesis": f"{second['source']}: {second['temperature_c']:g} C",
                            "synthesis": "Unresolved. Verify that entity, time, conditions and measurement uncertainty are comparable before treating this difference as a contradiction."})
        return {"contradiction_detected": bool(differences), "discrepancy_count": len(differences),
                "status": "potential_conflict" if differences else "no_conflict_in_compared_claims" if comparisons else "insufficient_comparable_evidence",
                "comparisons_performed": comparisons, "reconciliations": differences,
                "discourse_markers": markers, "automatically_resolved": False}
