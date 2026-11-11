"""Conservative measurement extraction for the deterministic numeric experts.

Values are scaled by the unit attached to that value, never by unrelated words
elsewhere in a question. Missing units use a documented SI default, where the
caller allows one. Unknown units are rejected instead of silently discarded.
"""
import math
import re
from typing import Dict, List, Optional

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?"


def read_quantity(text: str, labels: str, units: Dict[str, float], default_unit: Optional[str],
                  errors: List[str], assumptions: List[str], *, name: str,
                  standalone: bool = False) -> Optional[float]:
    unit_pattern = "|".join(re.escape(unit) for unit in sorted(units, key=len, reverse=True))
    suffix = rf"\s*(?P<unit>{unit_pattern})(?![\w/^²])" if units else r"(?!)"
    pattern = (rf"(?<!\w)(?:{labels})(?!\w)\s*(?:=|:|\bis\b|\bof\b|\bat\b)?\s*"
               rf"(?P<value>{NUMBER})(?:{suffix})?")
    match = re.search(pattern, text, re.IGNORECASE)
    if match is None and standalone and units:
        match = re.search(rf"(?<![\w.])(?P<value>{NUMBER}){suffix}", text, re.IGNORECASE)
    if match is None:
        return None
    value = float(match.group("value"))
    unit = match.groupdict().get("unit")
    if unit is None:
        # Words that merely connect measurements do not specify a unit.
        following = text[match.end("value"):].lstrip()
        word = re.match(r"[A-Za-zµμΩω°/]+", following)
        next_assignment = re.match(r"\w+\s*[:=]", following)
        if word and not next_assignment and word.group().lower() not in {"and", "with", "for", "to", "in", "at", "then", "or"}:
            errors.append(f"Unsupported or missing {name} unit: {word.group()}.")
            return None
        if default_unit is None:
            errors.append(f"An explicit unit is required for {name}.")
            return None
        unit = default_unit
        assumptions.append(f"Unspecified {name} unit interpreted as {default_unit}.")
    scale = units.get(unit.lower())
    if scale is None:
        errors.append(f"Unsupported {name} unit: {unit}.")
        return None
    value *= scale
    if not math.isfinite(value) or abs(value) > 1e12 or (value != 0 and abs(value) < 1e-15):
        errors.append(f"{name.capitalize()} must be zero or have finite magnitude between 1e-15 and 1e12 in SI units.")
        return None
    return value


def read_temperature(text: str, labels: str, errors: List[str], *, name: str) -> Optional[float]:
    """Read an explicitly labeled absolute temperature and return kelvin."""
    match = re.search(rf"(?<!\w)(?:{labels})(?!\w)\s*(?:=|:|\bis\b|\bof\b)?\s*"
                      rf"({NUMBER})\s*(°\s*[cf]|celsius|fahrenheit|kelvin|[kcf])?(?!\w)", text, re.I)
    if match is None:
        return None
    if match.group(2) is None:
        errors.append(f"Specify K, C or F explicitly for {name}; no temperature unit is inferred.")
        return None
    value = float(match.group(1))
    unit = match.group(2).replace("°", "").replace(" ", "").lower()
    if unit in {"c", "celsius"}:
        value += 273.15
    elif unit in {"f", "fahrenheit"}:
        value = (value - 32) * 5 / 9 + 273.15
    if not math.isfinite(value) or not 0 <= value <= 1e12:
        errors.append(f"{name.capitalize()} must be a finite absolute temperature from 0 to 1e12 K.")
        return None
    return value
