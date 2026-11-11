import os
import json
import re
from typing import Dict, Any, List, Optional

class DiagnosticTreeEngine:
    """Retrieve crop-specific diagnostic procedure references.

    This module does not execute a decision tree, validate its attributed
    sources, or confirm a diagnosis from unobserved tests.
    """

    _sources_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "decision_trees", "university_diagnostic_keys.json"
    )
    _legacy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "books", "decision_trees", "university_diagnostic_keys.json"
    )
    DEFAULT_TREE_FILE = _sources_path if os.path.exists(_sources_path) else _legacy_path

    def __init__(self, tree_file: Optional[str] = None):
        self.tree_file = tree_file or self.DEFAULT_TREE_FILE
        self.keys: List[Dict[str, Any]] = self._load_keys()

    def _load_keys(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.tree_file):
            return []
        try:
            with open(self.tree_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []
        except Exception:
            return []

    def get_in_field_test(
        self,
        condition: Optional[str] = None,
        crop: Optional[str] = None,
        query: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a crop-specific procedure reference; no test is executed here.
        """
        q_lower = query.lower()
        cond_lower = condition.lower() if condition else ""

        for k in self.keys:
            target_cond = k.get("condition", "").lower()
            target_crop = k.get("crop", "").strip().casefold()
            if crop and target_crop and crop.strip().casefold() != target_crop:
                continue
            condition_pattern = r"(?<!\w)" + re.escape(target_cond) + r"(?!\w)"
            if target_cond and (re.search(condition_pattern, q_lower) or re.search(condition_pattern, cond_lower)):
                return {
                    "status": "procedure_reference",
                    "reference_only": True,
                    "source_validation": "not_verified",
                    "applicable_crop": k.get("crop"),
                    "crop_confirmed": bool(crop),
                    "test_name": k.get("test_name"),
                    "university_source": k.get("university_source"),
                    "in_field_steps": [re.sub(r"\bconfirm(?:s|ed)?\b", "may be consistent with", str(step), flags=re.I)
                                       for step in k.get("in_field_steps", [])],
                    "rapid_diagnostic_outcome": "This procedure has not been executed. Observations and qualified verification are required before a diagnosis."
                }

        return None
