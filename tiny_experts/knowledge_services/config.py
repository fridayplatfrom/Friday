"""Explicit resource budgets. These are local limits, not throughput promises."""
from dataclasses import dataclass, asdict
from ..knowledge_core.store import CoreError


@dataclass(frozen=True)
class Limits:
    stream_bytes: int = 2 * 1024**3
    extracted_bytes: int = 256 * 1024**2
    chunk_characters: int = 4096
    max_segments: int = 100000
    model_input_tokens: int = 384
    retrieval_candidates: int = 100
    embedding_batch: int = 32
    audio_chunk_seconds: int = 60
    audio_duration_seconds: int = 14400
    max_transcript_segments: int = 5000
    crawl_response_bytes: int = 2 * 1024**2
    crawl_pages: int = 1000
    crawl_depth: int = 5
    crawl_frontier: int = 10000
    worker_timeout_seconds: int = 1800

    def __post_init__(self):
        for key, value in asdict(self).items():
            if type(value) is not int or value <= 0:
                raise CoreError(f'{key} must be a positive integer')
        if not 256 <= self.chunk_characters <= 16384:
            raise CoreError('chunk_characters must be 256..16384')
        if self.embedding_batch > 256 or self.retrieval_candidates > 1000:
            raise CoreError('Invalid retrieval batch/candidate budget')
        if self.crawl_depth > 20 or self.audio_chunk_seconds > 300:
            raise CoreError('Invalid crawl/audio processing budget')
        if self.worker_timeout_seconds>86340:
            raise CoreError('Worker timeout must leave room for a bounded lease')
        if self.extracted_bytes > self.stream_bytes:
            raise CoreError('Extracted-text budget cannot exceed streaming-asset budget')


SCHEMA = '''
CREATE TABLE IF NOT EXISTS service_schema(version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS text_chunks(
 tenant TEXT NOT NULL, revision_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
 char_start INTEGER NOT NULL, char_end INTEGER NOT NULL,
 byte_start INTEGER NOT NULL, byte_end INTEGER NOT NULL, sha256 TEXT NOT NULL,
 PRIMARY KEY(tenant,revision_id,ordinal));
CREATE INDEX IF NOT EXISTS chunks_range ON text_chunks(tenant,revision_id,char_start,char_end);
CREATE TABLE IF NOT EXISTS vectors(
 tenant TEXT NOT NULL, model_id TEXT NOT NULL, segment_id TEXT NOT NULL,
 revision_id TEXT NOT NULL, text_hash TEXT NOT NULL, dimensions INTEGER NOT NULL,
 embedding BLOB NOT NULL, indexed_at TEXT NOT NULL,
 PRIMARY KEY(tenant,model_id,segment_id));
CREATE INDEX IF NOT EXISTS vectors_revision ON vectors(tenant,revision_id);
CREATE TABLE IF NOT EXISTS operations(
 tenant TEXT NOT NULL, id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
 idempotency_key TEXT NOT NULL, payload_hash TEXT NOT NULL, state TEXT NOT NULL,
 attempts INTEGER NOT NULL, max_attempts INTEGER NOT NULL, available_at REAL NOT NULL,
 lease_token TEXT, lease_until REAL, result TEXT, error TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(tenant,id), UNIQUE(tenant,idempotency_key));
CREATE INDEX IF NOT EXISTS operation_queue ON operations(tenant,state,available_at,lease_until);
CREATE TABLE IF NOT EXISTS crawl_config(
 tenant TEXT NOT NULL, website_id TEXT NOT NULL, data TEXT NOT NULL,
 PRIMARY KEY(tenant,website_id));
CREATE TABLE IF NOT EXISTS crawl_frontier(
 tenant TEXT NOT NULL, website_id TEXT NOT NULL, url TEXT NOT NULL,
 depth INTEGER NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 available_at REAL NOT NULL, lease_token TEXT, lease_until REAL,
 revision_id TEXT, etag TEXT, modified TEXT, error TEXT, status_code INTEGER,
 PRIMARY KEY(tenant,website_id,url));
CREATE INDEX IF NOT EXISTS crawl_queue ON crawl_frontier(tenant,website_id,state,available_at);
CREATE TABLE IF NOT EXISTS crawl_hosts(
 tenant TEXT NOT NULL, website_id TEXT NOT NULL, next_request REAL NOT NULL,
 PRIMARY KEY(tenant,website_id));
'''
