"""Explicit, session-scoped user context. New stores contain no personal facts."""

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional


class EpisodicMemory:
    DB_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "tiny-expert-system")
    DB_PATH = os.path.join(DB_DIR, "episodic_store.db")

    def __init__(self, db_path: Optional[str] = None):
        state_dir = os.environ.get("TINY_EXPERT_STATE_DIR")
        default_path = os.path.join(state_dir, "episodic_store.db") if state_dir else self.DB_PATH
        self.db_path = os.fspath(db_path) if db_path is not None else default_path
        self._lock = threading.RLock()
        self._memory_connection = None
        self._closed = False
        if self.db_path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_connection.row_factory = sqlite3.Row
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        if self._closed:
            raise RuntimeError("This memory store is closed.")
        with self._lock:
            conn = self._memory_connection or sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            try:
                with conn:
                    yield conn
            finally:
                if conn is not self._memory_connection:
                    conn.close()

    def close(self):
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None
        self._closed = True

    @staticmethod
    def _scope(session_id: str) -> str:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string.")
        return session_id

    def _init_database(self):
        # Do not import the old global tables: they could contain seeded demo
        # facts or context from unrelated sessions. They remain untouched on disk.
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS user_profile_v2 (
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    category TEXT,
                    PRIMARY KEY (session_id, key)
                );
                CREATE TABLE IF NOT EXISTS user_pets_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    species TEXT NOT NULL,
                    breed TEXT,
                    medical_notes TEXT
                );
                CREATE TABLE IF NOT EXISTS observation_logs_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    organism_name TEXT NOT NULL,
                    category TEXT,
                    notes TEXT
                );
            """)

    def get_profile(self, session_id: str = "default_session") -> Dict[str, str]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM user_profile_v2 WHERE session_id = ?", (self._scope(session_id),))
            return {row["key"]: row["value"] for row in rows}

    def get_pets(self, session_id: str = "default_session") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, species, breed, medical_notes FROM user_pets_v2 WHERE session_id = ? ORDER BY id",
                (self._scope(session_id),),
            )
            return [dict(row) for row in rows]

    def add_pet(self, name: str, species: str, breed: str = "", medical_notes: str = "",
                session_id: str = "default_session"):
        if not name.strip() or not species.strip():
            raise ValueError("Pet name and species are required.")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_pets_v2 (session_id, name, species, breed, medical_notes)
                VALUES (?, ?, ?, ?, ?)
            """, (self._scope(session_id), name.strip(), species.strip().casefold(), breed, medical_notes))

    def update_profile(self, key: str, value: str, category: str = "environment",
                       session_id: str = "default_session"):
        if not key.strip():
            raise ValueError("A profile key is required.")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_profile_v2 (session_id, key, value, category) VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, key) DO UPDATE SET value=excluded.value, category=excluded.category
            """, (self._scope(session_id), key, value, category))

    def log_observation(self, organism_name: str, category: str = "", notes: str = "",
                        session_id: str = "default_session"):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO observation_logs_v2 (session_id, organism_name, category, notes) VALUES (?, ?, ?, ?)
            """, (self._scope(session_id), organism_name, category, notes))

    def get_observations(self, session_id: str = "default_session") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, timestamp, organism_name, category, notes FROM observation_logs_v2
                WHERE session_id = ? ORDER BY id
            """, (self._scope(session_id),))
            return [dict(row) for row in rows]

    def clear_session(self, session_id: str = "default_session"):
        """Delete only this session's explicit profile, pets and observation log."""
        scope = self._scope(session_id)
        with self._get_connection() as conn:
            for table in ("user_profile_v2", "user_pets_v2", "observation_logs_v2"):
                conn.execute(f"DELETE FROM {table} WHERE session_id = ?", (scope,))

    def retrieve_context_for_query(self, query: str, session_id: str = "default_session") -> Dict[str, Any]:
        tokens = set(re.findall(r"\w+", query.casefold()))
        profile = self.get_profile(session_id)
        pets = self.get_pets(session_id)
        selected_pets = []
        if tokens & {"pet", "pets", "dog", "cat", "puppy", "kitten", "horse", "animal", "animals"}:
            for pet in pets:
                if tokens & {"pet", "pets"} or pet["species"] in tokens or pet["name"].casefold() in tokens:
                    selected_pets.append(pet)
        environment = {}
        if tokens & {"plant", "plants", "grow", "garden", "soil", "climate", "zone", "winter", "temperature"}:
            environment = {key: profile[key] for key in ("climate_zone", "soil_type", "region") if profile.get(key)}
        return {
            "has_relevant_profile": bool(selected_pets or environment),
            "pets": selected_pets,
            "environment": environment,
        }
