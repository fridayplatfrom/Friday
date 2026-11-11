"""Explicit structured records with conservative name matching and provenance."""

import json
import os
import re
import tempfile
import threading
from typing import Any, Dict, Optional

from .schema import OrganismDataRecord


class KnowledgeStore:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "tiny-expert-system")
    STORE_PATH = os.path.join(DATA_DIR, "knowledge_base.json")
    _lock = threading.RLock()

    @classmethod
    def _path(cls, store_path: Optional[str] = None) -> str:
        if store_path is not None:
            return os.fspath(store_path)
        state_dir = os.environ.get("TINY_EXPERT_STATE_DIR")
        return os.path.join(state_dir, "knowledge_base.json") if state_dir else cls.STORE_PATH

    @classmethod
    def ensure_storage(cls, store_path: Optional[str] = None):
        path = cls._path(store_path)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "x", encoding="utf-8") as f:
                json.dump({}, f)

    @classmethod
    def load_all(cls, store_path: Optional[str] = None) -> Dict[str, Any]:
        path = cls._path(store_path)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not all(isinstance(record, dict) for record in data.values()):
            raise ValueError("Knowledge storage must contain a mapping of names to records.")
        for record in data.values():
            record.setdefault("verification_status", "unverified")
            record.setdefault("review_status", "unreviewed")
            record.setdefault("source_type", "local_record")
        return data

    @staticmethod
    def _normalise_name(value: str) -> str:
        return " ".join(re.findall(r"\w+", value.casefold()))

    @classmethod
    def save(cls, record: OrganismDataRecord, search_alias: Optional[str] = None,
             store_path: Optional[str] = None) -> bool:
        key = cls._normalise_name(record.common_name)
        if not key:
            raise ValueError("A record must have a non-empty common name.")
        path = cls._path(store_path)
        directory = os.path.dirname(os.path.abspath(path))
        with cls._lock:
            # Invalid existing JSON is an error, not an empty store to overwrite.
            data = cls.load_all(path)
            data[key] = record.to_dict()
            alias = cls._normalise_name(search_alias) if search_alias else ""
            if alias and alias != key:
                data[alias] = record.to_dict()
            os.makedirs(directory, exist_ok=True)
            temporary_path = None
            try:
                with tempfile.NamedTemporaryFile("w", dir=directory, suffix=".tmp", encoding="utf-8", delete=False) as f:
                    temporary_path = f.name
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(temporary_path, path)
            finally:
                if temporary_path and os.path.exists(temporary_path):
                    os.unlink(temporary_path)
        return True

    @classmethod
    def find(cls, query: str, store_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        q = cls._normalise_name(query)
        if not q:
            return None
        data = cls.load_all(store_path)
        candidates = []
        for alias, record in data.items():
            names = [alias, record.get("common_name") or "", record.get("scientific_name") or ""]
            for name in names:
                normalised = cls._normalise_name(name)
                if not normalised:
                    continue
                if q == normalised:
                    return record
                # Match whole names inside a sentence, never arbitrary summary
                # fragments or substrings such as 'cat' inside 'education'.
                if f" {normalised} " in f" {q} ":
                    candidates.append((len(normalised.split()), len(normalised), record))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return candidates[0][2]
        return None
