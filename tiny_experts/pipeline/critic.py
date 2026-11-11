"""Scoped consistency checks over actual structured outputs.

Passing these checks is not a general correctness, safety or clinical review.
"""
import math
import re
from typing import Any, Dict


class ScientificCritic:
    @classmethod
    def audit_and_correct(cls, aggregated: Dict[str, Any], query: str) -> Dict[str, Any]:
        checks, corrections, issues = [], [], []
        toxicity = aggregated.get("toxicity") or {}
        botany = aggregated.get("botany") or {}
        marine = aggregated.get("marine") or {}
        math_info = aggregated.get("math") or {}

        if toxicity.get("is_hazardous") is True and botany:
            conflict = False
            for field in ["recommendation", "care_instructions"]:
                text = botany.get(field)
                if isinstance(text, str) and re.search(r"\b(?:bare hands|safe to eat|safe to handle|safe for consumption)\b", text, re.I):
                    botany[field] = "A hazard flag conflicts with the prior handling advice. Identification and appropriate precautions require verification before handling or consumption."
                    corrections.append(f"Withheld conflicting botanical {field} after an explicit toxicity hazard flag.")
                    conflict = True
            checks.append({"rule": "explicit_hazard_vs_handling_advice", "status": "corrected" if conflict else "no_explicit_conflict_found"})

        if marine.get("relevant") is True and botany.get("soil_profile"):
            botany["soil_profile"] = "Terrestrial soil advice withheld for the identified marine context; verify the organism and its habitat."
            corrections.append("Withheld terrestrial soil advice in a marine context.")
            checks.append({"rule": "marine_vs_terrestrial_soil", "status": "corrected"})

        for detail in math_info.get("details", []):
            if not isinstance(detail, dict) or detail.get("type") != "Plot Density Calculation":
                continue
            length, width, spacing = detail.get("length_m"), detail.get("width_m"), detail.get("spacing_m")
            values = [length, spacing] + ([width] if width is not None else [])
            if not all(isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value > 0 for value in values):
                issues.append("Plot-density output has missing or invalid geometric inputs.")
                checks.append({"rule": "rectangular_spacing_cells", "status": "invalid_inputs"})
                continue
            maximum_row = math.floor(length / spacing)
            row = detail.get("row_capacity_count")
            expected_total = maximum_row * math.floor(width / spacing) if width is not None else None
            total = detail.get("total_capacity")
            valid = row == maximum_row and (expected_total is None or total == expected_total)
            checks.append({"rule": "rectangular_spacing_cells", "status": "passed" if valid else "conflict", "expected_row_count": maximum_row, "expected_total": expected_total})
            if not valid:
                issues.append("Plot capacity does not match the stated rectangular spacing-cell model.")

        interactions = (aggregated.get("biochemical_pathway") or {}).get("detected_drug_interactions", [])
        if interactions:
            checks.append({"rule": "potential_interaction_followup", "status": "requires_verification"})
            issues.append("Potential chemical interaction mentions require substance and exposure verification; this check establishes no clinical conclusion.")
        if not checks:
            status, passed = "no_applicable_checks", None
        elif issues:
            status, passed = "issues_require_review", False
        else:
            status, passed = "scoped_checks_completed", True
        summary = ("No applicable consistency checks were performed." if not checks else
                   f"{len(checks)} scoped consistency checks completed; {len(corrections)} corrections and {len(issues)} unresolved issues. This is not a complete factual verification.")
        return {"status": status, "audit_passed": passed, "checks": checks, "issues": issues,
                "corrections_applied": corrections, "critic_logs": [f"{check['rule']}: {check['status']}" for check in checks],
                "summary": summary}
