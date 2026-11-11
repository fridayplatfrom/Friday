"""Transactional, tenant-scoped metadata and immutable content storage.

This is an embedded trusted-process API, not an authentication server. A tenant
must come from trusted application configuration, never a source or model output.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid

KINDS = frozenset('concept lexical_entry lexical_sense translation work edition artifact revision segment claim capability entity website page offer annotation dataset training_run model evaluation deployment workflow job'.split())
UNAVAILABLE = frozenset({'withdrawn', 'superseded', 'affected', 'retired', 'deleted'})
MAX_ASSET = 20 * 1024 * 1024


class CoreError(ValueError):
    pass


class AccessDenied(CoreError):
    pass


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, field='value', maximum=4096):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or '\x00' in value:
        raise CoreError(f'{field} must be nonempty text of at most {maximum} characters')
    return value


def stable_id(kind, key):
    return 'urn:expertos:' + kind + ':' + str(uuid.uuid5(uuid.NAMESPACE_URL, 'expertos:' + kind + ':' + key))


SCHEMA = '''
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS nodes (
 tenant TEXT NOT NULL, id TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL,
 status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(tenant,id));
CREATE INDEX IF NOT EXISTS nodes_kind ON nodes(tenant,kind,status);
CREATE TABLE IF NOT EXISTS aliases (
 tenant TEXT NOT NULL, alias TEXT NOT NULL, node_id TEXT NOT NULL,
 PRIMARY KEY(tenant,alias), FOREIGN KEY(tenant,node_id) REFERENCES nodes(tenant,id));
CREATE TABLE IF NOT EXISTS edges (
 tenant TEXT NOT NULL, src TEXT NOT NULL, relation TEXT NOT NULL, dst TEXT NOT NULL,
 data TEXT NOT NULL, PRIMARY KEY(tenant,src,relation,dst),
 FOREIGN KEY(tenant,src) REFERENCES nodes(tenant,id),
 FOREIGN KEY(tenant,dst) REFERENCES nodes(tenant,id));
CREATE INDEX IF NOT EXISTS edges_reverse ON edges(tenant,dst,relation);
CREATE TABLE IF NOT EXISTS audit (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL, at TEXT NOT NULL,
 actor TEXT NOT NULL, action TEXT NOT NULL, node_id TEXT, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS history (
 tenant TEXT NOT NULL, node_id TEXT NOT NULL, version INTEGER NOT NULL,
 data TEXT NOT NULL, status TEXT NOT NULL, PRIMARY KEY(tenant,node_id,version));
CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(
 tenant UNINDEXED, segment_id UNINDEXED, revision_id UNINDEXED, text,
 tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS occurrences (
 tenant TEXT NOT NULL, revision_id TEXT NOT NULL, language TEXT NOT NULL,
 form TEXT NOT NULL, occurrences INTEGER NOT NULL, example_start INTEGER NOT NULL,
 PRIMARY KEY(tenant,revision_id,language,form));
'''


class Store:
    def __init__(self, root, *, tenant='local', actor='local-operator', curator=False):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.tenant = text(tenant, 'tenant', 128)
        self.actor = text(actor, 'actor', 128)
        self.curator = curator is True
        self.lock = threading.RLock()
        self._depth = 0
        self._handlers = {}
        self.runtime_id = str(uuid.uuid4())
        self.db = sqlite3.connect(self.root / 'knowledge.sqlite3', isolation_level=None,
                                  timeout=15, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        # Refuse an unknown schema before issuing any DDL or journal changes.
        if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone():
            versions=self.db.execute('SELECT version FROM schema_version').fetchall()
            if len(versions)!=1 or versions[0][0]!=1:
                self.db.close()
                raise CoreError('Unsupported database schema; do not overwrite it')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA busy_timeout=15000')
        self.db.executescript(SCHEMA)
        with self.transaction():
            versions = self.db.execute('SELECT version FROM schema_version').fetchall()
            if not versions:
                self.db.execute('INSERT INTO schema_version VALUES (1)')
            elif len(versions) != 1 or versions[0][0] != 1:
                raise CoreError('Unsupported database schema; do not overwrite it')
        self.asset_root = self.root / 'assets' / digest(self.tenant.encode())
        self.asset_root.mkdir(parents=True, exist_ok=True)

    def close(self):
        with self.lock:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def transaction(self):
        with self.lock:
            level = self._depth
            self.db.execute('BEGIN IMMEDIATE' if level == 0 else f'SAVEPOINT nested_{level}')
            self._depth += 1
            try:
                yield
                self.db.execute('COMMIT' if level == 0 else f'RELEASE nested_{level}')
            except BaseException:
                self.db.execute('ROLLBACK' if level == 0 else f'ROLLBACK TO nested_{level}')
                if level:
                    self.db.execute(f'RELEASE nested_{level}')
                raise
            finally:
                self._depth -= 1

    def _audit(self, action, node_id=None, **detail):
        self.db.execute('INSERT INTO audit(tenant,at,actor,action,node_id,detail) VALUES (?,?,?,?,?,?)',
                        (self.tenant, now(), self.actor, action, node_id, dumps(detail)))

    def _new(self, kind, data, *, id=None, alias=None, status='active'):
        if kind not in KINDS or not isinstance(data, dict):
            raise CoreError('Unknown record kind or invalid payload')
        encoded = dumps(data)
        if len(encoded.encode()) > 4 * 1024 * 1024:
            raise CoreError('Record exceeds metadata budget')
        id = text(id or 'urn:expertos:' + kind + ':' + str(uuid.uuid4()), 'id', 256)
        at = now()
        self.db.execute('INSERT INTO nodes VALUES (?,?,?,?,?,1,?,?)',
                        (self.tenant, id, kind, encoded, status, at, at))
        if alias:
            self._alias(alias, id)
        self._audit('created', id, kind=kind)
        return id

    def _alias(self, alias, id):
        text(alias, 'alias', 512)
        existing = self.db.execute('SELECT node_id FROM aliases WHERE tenant=? AND alias=?',
                                   (self.tenant, alias)).fetchone()
        if existing and existing[0] != id:
            raise CoreError('Alias already belongs to another object')
        self.db.execute('INSERT OR IGNORE INTO aliases VALUES (?,?,?)', (self.tenant, alias, id))

    def resolve_id(self, id):
        text(id, 'id', 512)
        row = self.db.execute('SELECT node_id FROM aliases WHERE tenant=? AND alias=?',
                               (self.tenant, id)).fetchone()
        return row[0] if row else id

    def get(self, id, kind=None):
        with self.lock:
            id = self.resolve_id(id)
            row = self.db.execute('SELECT * FROM nodes WHERE tenant=? AND id=?', (self.tenant, id)).fetchone()
            if not row or (kind and row['kind'] != kind):
                raise CoreError('Record not found in this tenant or wrong record kind')
            result = dict(row)
            result['data'] = json.loads(result['data'])
            return result

    def maybe(self, id, kind=None):
        try:
            return self.get(id, kind)
        except CoreError:
            return None

    def records(self, kind, *, include_inactive=False, limit=1000, offset=0):
        if kind not in KINDS or type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
            raise CoreError('Invalid record query')
        with self.lock:
            sql = 'SELECT id FROM nodes WHERE tenant=? AND kind=?'
            if not include_inactive:
                sql += " AND status NOT IN ('withdrawn','superseded','affected','retired','deleted')"
            rows = self.db.execute(sql + ' ORDER BY id LIMIT ? OFFSET ?', (self.tenant, kind, limit, offset)).fetchall()
            return [self.get(row[0]) for row in rows]

    def iter_records(self, kind, *, include_inactive=False):
        offset = 0
        while True:
            batch = self.records(kind, include_inactive=include_inactive, offset=offset)
            if not batch:
                break
            yield from batch
            offset += len(batch)

    def _change(self, id, *, data=None, status=None, expected_version=None):
        record = self.get(id)
        if expected_version is not None and expected_version != record['version']:
            raise CoreError('Version conflict: refresh before retrying')
        self.db.execute('INSERT INTO history VALUES (?,?,?,?,?)',
                        (self.tenant, record['id'], record['version'], dumps(record['data']), record['status']))
        self.db.execute('UPDATE nodes SET data=?,status=?,version=version+1,updated_at=? WHERE tenant=? AND id=?',
                        (dumps(record['data'] if data is None else data), status or record['status'],
                         now(), self.tenant, record['id']))
        self._audit('updated', record['id'], previous_version=record['version'], status=status)

    def _edge(self, src, relation, dst, data=None):
        src = self.get(src)['id']; dst = self.get(dst)['id']
        self.db.execute('INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)',
                        (self.tenant, src, relation, dst, dumps(data or {})))

    def edges(self, id, *, relation=None, reverse=False):
        node = self.get(id)
        sql = 'SELECT src,relation,dst,data FROM edges WHERE tenant=? AND ' + ('dst' if reverse else 'src') + '=?'
        args = [self.tenant, node['id']]
        if relation:
            sql += ' AND relation=?'; args.append(relation)
        with self.lock:
            return [{**dict(row), 'data': json.loads(row['data'])} for row in self.db.execute(sql, args)]

    def put_asset(self, raw):
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ASSET:
            raise CoreError('Asset must contain 1 byte to 20 MiB')
        sha = digest(raw)
        path = self.asset_root / sha
        # O_EXCL avoids overwriting an immutable blob. A crash can leave an orphan;
        # it cannot make that blob part of a committed metadata transaction.
        try:
            with path.open('xb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            try:
                path.chmod(0o600)
            except OSError:
                pass
        except FileExistsError:
            if digest(path.read_bytes()) != sha:
                raise CoreError('Existing immutable asset is corrupted')
        return sha

    def read_asset(self, sha):
        if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise CoreError('Invalid asset checksum')
        path = self.asset_root / sha
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ASSET:
            raise CoreError('Missing, linked or oversized asset')
        raw = path.read_bytes()
        if digest(raw) != sha:
            raise CoreError('Asset checksum mismatch')
        return raw

    def require_curator(self):
        if not self.curator:
            raise AccessDenied('Explicit trusted curator context is required')

    def audit_events(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise CoreError('Invalid audit limit')
        with self.lock:
            return [dict(row) for row in self.db.execute(
                'SELECT at,actor,action,node_id,detail FROM audit WHERE tenant=? ORDER BY seq DESC LIMIT ?',
                (self.tenant, limit))]

    def counts(self):
        with self.lock:
            return {row['kind']: row['n'] for row in self.db.execute(
                'SELECT kind,count(*) n FROM nodes WHERE tenant=? GROUP BY kind', (self.tenant,))}


    def backup_to(self, destination):
        """Consistent local backup for a single-tenant database, including blobs."""
        import shutil
        self.require_curator()
        target=Path(destination).resolve()
        if target==self.root or self.root in target.parents or (target.exists() and any(target.iterdir())):
            raise CoreError('Backup destination must be empty and outside the core root')
        if self._depth:raise CoreError('Start backup outside an existing transaction')
        with self.transaction():
            tenants={r[0] for r in self.db.execute('SELECT DISTINCT tenant FROM nodes')}
            if tenants-{self.tenant}:
                raise AccessDenied('Database-wide backup is unavailable from a tenant context when other tenants exist')
            if any(p.is_symlink() for p in self.asset_root.rglob('*')):
                raise CoreError('Asset symlink rejected during backup')
            target.mkdir(parents=True,exist_ok=True)
            # A separate reader can snapshot WAL while this connection holds the
            # writer lease, preventing concurrent source replacement/purge.
            reader=sqlite3.connect(self.root/'knowledge.sqlite3')
            output=sqlite3.connect(target/'knowledge.sqlite3')
            try:reader.backup(output)
            finally:reader.close();output.close()
            dest=target/'assets'/self.asset_root.name
            dest.parent.mkdir(exist_ok=True)
            shutil.copytree(self.asset_root,dest)
        return {'directory':str(target),'schema_version':1,'tenant':self.tenant}
