"""Source identities, versioned multimodal evidence, and incremental retrieval."""
from collections import Counter
from pathlib import Path
import math
import re
from .store import CoreError, AccessDenied, digest, dumps, now, stable_id, text, UNAVAILABLE

USES = frozenset({'store','retrieve','train','redistribute'})
DEPENDENCIES = frozenset({'derived_from','segment_of','uses','trained_on','evaluates','model_for','deployment_of'})


def rights_policy(rights):
    if not isinstance(rights,dict) or set(rights) - USES or any(type(v) is not bool for v in rights.values()):
        raise CoreError('Rights must explicitly map allowed uses to booleans')
    result={use:rights.get(use,False) for use in USES}
    if not result['store']:
        raise AccessDenied('Storing source content has not been permitted')
    return result


class Sources:
    def register_source(self, source_key, title, *, source_type='book', language='en',
                        edition_label=None, family_id=None, metadata=None, concept_ids=(), work_id=None, edition_id=None):
        text(source_key,'source_key',384);text(title,'title',1024);text(language,'language',32)
        with self.transaction():
            existing=self.maybe('source:'+source_key)
            if existing:
                return existing['id']
            concepts=[self.get(cid,'concept')['id'] for cid in concept_ids]
            if edition_id:
                ed=self.get(edition_id,'edition')
                edition=ed['id'];work=ed['data']['work_id']
                if work_id and self.get(work_id,'work')['id']!=work:
                    raise CoreError('Edition does not belong to supplied work')
                if language!=ed['data']['language']:
                    raise CoreError('Artifact language differs from edition')
            else:
                work=self.get(work_id,'work')['id'] if work_id else self._new('work',{
                    'title':title,'source_type':source_type,'metadata':metadata or {},'review_state':'unreviewed'})
                edition=self._new('edition',{'work_id':work,'language':language,
                              'edition_label':edition_label,'review_state':'unreviewed'})
            artifact=self._new('artifact',{'edition_id':edition,'work_id':work,'title':title,
                           'family_id':family_id or work,'language':language,'current_revision':None,
                           'source_key':source_key},alias='source:'+source_key)
            self._edge(edition,'edition_of',work);self._edge(artifact,'representation_of',edition)
            for cid in concepts:
                self.link(work,'about',cid)
            return artifact

    def ingest(self, artifact, raw, *, media_type='text/plain', extracted_text=None,
               rights, license_note, concept_ids=(), extraction_method='direct-utf8',
               metadata=None, parent_revisions=(), chunk_words=180, overlap=30):
        policy=rights_policy(rights);text(license_note,'license_note',4096)
        text(media_type,'media_type',128);text(extraction_method,'extraction_method',256)
        if type(chunk_words) is not int or not 1<=chunk_words<=4096 or type(overlap) is not int or not 0<=overlap<chunk_words:
            raise CoreError('Invalid chunk budget')
        if not isinstance(raw,bytes) or not raw or len(raw)>20*1024*1024:
            raise CoreError('Source must contain 1 byte to 20 MiB')
        if extracted_text is None and media_type in {'text/plain','text/markdown','text/csv','text/x-python'}:
            try:
                extracted_text=raw.decode('utf-8-sig')
            except UnicodeError as exc:
                raise CoreError('Source is not UTF-8; use an explicit extractor') from exc
        if extracted_text is not None:
            if not isinstance(extracted_text,str) or '\x00' in extracted_text or not extracted_text.strip() or len(extracted_text.encode())>8*1024*1024:
                raise CoreError('Extracted text must contain 1 character to 8 MiB without NUL')
        with self.transaction():
            a=self.get(artifact,'artifact'); artifact=a['id']
            concepts=[self.get(c,'concept')['id'] for c in concept_ids]
            parents=[self.get(p,'revision')['id'] for p in parent_revisions]
            for parent in parents:
                if self.get(parent)['data']['artifact_id']==artifact:
                    raise CoreError('A derivative must use a separate artifact from its parent')
                self.require_source_use(parent,'retrieve')
                pp=self.get(parent)['data']['rights']
                if any(policy[use] and not pp.get(use,False) for use in USES):
                    raise AccessDenied('A derivative cannot increase its source permissions')
            raw_sha=self.put_asset(raw)
            text_sha=self.put_asset(extracted_text.encode()) if extracted_text is not None else None
            key=dumps([artifact,raw_sha,text_sha,extraction_method,parents,metadata or {}])
            revision=stable_id('revision',key)
            prior=self.maybe(revision)
            if prior:
                if prior['status']!='active' or a['data']['current_revision']!=revision:
                    raise CoreError('This historical revision cannot be silently reactivated')
                if prior['data']['rights']!=policy:
                    raise CoreError('Use set_rights to change an existing revision policy')
                for cid in concepts:
                    self.link(revision,'about',cid)
                    for edge in self.edges(revision,relation='segment_of',reverse=True):
                        self.link(edge['src'],'about',cid)
                return {'revision_id':revision,'artifact_id':artifact,'idempotent':True,
                        'segments':len(self.edges(revision,relation='segment_of',reverse=True))}
            old=a['data']['current_revision']
            if old:
                self._invalidate(old,'superseded')
            info={'artifact_id':artifact,'family_id':a['data']['family_id'],'sha256':raw_sha,
                  'text_sha256':text_sha,'media_type':media_type,'rights':policy,'license_note':license_note,
                  'language':a['data']['language'],'title':a['data']['title'],
                  'acquired_at':now(),'extraction_method':extraction_method,'metadata':metadata or {},
                  'stage':'extracted' if text_sha else 'acquired','review_state':'unreviewed'}
            self._new('revision',info,id=revision)
            self._edge(revision,'revision_of',artifact)
            for parent in parents:
                self._edge(revision,'derived_from',parent)
            if not concepts:
                concepts=[c['id'] for c in self.concepts_for(a['data']['work_id'])]
            for cid in concepts:
                self.link(revision,'about',cid)
            count=0
            if extracted_text is not None:
                words=list(re.finditer(r'\S+',extracted_text));start=0
                while start<len(words):
                    end=min(start+chunk_words,len(words))
                    self.add_segment(revision,{'type':'text','start':words[start].start(),'end':words[end-1].end()},concept_ids=concepts)
                    count+=1
                    if end==len(words): break
                    start=end-overlap
                observed=Counter(); first={}
                for match in re.finditer(r'[^\W_]+(?:[-’\'][^\W_]+)*',extracted_text,re.UNICODE):
                    form=match.group().casefold()
                    if len(form)<=128:
                        observed[form]+=1;first.setdefault(form,match.start())
                    if len(observed)>100000:
                        raise CoreError('Source exceeds vocabulary observation budget')
                self.db.executemany('INSERT INTO occurrences VALUES (?,?,?,?,?,?)',
                    [(self.tenant,revision,info['language'],f,n,first[f]) for f,n in observed.items()])
                self._change(revision,data={**info,'stage':'indexed'})
            self._change(artifact,data={**a['data'],'current_revision':revision})
            self._audit('source_ingested',revision,segment_count=count,raw_sha256=raw_sha,previous=old)
            return {'revision_id':revision,'artifact_id':artifact,'segments':count,'idempotent':False,
                    'review_state':'unreviewed','neural_training_started':False}

    def import_text(self, source_key, title, body, *, rights, license_note, concepts=(), language='en', family_id=None):
        if not isinstance(body,str): raise CoreError('body must be text')
        with self.transaction():
            artifact=self.register_source(source_key,title,language=language,family_id=family_id,concept_ids=concepts)
            return self.ingest(artifact,body.encode(),rights=rights,license_note=license_note,concept_ids=concepts)

    def require_source_use(self, revision, use, *, historical=False, _seen=None):
        if use not in USES: raise CoreError('Unknown source use')
        row=self.get(revision,'revision');id=row['id']
        seen=set() if _seen is None else _seen
        if id in seen: return row
        seen.add(id)
        allowed_history=historical and self.curator and use=='retrieve' and row['status']=='superseded'
        if row['status']!='active' and not allowed_history:
            raise AccessDenied('Source revision is unavailable')
        if not row['data']['rights'].get(use,False):
            raise AccessDenied('Source permission does not allow '+use)
        for edge in self.edges(id,relation='derived_from'):
            self.require_source_use(edge['dst'],use,historical=historical,_seen=seen)
        return row

    def add_segment(self, revision, selector, *, concept_ids=(), metadata=None):
        with self.transaction():
            row=self.get(revision,'revision')
            if row['status']!='active': raise CoreError('Cannot segment an inactive revision')
            content=self._select(row,selector)
            id=stable_id('segment',dumps([row['id'],selector]))
            if self.maybe(id): return id
            self._new('segment',{'revision_id':row['id'],'selector':selector,'metadata':metadata or {},
                                'review_state':'unreviewed'},id=id)
            self._edge(id,'segment_of',row['id'])
            for cid in concept_ids:
                self.link(id,'about',cid)
            if content is not None:
                self.db.execute('INSERT INTO passages VALUES (?,?,?,?)',(self.tenant,id,row['id'],content))
            return id

    def _select(self, revision, selector):
        if not isinstance(selector,dict) or 'type' not in selector:
            raise CoreError('Typed selector required')
        data=revision['data'];kind=selector['type']
        if kind=='text':
            if set(selector)-{'type','start','end'}: raise CoreError('Unknown text-selector fields')
            if not data.get('text_sha256'): raise CoreError('Source has no extracted text')
            body=self.read_asset(data['text_sha256']).decode('utf-8')
            start,end=selector.get('start'),selector.get('end')
            if type(start) is not int or type(end) is not int or not 0<=start<end<=len(body):
                raise CoreError('Invalid text offsets')
            return body[start:end]
        if kind=='image_region':
            if not data['media_type'].startswith('image/'):
                raise CoreError('Image region requires image source')
            width,height=data['metadata'].get('width'),data['metadata'].get('height')
            xywh=selector.get('xywh')
            if not isinstance(xywh,list) or len(xywh)!=4 or not all(type(x) is int for x in xywh):
                raise CoreError('Pixel coordinates must be four integers')
            x,y,w,h=xywh
            if type(width) is not int or type(height) is not int or not (x>=0 and y>=0 and w>0 and h>0 and x+w<=width and y+h<=height):
                raise CoreError('Image region outside declared dimensions')
        elif kind=='time':
            if not data['media_type'].startswith(('audio/','video/')):
                raise CoreError('Time selector requires audio/video')
            start,end,duration=selector.get('start_seconds'),selector.get('end_seconds'),data['metadata'].get('duration_seconds')
            if not all(type(x) in (int,float) and math.isfinite(x) for x in (start,end,duration)) or not 0<=start<end<=duration:
                raise CoreError('Time selector outside declared duration')
        else:
            raise CoreError('Unsupported selector; do not fabricate page/region/time locations')
        self.read_asset(data['sha256'])
        return None

    def evidence(self, segment, *, quote=None, historical=False):
        item=self.get(segment,'segment')
        revision=self.require_source_use(item['data']['revision_id'],'retrieve',historical=historical)
        value=self._select(revision,item['data']['selector'])
        self.read_asset(revision['data']['sha256'])
        if quote is not None and (not isinstance(quote,str) or not quote or value is None or quote not in value):
            raise CoreError('Evidence quotation does not occur in the anchored text')
        return {'segment_id':item['id'],'revision_id':revision['id'],
                'source_sha256':revision['data']['sha256'],'text_sha256':revision['data'].get('text_sha256'),
                'selector':item['data']['selector'],'text':value,'quote':quote,
                'source_consistency':True,'semantic_support':'not_evaluated','review_state':revision['data']['review_state']}

    def search(self, query, *, concepts=(), revision=None, top_k=5):
        text(query,'query',2048)
        if type(top_k) is not int or not 1<=top_k<=100: raise CoreError('Invalid result budget')
        tokens=list(dict.fromkeys(re.findall(r'\w+',query.casefold())))[:32]
        if not tokens: return []
        cids={self.get(c,'concept')['id'] for c in concepts}
        with self.lock:
            args=[' OR '.join('"'+t+'"' for t in tokens),self.tenant]
            sql='''SELECT p.segment_id,p.revision_id,bm25(passages) rank FROM passages p
                JOIN nodes n ON n.tenant=p.tenant AND n.id=p.revision_id
                WHERE passages MATCH ? AND p.tenant=? AND n.status='active'
                AND json_extract(n.data,'$.rights.retrieve')=1'''
            if revision:
                rev=self.require_source_use(revision,'retrieve');sql+=' AND p.revision_id=?';args.append(rev['id'])
            # Limit only after concept/access filtering; otherwise top-k can lose valid hits.
            rows=self.db.execute(sql+' ORDER BY rank,p.segment_id',args)
            result=[]
            for row in rows:
                if cids and not cids.intersection(e['dst'] for e in self.edges(row['segment_id'],relation='about')):
                    continue
                try:
                    proof=self.evidence(row['segment_id'])
                except (CoreError,OSError,UnicodeError):
                    continue
                result.append({**proof,'rank':row['rank']})
                if len(result)==top_k: break
            return result

    def _invalidate(self, id, status='withdrawn'):
        pending=[id];seen=set()
        while pending:
            node=pending.pop()
            if node in seen: continue
            seen.add(node);r=self.get(node)
            new=status if node==id else 'affected'
            if r['status'] not in {'withdrawn','deleted'}:
                self._change(node,status=new)
            if r['kind']=='revision':
                self.db.execute('DELETE FROM passages WHERE tenant=? AND revision_id=?',(self.tenant,node))
                self.db.execute('DELETE FROM occurrences WHERE tenant=? AND revision_id=?',(self.tenant,node))
            for edge in self.edges(node,reverse=True):
                if edge['relation'] in DEPENDENCIES: pending.append(edge['src'])
        self._audit('lineage_invalidated',id,affected_count=len(seen),reason=status)
        return sorted(seen)

    def withdraw_source(self, revision, *, reason):
        self.require_curator();text(reason,'reason',1024)
        with self.transaction():
            row=self.get(revision,'revision')
            affected=self._invalidate(row['id'])
            self._audit('withdrawal_reason',row['id'],reason=reason)
            return affected

    def set_rights(self, revision, rights, *, reason):
        self.require_curator();text(reason,'reason',1024)
        if not isinstance(rights,dict) or set(rights)-USES or any(type(v) is not bool for v in rights.values()):
            raise CoreError('Explicit rights dictionary required')
        policy={use:rights.get(use,False) for use in USES}
        with self.transaction():
            row=self.get(revision,'revision')
            # Any changed rights invalidate released downstream data and models.
            if row['data']['rights']!=policy:
                for edge in self.edges(row['id'],reverse=True):
                    if edge['relation'] in DEPENDENCIES and self.get(edge['src'])['kind']!='segment':
                        self._invalidate(edge['src'],'affected')
                self._change(row['id'],data={**row['data'],'rights':policy})
                if not policy['store']:
                    self._invalidate(row['id'])
                self._audit('rights_changed',row['id'],reason=reason)

    def add_claim(self, subject, predicate, value, evidence_ids, *, context=None, units=None):
        self.get(subject);text(predicate,'predicate',128)
        if not evidence_ids: raise CoreError('A claim needs source evidence')
        with self.transaction():
            for sid in evidence_ids: self.evidence(sid)
            id=self._new('claim',{'subject_id':subject,'predicate':predicate,'value':value,
                         'context':context or {},'units':units,'review_state':'proposed'})
            for sid in evidence_ids: self._edge(id,'derived_from',sid)
            return id

    def review(self, id, *, decision, note):
        self.require_curator();text(note,'review note',4096)
        if decision not in {'accepted','rejected'}: raise CoreError('Invalid review decision')
        with self.transaction():
            row=self.get(id)
            if row['kind'] not in {'concept','lexical_sense','translation','revision','segment','claim','annotation'} or row['status']!='active':
                raise CoreError('Record cannot be reviewed by this operation')
            if row['kind']=='revision': self.require_source_use(id,'retrieve')
            if row['kind']=='segment': self.evidence(id)
            state={'decision':decision,'reviewer':self.actor,'at':now(),'note':note,
                   'identity_authenticated_by':'trusted_local_application','independent_truth_verified':False}
            if decision=='rejected' and row['data'].get('review_state')=='accepted':
                for edge in self.edges(row['id'],reverse=True):
                    if edge['relation'] in DEPENDENCIES:
                        self._invalidate(edge['src'],'affected')
            self._change(id,data={**row['data'],'review_state':decision,'review':state})
            self._audit('review_recorded',id,decision=decision)

    def source_ancestry(self, revision):
        todo=[self.get(revision,'revision')['id']];seen=set()
        while todo:
            current=todo.pop()
            if current in seen: continue
            seen.add(current)
            todo.extend(e['dst'] for e in self.edges(current,relation='derived_from'))
        return [self.get(id,'revision') for id in sorted(seen)]

    def add_structure(self, revision, structure_type, representation, *, segment_id=None, metadata=None):
        """Preserve tables/formulae/code structures as proposed annotations.

        This does not claim a layout/table/equation parser produced the structure.
        A caller must record its extractor and review the result separately.
        """
        source=self.require_source_use(revision,'retrieve')
        if structure_type not in {'table','equation','code'} or not isinstance(representation,dict):
            raise CoreError('Supported structured representation required')
        if structure_type=='table':
            headers,rows=representation.get('headers'),representation.get('rows')
            if not isinstance(headers,list) or not headers or not all(isinstance(h,str) for h in headers) or not isinstance(rows,list):
                raise CoreError('Table requires headers and rows')
            if len(rows)>10000 or any(not isinstance(row,list) or len(row)!=len(headers) for row in rows):
                raise CoreError('Table row widths do not match the headers')
            if not isinstance(representation.get('units',{}),dict):raise CoreError('Table units must be a column map')
        elif structure_type=='equation':
            text(representation.get('original'),'original equation',4096)
            if not isinstance(representation.get('symbols'),dict) or not isinstance(representation.get('assumptions'),list):
                raise CoreError('Equation symbols and assumptions are required')
        else:
            text(representation.get('language'),'code language',128)
            text(representation.get('repository_revision'),'repository revision',256)
            text(representation.get('path'),'repository file path',1024)
        with self.transaction():
            if segment_id and self.evidence(segment_id)['revision_id']!=source['id']:
                raise CoreError('Structure anchor belongs to another revision')
            id=self._new('entity',{'name':structure_type,'entity_type':structure_type,
                'representation':representation,'metadata':metadata or {},'review_state':'proposed'})
            self._edge(id,'derived_from',segment_id or source['id'])
            return id

    def purge_source(self, revision, *, reason):
        """Withdraw content and derived source bytes where not shared by other records.

        IDs, hashes and minimal audit history remain. Model releases are marked
        affected, not magically unlearned. Backups are outside this local purge.
        """
        self.require_curator();text(reason,'reason',1024)
        with self.transaction():
            root=self.get(revision,'revision')
            affected=self._invalidate(root['id'])
            candidates=set()
            for id in affected:
                row=self.get(id)
                if row['kind']=='revision':
                    candidates.update(x for x in (row['data'].get('sha256'),row['data'].get('text_sha256')) if x)
                    self._change(id,data={**row['data'],'metadata':{},'title':'[purged source]','review_state':'withdrawn'},status='deleted')
                elif row['kind']=='segment':
                    self._change(id,data={'revision_id':row['data']['revision_id'],
                        'selector':row['data']['selector'],'metadata':{},'review_state':'withdrawn'},status='deleted')
                elif row['kind'] in {'annotation','claim','translation','entity'}:
                    self._change(id,data={'purged':True,'original_data_hash':digest(dumps(row['data']).encode())},status='deleted')
                self.db.execute('DELETE FROM history WHERE tenant=? AND node_id=?',(self.tenant,id))
            # Content-addressed blobs may be shared by a different allowed source.
            referenced=set()
            for row in self.iter_records('revision',include_inactive=True):
                if row['status']!='deleted':
                    referenced.update(x for x in (row['data'].get('sha256'),row['data'].get('text_sha256')) if x)
            # Do not unlink before committing: a later rollback must not break a live revision.
            removable=sorted(candidates-referenced)
            self._audit('purge_requested',root['id'],reason=reason,retained_shared_blobs=len(candidates&referenced))
        deleted=[]
        # Recheck after metadata commit under a fresh writer lock. Another source
        # could have acquired the same content between the two transactions.
        with self.transaction():
            live=set()
            for kind in ('revision','dataset','model'):
                for record in self.iter_records(kind,include_inactive=True):
                    if record['status']!='deleted':
                        live.update(record['data'].get(k) for k in
                                    ('sha256','text_sha256','manifest_sha256','weights_sha256')
                                    if record['data'].get(k))
            for sha in removable:
                path=self.asset_root/sha
                if sha not in live and path.exists() and not path.is_symlink():
                    path.unlink();deleted.append(sha)
            self._audit('content_purged',root['id'],deleted_blob_count=len(deleted))
        return {'affected':affected,'deleted_blob_hashes':deleted,'model_unlearning_performed':False,
                'backups_purged':False,'identity_and_audit_metadata_retained':True}
