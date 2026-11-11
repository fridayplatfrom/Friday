"""A rebuildable SQLite FTS5 cache of passage text and its source metadata."""

import hashlib
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional


class SQLiteFTSEngine:
    """Search passage text; bibliographic metadata is retained but not indexed.

    The database is a derived cache, not the source of truth. BookEngine replaces
    its snapshot from source files on load, including when the row count is equal.
    """

    STOPWORDS = {
        "how", "do", "does", "what", "is", "are", "and", "or", "in", "the",
        "a", "an", "of", "to", "for", "with", "on", "at", "by", "from", "can",
        "be", "about", "tell", "me", "please", "explain", "describe", "show",
        "why", "which", "this", "that", "these", "those", "it", "its", "their",
        "has", "have", "was", "were", "could", "would", "should",
    }
    _COLUMNS = [
        "passage_id", "document_id", "book_id", "source", "shelf",
        "chapter_title", "text", "citation", "metadata",
    ]

    def __init__(self, db_path: Optional[str] = None):
        state_dir = os.environ.get("TINY_EXPERT_STATE_DIR") or os.path.join(
            os.path.expanduser("~"), ".local", "share", "tiny-expert-system"
        )
        self.db_path = os.fspath(db_path) if db_path is not None else os.path.join(state_dir, "epistemic_fts.db")
        self._lock = threading.RLock()
        self._memory_connection = None
        if self.db_path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_connection.row_factory = sqlite3.Row
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        with self._lock:
            con = self._memory_connection or sqlite3.connect(self.db_path, timeout=10.0)
            con.row_factory = sqlite3.Row
            try:
                with con:
                    yield con
            finally:
                if con is not self._memory_connection:
                    con.close()

    def close(self):
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None

    def _init_db(self):
        with self._get_connection() as con:
            columns = [r["name"] for r in con.execute("PRAGMA table_info(epistemic_passages)")]
            if columns and columns != self._COLUMNS:
                # The old cache indexed authority strings and omitted metadata.
                con.execute("DROP TABLE epistemic_passages")
            con.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS epistemic_passages USING fts5(
                    passage_id UNINDEXED,
                    document_id UNINDEXED,
                    book_id UNINDEXED,
                    source UNINDEXED,
                    shelf UNINDEXED,
                    chapter_title UNINDEXED,
                    text,
                    citation UNINDEXED,
                    metadata UNINDEXED,
                    tokenize = 'unicode61 remove_diacritics 2'
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS epistemic_snapshot_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    snapshot_hash TEXT NOT NULL,
                    row_count INTEGER NOT NULL
                )
            """)

    @staticmethod
    def prepare_passage(passage: Dict[str, Any]) -> Dict[str, Any]:
        """Give a passage stable identities without discarding supplied metadata."""
        p = dict(passage)
        if not isinstance(p.get("text"), str) or not p["text"].strip():
            raise ValueError("A passage must contain non-empty text.")
        p.setdefault("shelf", "general")
        p.setdefault("source", "Untitled local document")
        identity = f"{p['shelf']}\n{p['source']}"
        p["document_id"] = p.get("document_id") or p.get("book_id") or (
            "doc_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        )
        p["content_hash"] = p.get("content_hash") or hashlib.sha256(p["text"].encode("utf-8")).hexdigest()
        p["passage_id"] = p.get("passage_id") or hashlib.sha256(
            f"{p['document_id']}\n{p['text']}".encode("utf-8")
        ).hexdigest()
        p.setdefault("verification_status", "unverified")
        p.setdefault("review_status", "unreviewed")
        return p

    @classmethod
    def _rows(cls, passages: List[Dict[str, Any]]):
        # Last occurrence wins if the same passage is supplied more than once.
        prepared = {p["passage_id"]: p for p in map(cls.prepare_passage, passages)}
        return [
            (p["passage_id"], p["document_id"], p.get("book_id"), p.get("source"),
             p.get("shelf"), p.get("chapter_title"), p["text"], p.get("citation"),
             json.dumps(p, ensure_ascii=False, sort_keys=True))
            for p in prepared.values()
        ]

    @staticmethod
    def _insert_rows(con, rows):
        con.executemany("""
            INSERT INTO epistemic_passages
            (passage_id, document_id, book_id, source, shelf, chapter_title, text, citation, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

    def index_passage(self, text: str, source: str, shelf: str,
                      book_id: Optional[str] = None, chapter_title: Optional[str] = None,
                      citation: Optional[str] = None, **metadata):
        self.index_bulk_passages([{
            **metadata, "text": text, "source": source, "shelf": shelf,
            "book_id": book_id, "chapter_title": chapter_title, "citation": citation,
        }])

    def index_bulk_passages(self, passages: List[Dict[str, Any]]):
        """Idempotently upsert passages; use replace_document for a new revision."""
        rows = self._rows(passages)
        with self._get_connection() as con:
            con.executemany("DELETE FROM epistemic_passages WHERE passage_id = ?", [(r[0],) for r in rows])
            self._insert_rows(con, rows)

    def replace_document(self, document_id: str, passages: List[Dict[str, Any]]):
        """Atomically remove every old passage of a document and insert its revision."""
        if not document_id:
            raise ValueError("document_id is required for replacement.")
        rows = self._rows([{**p, "document_id": document_id} for p in passages])
        with self._get_connection() as con:
            con.execute("DELETE FROM epistemic_passages WHERE document_id = ?", (document_id,))
            self._insert_rows(con, rows)

    def replace_all_passages(self, passages: List[Dict[str, Any]]):
        """Synchronize the complete source snapshot in one transaction (skipping rewrite if content-hash is identical)."""
        rows = self._rows(passages)
        snap_hash = hashlib.sha256(
            "\n".join(f"{r[0]}:{hashlib.sha256(r[8].encode('utf-8')).hexdigest()}" for r in rows).encode("utf-8")
        ).hexdigest()
        with self._get_connection() as con:
            meta = con.execute("SELECT snapshot_hash, row_count FROM epistemic_snapshot_meta WHERE id = 1").fetchone()
            if meta and meta["snapshot_hash"] == snap_hash and meta["row_count"] == len(rows):
                actual_count = int(con.execute("SELECT count(*) FROM epistemic_passages").fetchone()[0])
                if actual_count == len(rows):
                    return
            con.execute("DELETE FROM epistemic_passages")
            self._insert_rows(con, rows)
            con.execute(
                "INSERT OR REPLACE INTO epistemic_snapshot_meta (id, snapshot_hash, row_count) VALUES (1, ?, ?)",
                (snap_hash, len(rows)),
            )

    @classmethod
    def query_tokens(cls, query: str, shelf: Optional[str] = None) -> List[str]:
        shelf_terms = set(re.findall(r"\w+", (shelf or "").replace("_", " ").casefold()))
        return list(dict.fromkeys(
            t for t in re.findall(r"\w+", (query or "").casefold())
            if len(t) > 1 and t not in cls.STOPWORDS and t not in shelf_terms
        ))

    def search(self, query: str, shelf: Optional[str] = None, limit: int = 5, *,
               document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not isinstance(query, str) or len(query) > 8192:
            raise ValueError("Query must be text no longer than 8192 characters")
        if type(limit) is not int or limit > 1000:
            raise ValueError("Result limit must be an integer no greater than 1000")
        tokens = self.query_tokens(query, shelf)[:64]
        if not tokens or limit <= 0:
            return []
        fts_query = " OR ".join(f'"{token}"' for token in tokens)
        sql = """
            SELECT metadata, snippet(epistemic_passages, 6, '<mark>', '</mark>', '...', 32) AS snippet_text,
                   bm25(epistemic_passages) AS bm25_rank
            FROM epistemic_passages WHERE epistemic_passages MATCH ?
        """
        params: List[Any] = [fts_query]
        if shelf is not None:
            sql += " AND shelf = ?"
            params.append(shelf)
        if document_id is not None:
            sql += " AND document_id = ?"
            params.append(document_id)
        sql += " ORDER BY bm25_rank ASC, passage_id ASC LIMIT ?"
        params.append(int(limit))
        with self._get_connection() as con:
            results = []
            for row in con.execute(sql, params):
                record = json.loads(row["metadata"])
                record["snippet"] = row["snippet_text"]
                record["bm25_rank"] = row["bm25_rank"]
                results.append(record)
            return results

    def get_total_passages_count(self) -> int:
        with self._get_connection() as con:
            return int(con.execute("SELECT count(*) FROM epistemic_passages").fetchone()[0])
