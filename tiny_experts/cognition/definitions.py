"""Reviewed, multi-source scientific definition registry: no generated citations.

This module stores curator-written paraphrases, not source quotations. It does not
assert scientific consensus and never automatically approves model extractions.
"""
from __future__ import annotations
import json
import secrets
from ..knowledge_core.store import CoreError, AccessDenied, dumps, now, text

SCHEMA='''
CREATE TABLE IF NOT EXISTS concept_definitions (
 tenant TEXT NOT NULL,id TEXT NOT NULL,concept_id TEXT NOT NULL,
 wording TEXT NOT NULL,scope TEXT NOT NULL,evidence TEXT NOT NULL,
 review_state TEXT NOT NULL,review_note TEXT,reviewer TEXT,
 created_at TEXT NOT NULL,PRIMARY KEY(tenant,id));
CREATE INDEX IF NOT EXISTS defs_concept ON concept_definitions(tenant,concept_id,review_state);
'''

class DefinitionLibrary:
    def __init__(self,core):
        self.core=core
        core.db.executescript(SCHEMA)

    def propose(self,concept,wording,*,evidence_ids,scope):
        cid=self.core.get(concept,'concept')['id']
        text(wording,'wording',4096);text(scope,'definition scope',1024)
        if not isinstance(evidence_ids,list) or not 1<=len(evidence_ids)<=20 or len(set(evidence_ids))!=len(evidence_ids):
            raise CoreError('Supply 1..20 distinct evidence segments')
        sources=[]
        for sid in evidence_ids:
            proof=self.core.evidence(sid)
            self.core.require_source_use(proof['revision_id'],'retrieve')
            # Refuse an evidence selector without actual source bytes.
            revision=self.core.get(proof['revision_id'],'revision')
            sources.append({'segment_id':proof['segment_id'],'revision_id':proof['revision_id'],
                'family_id':revision['data']['family_id'],'source_sha256':proof['source_sha256']})
        if len(dumps(sources+[{"wording":wording}]).encode())>16000:raise CoreError('Definition metadata too large')
        ident='definition:'+secrets.token_hex(16)
        with self.core.transaction():
            self.core.db.execute('INSERT INTO concept_definitions VALUES (?,?,?,?,?,?,?,?,?,?)',
                (self.core.tenant,ident,cid,wording,scope,dumps(sources),'proposed',None,None,now()))
            self.core._audit('definition_proposed',cid,definition_id=ident)
        return ident

    def review(self,definition,*,accept,note):
        self.core.require_curator();text(note,'review note',4096)
        if type(accept) is not bool:raise CoreError('Explicit review decision required')
        entry=self.get(definition,include_unreviewed=True)
        if entry['review_state']!='proposed':raise CoreError('Definition already reviewed')
        if accept:
            for e in entry['evidence']:
                r=self.core.require_source_use(e['revision_id'],'retrieve')
                if r['data']['review_state']!='accepted':
                    raise CoreError('Source revision must be reviewed first')
                proof=self.core.evidence(e['segment_id'])
                if proof['source_sha256']!=e['source_sha256']:
                    raise CoreError('Source evidence changed')
        with self.core.transaction():
            self.core.db.execute('UPDATE concept_definitions SET review_state=?,review_note=?,reviewer=? WHERE tenant=? AND id=?',
                ('accepted' if accept else 'rejected',note,self.core.actor,self.core.tenant,definition))
            self.core._audit('definition_reviewed',entry['concept_id'],definition_id=definition,accepted=accept)
        return {'definition_id':definition,'review_state':'accepted' if accept else 'rejected'}

    def get(self,definition,*,include_unreviewed=False):
        row=self.core.db.execute('SELECT * FROM concept_definitions WHERE tenant=? AND id=?',(self.core.tenant,definition)).fetchone()
        if not row:raise CoreError('Definition unavailable')
        if row['review_state']!='accepted' and not include_unreviewed:
            raise AccessDenied('Definition is not accepted')
        entry={'id':row['id'],'concept_id':row['concept_id'],'wording':row['wording'],
            'scope':row['scope'],'review_state':row['review_state'],'reviewer':row['reviewer'],
            'review_note':row['review_note'],'evidence':json.loads(row['evidence'])}
        if row['review_state']=='accepted':
            references=[]
            for e in entry['evidence']:
                revision=self.core.require_source_use(e['revision_id'],'retrieve')
                proof=self.core.evidence(e['segment_id'])
                if proof['source_sha256']!=e['source_sha256']:
                    raise AccessDenied('Definition source changed')
                artifact=self.core.get(revision['data']['artifact_id'],'artifact')
                edition=self.core.get(artifact['data']['edition_id'],'edition')
                work=self.core.get(edition['data']['work_id'],'work')
                references.append({'source_title':work['data']['title'],
                    'edition_label':edition['data'].get('edition_label'),
                    'revision_id':e['revision_id'],'segment_id':e['segment_id'],
                    'selector':proof['selector'],'family_id':e['family_id']})
            entry['references']=references
            entry['independent_book_count']=len(set(e['family_id'] for e in entry['evidence']))
        return entry

    def for_concept(self,concept,*,limit=20):
        cid=self.core.get(concept,'concept')['id']
        if type(limit) is not int or not 1<=limit<=100:raise CoreError('Invalid limit')
        rows=self.core.db.execute('SELECT id FROM concept_definitions WHERE tenant=? AND concept_id=? AND review_state=\'accepted\' ORDER BY created_at,id LIMIT ?',
            (self.core.tenant,cid,limit)).fetchall()
        # A revoked original removes definitions from ordinary retrieval.
        available=[]
        for r in rows:
            try:available.append(self.get(r['id']))
            except (CoreError,AccessDenied):continue
        return available
