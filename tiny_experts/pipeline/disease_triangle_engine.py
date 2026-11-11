"""Local weather-based screening rules, not calibrated outbreak forecasts.

The existing rule bands are retained as transparent calculations. They have not
been validated against outbreak outcomes or the published models they resemble.
Missing weather is never replaced with invented observations.
"""
import math
import re
from typing import Any, Dict, Optional
from .quantity_parser import NUMBER


class DiseaseTriangleEngine:
    @classmethod
    def extract_weather_from_text(cls, query: str) -> Dict[str, Optional[float]]:
        values = {"temp_c": None, "rh_percent": None, "leaf_wetness_hours": None, "rainfall_mm": None}
        temp = re.search(rf"(?<![\w.])({NUMBER})\s*(°\s*[cf]|celsius|fahrenheit|kelvin|[ckf])(?!\w)", query, re.I)
        if temp:
            value, unit = float(temp.group(1)), temp.group(2).replace("°", "").replace(" ", "").lower()
            values["temp_c"] = value - 273.15 if unit in {"k", "kelvin"} else ((value - 32) * 5 / 9 if unit in {"f", "fahrenheit"} else value)
        humidity = re.search(rf"(?:\b(?:rh|humidity)\s*[:=]?\s*({NUMBER})\s*%|({NUMBER})\s*%\s*(?:rh|humidity)\b)", query, re.I)
        if humidity:
            values["rh_percent"] = float(humidity.group(1) or humidity.group(2))
        wetness = re.search(rf"\b(?:leaf\s*wetness|wet(?:ness)?|dew|rain\s+duration)\s*(?:for\s*)?[:=]?\s*({NUMBER})\s*(?:hours?|hrs?|h)\b", query, re.I)
        if wetness:
            values["leaf_wetness_hours"] = float(wetness.group(1))
        rain = re.search(rf"\brain(?:fall)?\s*[:=]?\s*({NUMBER})\s*mm\b", query, re.I)
        if rain:
            values["rainfall_mm"] = float(rain.group(1))
        return values

    @classmethod
    def calculate_wallin_severity_value(cls, temp_c: float, wet_hours: float, rh_percent: float) -> int:
        """Compute the legacy 0..4 daily screening index; not a validated Wallin implementation."""
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                   for v in [temp_c, wet_hours, rh_percent]):
            raise ValueError("Weather measurements must be finite numbers.")
        if not (-80 <= temp_c <= 60 and 0 <= wet_hours <= 24 and 0 <= rh_percent <= 100):
            raise ValueError("Provide valid daily temperature, humidity and 0..24 wetness hours.")
        if rh_percent < 90:
            return 0
        thresholds = [10, 13, 16, 19] if 15 <= temp_c <= 25 else [12, 16, 19, 22] if 10 <= temp_c < 15 else []
        if thresholds:
            return sum(wet_hours >= threshold for threshold in thresholds)
        return 1 if (7 <= temp_c < 10 or 25 < temp_c <= 28) and wet_hours >= 16 else 0

    @classmethod
    def evaluate_outbreak_risk(cls, disease_name: str, temp_c: Optional[float] = None,
                              rh_percent: Optional[float] = None, leaf_wetness_hours: Optional[float] = None,
                              rainfall_mm: Optional[float] = None, query: Optional[str] = None) -> Dict[str, Any]:
        values = dict(temp_c=temp_c, rh_percent=rh_percent, leaf_wetness_hours=leaf_wetness_hours, rainfall_mm=rainfall_mm)
        sources = {key: "provided" for key, value in values.items() if value is not None}
        if query:
            for key, value in cls.extract_weather_from_text(query).items():
                if values[key] is None and value is not None:
                    values[key], sources[key] = value, "parsed_from_query"
        result = {"disease": disease_name, "status": "insufficient_data", "risk_level": "UNKNOWN",
                  "outbreak_probability_pct": None, "model_validation": "not_validated", "reference_only": True,
                  "model_used": None, "severity_value": None, "symptom_window": None,
                  "weather_measurements": values, "measurement_sources": sources,
                  "weather_snapshot": " | ".join(f"{key}: {value if value is not None else 'unknown'}" for key, value in values.items()),
                  "missing_inputs": [], "errors": [],
                  "preventative_action": "Collect the required observations and confirm the suspected condition before using a disease-specific management protocol."}
        bounds = {"temp_c": (-80, 60), "rh_percent": (0, 100), "leaf_wetness_hours": (0, 24), "rainfall_mm": (0, 2000)}
        for key, value in values.items():
            low, high = bounds[key]
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high):
                result["errors"].append(f"{key} must be a finite number between {low} and {high}.")
        if result["errors"]:
            result["status"] = "invalid_data"
            return result
        disease = str(disease_name).lower()
        if re.search(r"\b(?:late blight|downy mildew)\b", disease):
            group = "late_blight"
        elif "powdery mildew" in disease:
            group = "powdery_mildew"
        elif re.search(r"\b(?:bacterial|canker|kresek)\b", disease):
            group = "bacterial"
        elif re.search(r"\b(?:early blight|alternaria|rust|scab|leaf spot)\b", disease):
            group = "fungal_wetness"
        else:
            result["status"] = "unsupported_disease"
            return result
        required = ["temp_c", "rh_percent", "leaf_wetness_hours"] + (["rainfall_mm"] if group == "bacterial" else [])
        result["missing_inputs"] = [key for key in required if values[key] is None]
        if result["missing_inputs"]:
            return result
        t, rh, wet = values["temp_c"], values["rh_percent"], values["leaf_wetness_hours"]
        if group == "late_blight":
            severity = cls.calculate_wallin_severity_value(t, wet, rh)
            band = "HIGH" if severity >= 3 else "MODERATE" if severity >= 1 else "LOW"
            index = f"SV {severity}/4"
        elif group == "powdery_mildew":
            warm, dry = 16 <= t <= 28, wet <= 3
            band = "HIGH" if warm and dry and 55 <= rh <= 85 else "MODERATE" if warm and rh > 45 else "LOW"
            index = f"Warm={warm}; dry_leaf={dry}; RH={rh}%"
        elif group == "bacterial":
            rainy, warm = values["rainfall_mm"] >= 10 or wet >= 12, 24 <= t <= 34
            band = "HIGH" if rainy and warm else "MODERATE" if rainy or (warm and rh >= 80) else "LOW"
            index = f"Moisture_trigger={rainy}; warm={warm}"
        else:
            threshold = 9 if 15 <= t <= 24 else 14 if 10 <= t < 15 else 18
            band = "HIGH" if wet >= threshold and rh >= 85 else "MODERATE" if wet >= .7 * threshold else "LOW"
            index = f"Wetness {wet:g}h / local threshold {threshold}h"
        result.update(status="computed_rule_index", risk_level=f"{band} RULE BAND",
                      model_used=f"Local {group.replace('_', ' ')} weather screening rule (unvalidated)", severity_value=index,
                      preventative_action="Use this screening band to prioritize observation; it is not an outbreak probability or a treatment recommendation.")
        return result
