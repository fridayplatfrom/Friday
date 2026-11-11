"""Streaming immutable assets and incremental, byte-addressed text ingestion.

The old small-byte API remains bounded. Large files use put_stream/ingest_stream;
passage reads never materialize a complete large text document in memory.
"""
from collections import Counter
from pathlib import Path
import codecs
import hashlib
import io
import os
import re
import tempfile
from ..knowledge_core.store import CoreError, AccessDenied, dumps, digest, now, stable_id, text
from ..knowledge_core.sources import rights_policy, USES


class Streaming:
    def _asset_path(self, sha):
        if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise CoreError('Invalid asset checksum')
        path = self.asset_root / sha
        if path.is_symlink() or not path.is_file():
            raise CoreError('Missing or linked asset')
        if path.stat().st_size > self.limits.stream_bytes:
            raise CoreError('Asset exceeds configured streaming budget')
        return path

    def verify_asset(self, sha):
        path = self._asset_path(sha)
        stat = path.stat()
        key = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if self._verified_assets.get(sha) != key:
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    h.update(block)
            after = path.stat()
            after_key = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            if h.hexdigest() != sha or after_key != key:
                raise CoreError('Asset checksum mismatch or concurrent change')
            self._verified_assets[sha] = key
        return path

    def put_stream(self, stream, *, max_bytes=None, cancelled=lambda: False):
        budget = self.limits.stream_bytes if max_bytes is None else max_bytes
        if type(budget) is not int or not 0 < budget <= self.limits.stream_bytes:
            raise CoreError('Invalid streaming byte budget')
        h = hashlib.sha256(); size = 0; temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.asset_root, prefix='.incoming-', delete=False) as out:
                temporary = Path(out.name)
                while True:
                    if cancelled(): raise CoreError('Operation cancelled')
                    chunk = stream.read(min(1024*1024, budget+1-size))
                    if not isinstance(chunk, bytes): raise CoreError('Binary stream required')
                    if not chunk: break
                    size += len(chunk)
                    if size > budget: raise CoreError('Streaming asset byte budget exceeded')
                    h.update(chunk); out.write(chunk)
                out.flush(); os.fsync(out.fileno())
            if not size: raise CoreError('Empty source')
            sha = h.hexdigest(); target = self.asset_root / sha
            try:
                # Same-filesystem atomic publish, never overwrite an existing blob.
                os.link(temporary, target)
            except FileExistsError:
                self.verify_asset(sha)
            target.chmod(0o600)
            return {'sha256': sha, 'bytes': size}
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)

    def _text_parts(self, binary, cancelled):
        decoder = codecs.getincrementaldecoder('utf-8-sig')('strict')
        pending = ''; finished = False; total = 0
        while not finished:
            if cancelled(): raise CoreError('Operation cancelled')
            block = binary.read(65536); finished = not block
            decoded = decoder.decode(block, final=finished)
            if '\x00' in decoded: raise CoreError('Binary NUL in extracted text')
            total += len(decoded.encode('utf-8'))
            if total > self.limits.extracted_bytes:
                raise CoreError('Extracted-text byte budget exceeded')
            pending += decoded
            while len(pending) >= self.limits.chunk_characters or (finished and pending):
                end = min(len(pending), self.limits.chunk_characters)
                if end < len(pending):
                    boundary = max(pending.rfind(' ', 0, end), pending.rfind('\n', 0, end))
                    if boundary >= end//2: end = boundary+1
                yield pending[:end]; pending = pending[end:]

    def ingest_stream(self, artifact, stream, *, rights, license_note,
                      media_type='text/plain', extracted_stream=None, concept_ids=(),
                      metadata=None, parent_revisions=(), extraction_method='stream-utf8-v1',
                      cancelled=lambda: False):
        policy = rights_policy(rights); text(license_note, 'license_note')
        text(media_type, 'media_type', 128); text(extraction_method, 'extraction_method', 256)
        metadata = dict(metadata or {})
        # Parent/access checks happen both before reading and before publication.
        a = self.get(artifact, 'artifact'); artifact = a['id']
        parents = [self.get(p, 'revision')['id'] for p in parent_revisions]
        for p in parents:
            parent = self.require_source_use(p, 'retrieve')
            if parent['data']['artifact_id'] == artifact:
                raise CoreError('Derivative must use a separate artifact')
            if any(policy[u] and not parent['data']['rights'].get(u, False) for u in USES):
                raise AccessDenied('Derivative cannot expand source permissions')
        raw = self.put_stream(stream, cancelled=cancelled)
        textual = media_type in {'text/plain','text/markdown','text/csv','text/x-python'}
        owned = None; text_sha = None; index_file = None; normalized = None
        try:
            if extracted_stream is None and textual:
                owned = self.verify_asset(raw['sha256']).open('rb'); extracted_stream = owned
            if extracted_stream is not None:
                normalized = tempfile.TemporaryFile(); index_file = tempfile.TemporaryFile(mode='w+t', encoding='utf-8')
                cp = bp = count = 0; has_text = False
                for part in self._text_parts(extracted_stream, cancelled):
                    encoded = part.encode('utf-8'); normalized.write(encoded)
                    has_text |= bool(part.strip())
                    index_file.write(dumps([count,cp,cp+len(part),bp,bp+len(encoded),digest(encoded)])+'\n')
                    cp += len(part); bp += len(encoded); count += 1
                    if count > self.limits.max_segments: raise CoreError('Segment count budget exceeded')
                if not has_text: raise CoreError('Extracted text is empty')
                normalized.seek(0)
                text_sha = self.put_stream(normalized, max_bytes=self.limits.extracted_bytes, cancelled=cancelled)['sha256']
                index_file.seek(0)
            concepts = [self.get(c, 'concept')['id'] for c in concept_ids]
            key = dumps([artifact,raw['sha256'],text_sha,extraction_method,parents,metadata])
            rid = stable_id('revision', key)
            with self.transaction():
                for p in parents:
                    parent = self.require_source_use(p, 'retrieve')
                    if any(policy[u] and not parent['data']['rights'].get(u, False) for u in USES):
                        raise AccessDenied('Parent rights changed during ingestion')
                a = self.get(artifact, 'artifact'); previous = a['data']['current_revision']
                prior = self.maybe(rid)
                if prior:
                    if prior['status'] != 'active' or previous != rid or prior['data']['rights'] != policy:
                        raise CoreError('Inactive revision or changed policy cannot be silently reused')
                    for cid in concepts:
                        self.link(rid,'about',cid)
                        for edge in self.edges(rid,relation='segment_of',reverse=True):self.link(edge['src'],'about',cid)
                    return {'revision_id':rid, 'artifact_id':artifact, 'idempotent':True, 'neural_training_started':False}
                if previous: self._invalidate(previous, 'superseded')
                info = {'artifact_id':artifact,'family_id':a['data']['family_id'],
                        'sha256':raw['sha256'],'text_sha256':text_sha,'byte_count':raw['bytes'],
                        'media_type':media_type,'rights':policy,'license_note':license_note,
                        'language':a['data']['language'],'title':a['data']['title'],
                        'acquired_at':now(),'extraction_method':extraction_method,'metadata':metadata,
                        'stage':'indexed' if text_sha else 'acquired','review_state':'unreviewed',
                        'streamed_text':bool(text_sha)}
                self._new('revision', info, id=rid); self._edge(rid, 'revision_of', artifact)
                for p in parents: self._edge(rid, 'derived_from', p)
                concepts = concepts or [c['id'] for c in self.concepts_for(a['data']['work_id'])]
                for cid in concepts: self.link(rid, 'about', cid)
                count = 0
                if index_file:
                    import json
                    previous_character=' '
                    total_text_bytes=self._asset_path(text_sha).stat().st_size
                    with self.verify_asset(text_sha).open('rb') as content:
                        for line in index_file:
                            if cancelled(): raise CoreError('Operation cancelled')
                            ordinal,cs,ce,bs,be,sha = json.loads(line)
                            content.seek(bs); part = content.read(be-bs).decode('utf-8')
                            self.db.execute('INSERT INTO text_chunks VALUES (?,?,?,?,?,?,?,?)',
                                (self.tenant,rid,ordinal,cs,ce,bs,be,sha))
                            self.add_segment(rid, {'type':'text','start':cs,'end':ce}, concept_ids=concepts)
                            counts=Counter();first_offsets={}
                            for match in re.finditer(r'[^\W_]+',part):
                                if len(match.group())>128:continue
                                if match.start()==0 and previous_character.isalnum() and part[0].isalnum():continue
                                if match.end()==len(part) and be<total_text_bytes and part[-1].isalnum():continue
                                word=match.group().casefold();counts[word]+=1;first_offsets.setdefault(word,cs+match.start())
                            previous_character=part[-1:]
                            self.db.executemany('''INSERT INTO occurrences VALUES (?,?,?,?,?,?)
                                ON CONFLICT(tenant,revision_id,language,form) DO UPDATE
                                SET occurrences=occurrences+excluded.occurrences''',
                                [(self.tenant,rid,info['language'],word,n,first_offsets[word]) for word,n in counts.items()])
                            count += 1
                self._change(artifact, data={**a['data'],'current_revision':rid})
                self._audit('stream_ingested', rid, byte_count=raw['bytes'], segment_count=count)
            return {'revision_id':rid,'artifact_id':artifact,'segments':count,'idempotent':False,
                    'review_state':'unreviewed','neural_training_started':False}
        finally:
            for file in (owned, normalized, index_file):
                if file: file.close()

    def _select(self, revision, selector):
        if revision['data'].get('streamed_text') and isinstance(selector,dict) and selector.get('type')=='text':
            if set(selector)-{'type','start','end'}: raise CoreError('Unknown text selector fields')
            start,end = selector.get('start'),selector.get('end')
            if type(start) is not int or type(end) is not int or not 0<=start<end or end-start>262144:
                raise CoreError('Invalid or oversized text selector')
            path = self._asset_path(revision['data']['text_sha256'])
            rows = self.db.execute('''SELECT * FROM text_chunks WHERE tenant=? AND revision_id=?
                AND char_start<? AND char_end>? ORDER BY ordinal''', (self.tenant,revision['id'],end,start)).fetchall()
            if not rows or rows[0]['char_start']>start or rows[-1]['char_end']<end:
                raise CoreError('Text range outside snapshot')
            parts = []; expected = rows[0]['char_start']
            with path.open('rb') as stream:
                for row in rows:
                    if row['char_start'] != expected: raise CoreError('Noncontiguous source chunks')
                    stream.seek(row['byte_start']); raw = stream.read(row['byte_end']-row['byte_start'])
                    if digest(raw)!=row['sha256']: raise CoreError('Source chunk checksum mismatch')
                    part=raw.decode('utf-8'); parts.append(part[max(0,start-row['char_start']):end-row['char_start']])
                    expected=row['char_end']
            return ''.join(parts)
        if isinstance(selector,dict) and selector.get('type') in {'time','image_region'}:
            # Existing validators read bytes only to verify integrity. Keep small
            # assets on their original path; large time selectors are checked here.
            if selector['type']=='time' and revision['data'].get('byte_count',0)>20*1024**2:
                import math
                d=revision['data']; s,e=selector.get('start_seconds'),selector.get('end_seconds'); duration=d['metadata'].get('duration_seconds')
                if not d['media_type'].startswith(('audio/','video/')) or not all(type(x) in (int,float) and math.isfinite(x) for x in (s,e,duration)) or not 0<=s<e<=duration:
                    raise CoreError('Time selector outside duration')
                self.verify_asset(d['sha256']); return None
        return super()._select(revision, selector)

    def evidence(self, segment, *, quote=None, historical=False):
        item=self.get(segment,'segment')
        source=self.require_source_use(item['data']['revision_id'],'retrieve',historical=historical)
        value=self._select(source,item['data']['selector'])
        self.verify_asset(source['data']['sha256'])
        if quote is not None and (not isinstance(quote,str) or not quote or value is None or quote not in value):
            raise CoreError('Evidence quote is absent from source segment')
        return {'segment_id':item['id'],'revision_id':source['id'],'source_sha256':source['data']['sha256'],
                'text_sha256':source['data'].get('text_sha256'),'selector':item['data']['selector'],
                'text':value,'quote':quote,'source_consistency':True,'semantic_support':'not_evaluated',
                'review_state':source['data']['review_state']}

    def _invalidate(self, id, status='withdrawn'):
        affected=super()._invalidate(id,status)
        self.db.executemany('DELETE FROM vectors WHERE tenant=? AND revision_id=?',[(self.tenant,x) for x in affected])
        return affected

    def purge_source(self, revision, *, reason):
        result=super().purge_source(revision,reason=reason)
        with self.transaction():
            for rid in result['affected']:
                self.db.execute('DELETE FROM text_chunks WHERE tenant=? AND revision_id=?',(self.tenant,rid))
                self.db.execute('DELETE FROM vectors WHERE tenant=? AND revision_id=?',(self.tenant,rid))
        self._verified_assets.clear()
        return result

    def iter_pretraining(self,dataset,*,partition='train'):
        """Yield bounded, source-addressed training text; never export test data implicitly."""
        rows=self.export_dataset(dataset,partition=partition)
        revisions=sorted({p['revision_id'] for row in rows for p in row['evidence']})
        dataset_id=self.get(dataset,'dataset')['id']
        for rid in revisions:
            source=self.require_source_use(rid,'train');sha=source['data'].get('text_sha256')
            if not sha:continue
            path=self.verify_asset(sha)
            with path.open('rb') as stream:
                start=0
                for part in self._text_parts(stream,lambda:False):
                    self.require_source_use(rid,'train')
                    yield {'dataset_id':dataset_id,'revision_id':rid,'source_family_id':source['data']['family_id'],
                           'sha256':sha,'partition':partition,'language':source['data']['language'],
                           'text':part,'char_start':start,'char_end':start+len(part),
                           'license_note':source['data']['license_note']}
                    start+=len(part)
