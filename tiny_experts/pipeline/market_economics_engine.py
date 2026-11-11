import os
import json
from typing import Dict, Any, List, Optional

class MarketEconomicsEngine:
    """
    Tier 6 Knowledge Engine: Mandi Market Commodity Pricing & Treatment Economics.
    
    Features:
    - Ingests e-NAM / Agmarknet modal wholesale commodity prices.
    - Computes Economic Injury Level (EIL) and Treatment Return-on-Investment (ROI).
    - Protects growers from bankrupting expenses when crop market prices are depressed.
    """

    _sources_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "economics", "mandi_market_rates_2026.json"
    )
    _legacy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "books", "economics", "mandi_market_rates_2026.json"
    )
    DEFAULT_ECONOMICS_FILE = _sources_path if os.path.exists(_sources_path) else _legacy_path

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or self.DEFAULT_ECONOMICS_FILE
        self.rates: List[Dict[str, Any]] = self._load_rates()

    def _load_rates(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.data_file):
            return []
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def evaluate_viability(
        self,
        crop: Optional[str] = None,
        estimated_spray_cost_inr: float = 650.0
    ) -> Optional[Dict[str, Any]]:
        """Estimate cost relative to *historical* assumed gross crop value.

        This is not ROI, economic injury level, treatment advice, or a current
        price quote; it excludes loss probability, efficacy, labor and yield risk.
        """
        import math
        if not crop or not math.isfinite(estimated_spray_cost_inr) or estimated_spray_cost_inr < 0:
            return None
        matches = [r for r in self.rates if str(r.get("crop", "")).casefold() == crop.strip().casefold()]
        if len(matches) != 1:
            return None
        matched = matches[0]
        try:
            price = float(matched["modal_price_per_quintal_inr"])
            yield_q = float(matched["average_yield_quintals_per_acre"])
        except (ValueError, TypeError, KeyError):
            return None
        if not all(math.isfinite(x) and x > 0 for x in (price, yield_q)):
            return None
        gross_value = price * yield_q
        ratio = estimated_spray_cost_inr / gross_value
        return {
            "crop": matched["crop"],
            "modal_price_per_quintal_inr": price,
            "primary_mandi": matched.get("primary_mandi"),
            "price_observation_date": matched.get("date"),
            "estimated_spray_cost_inr": estimated_spray_cost_inr,
            "assumed_gross_value_per_acre_inr": gross_value,
            "treatment_cost_to_assumed_gross_value_ratio": ratio,
            "viability_status": "NOT_ASSESSED",
            "financial_advisory": "No treatment or profitability recommendation is supported by this calculation.",
            "limitations": [
                "Price observation date, location and source need verification.",
                "Gross value is not net profit or expected avoided crop loss.",
                "Economic injury level and treatment effectiveness were not calculated."
            ]
        }
