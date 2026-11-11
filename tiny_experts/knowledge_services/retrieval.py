"""Persistent model-versioned vectors + lexical retrieval + reciprocal rank fusion.

The embedded backend performs a bounded-memory exact vector scan. It is not an
ANN/distributed serving claim. Permission and ancestry filters precede ranking.
"""
import heapq
import math
import struct
from ..knowledge_core import KnowledgeCore
from ..knowledge_core.store import CoreError, digest, now


def unit_vector(values):
    if not isinstance(values,(list,tuple)) or not 1<=len(values)<=8192:
        raise CoreError('Invalid embedding dimension')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise CoreError('Embedding contains invalid numbers')
    length=math.sqrt(sum(float(v)**2 for v in values))
    if not math.isfinite(length) or length<=1e-12: raise CoreError('Zero or invalid embedding')
    return [float(v)/length for v in values]


class Retrieval:
    def index_semantic(self, *, max_segments=10000, after='', cancelled=lambda:False):
        encoder=self.embedding_provider
        if encoder is None: raise CoreError('Semantic model is not configured')
        if type(max_segments) is not int or not 1<=max_segments<=100000:
            raise CoreError('Invalid index batch budget')
        processed=skipped=visited=0;cursor=after;done=False
        while visited<max_segments:
            with self.lock:
                rows=self.db.execute("SELECT id FROM nodes WHERE tenant=? AND kind='segment' AND status='active' AND id>? ORDER BY id LIMIT ?",
                    (self.tenant,cursor,min(self.limits.embedding_batch,max_segments-visited))).fetchall()
            if not rows:done=True;break
            batch=[]
            for row in rows:
                if cancelled():raise CoreError('Operation cancelled')
                cursor=row[0];visited+=1
                try:proof=self.evidence(cursor)
                except (CoreError,OSError):skipped+=1;continue
                if not proof['text']:skipped+=1;continue
                spans=encoder.chunk_spans(proof['text']) if hasattr(encoder,'chunk_spans') else [(0,len(proof['text']))]
                if not isinstance(spans,list) or not 1<=len(spans)<=128:raise CoreError('Invalid embedding chunk plan')
                selector=proof['selector'];candidates=[]
                for start,end in spans:
                    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(proof['text']):
                        raise CoreError('Embedding chunk outside source')
                    if start==0 and end==len(proof['text']):candidates.append(proof)
                    else:
                        if selector['type']!='text':raise CoreError('Embedding requires text offsets')
                        sid=self.add_segment(proof['revision_id'],{'type':'text','start':selector['start']+start,'end':selector['start']+end},
                            concept_ids=[c['id'] for c in self.concepts_for(proof['segment_id'])],
                            metadata={'embedding_parent_segment':proof['segment_id'],'model_id':encoder.identity})
                        candidates.append(self.evidence(sid))
                for candidate in candidates:
                    sha=digest(candidate['text'].encode())
                    old=self.db.execute('SELECT text_hash FROM vectors WHERE tenant=? AND model_id=? AND segment_id=?',
                                       (self.tenant,encoder.identity,candidate['segment_id'])).fetchone()
                    if old and old[0]==sha:skipped+=1;continue
                    batch.append((candidate,sha))
            for offset in range(0,len(batch),self.limits.embedding_batch):
                subset=batch[offset:offset+self.limits.embedding_batch]
                vectors=encoder.encode_documents([p['text'] for p,_ in subset])
                if len(vectors)!=len(subset):raise CoreError('Embedding output cardinality mismatch')
                normalized=[unit_vector(v) for v in vectors];dimensions={len(v) for v in normalized}
                if len(dimensions)!=1:raise CoreError('Inconsistent embedding dimensions')
                with self.transaction():
                    existing=self.db.execute('SELECT dimensions FROM vectors WHERE tenant=? AND model_id=? LIMIT 1',(self.tenant,encoder.identity)).fetchone()
                    if existing and existing[0]!=next(iter(dimensions)):raise CoreError('Model dimension changed without a new version')
                    if cancelled():raise CoreError('Operation cancelled')
                    for (proof,sha),vector in zip(subset,normalized):
                        self.require_source_use(proof['revision_id'],'retrieve')
                        if self.get(proof['segment_id'])['status']!='active':raise CoreError('Source changed while embedding')
                        self.db.execute('INSERT OR REPLACE INTO vectors VALUES (?,?,?,?,?,?,?,?)',
                            (self.tenant,encoder.identity,proof['segment_id'],proof['revision_id'],sha,len(vector),
                             struct.pack('<'+'f'*len(vector),*vector),now()))
                        processed+=1
        with self.transaction():self._audit('semantic_index_batch',model_id=encoder.identity,indexed=processed,skipped=skipped)
        return {'indexed':processed,'skipped':skipped,'parents_examined':visited,'cursor':cursor,'complete':done,
                'model_id':encoder.identity,'quality_evaluated':False}

    def hybrid_search(self,query,*,concepts=(),revision=None,top_k=5,rerank=True):
        if not isinstance(query,str) or not query.strip() or len(query)>2048 or type(top_k) is not int or not 1<=top_k<=100:
            raise CoreError('Invalid query/result budget')
        budget=max(top_k,self.limits.retrieval_candidates)
        lexical=KnowledgeCore.search(self,query,concepts=concepts,revision=revision,top_k=min(100,budget))
        encoder=self.embedding_provider
        if encoder is None:
            return {'mode':'lexical_only','model_status':'not_configured','results':lexical[:top_k]}
        q=unit_vector(encoder.encode_query(query));cids={self.get(c,'concept')['id'] for c in concepts}
        rid=self.require_source_use(revision,'retrieve')['id'] if revision else None
        heap=[];eligible=0
        args=[self.tenant,encoder.identity]
        sql='''SELECT v.* FROM vectors v JOIN nodes n ON n.tenant=v.tenant AND n.id=v.revision_id
            JOIN nodes s ON s.tenant=v.tenant AND s.id=v.segment_id
            WHERE v.tenant=? AND v.model_id=? AND n.status='active' AND s.status='active'
            AND json_extract(n.data,'$.rights.retrieve')=1'''
        if rid: sql+=' AND v.revision_id=?';args.append(rid)
        with self.lock:
            for row in self.db.execute(sql,args):
                if cids and not cids.intersection(e['dst'] for e in self.edges(row['segment_id'],relation='about')): continue
                try: self.require_source_use(row['revision_id'],'retrieve')
                except CoreError: continue
                if row['dimensions']!=len(q): raise CoreError('Query/index embedding dimension mismatch')
                if len(row['embedding'])!=4*len(q): raise CoreError('Corrupt vector payload')
                v=struct.unpack('<'+'f'*len(q),row['embedding'])
                score=sum(a*b for a,b in zip(q,v))
                if not math.isfinite(score): raise CoreError('Non-finite index score')
                eligible+=1
                item=(score,row['segment_id'],row['text_hash'])
                if len(heap)<budget:heapq.heappush(heap,item)
                elif item>heap[0]:heapq.heapreplace(heap,item)
        ranked=sorted(heap,reverse=True);combined={};scores={}
        for i,p in enumerate(lexical):combined[p['segment_id']]=p;scores[p['segment_id']]=1/(60+i+1)
        for i,(_,sid,sha) in enumerate(ranked):
            try:proof=self.evidence(sid)
            except (CoreError,OSError):continue
            if digest((proof['text'] or '').encode())!=sha:continue
            combined[sid]=proof;scores[sid]=scores.get(sid,0)+1/(60+i+1)
        ids=sorted(combined,key=lambda k:(-scores[k],k))[:budget]
        ranked_scores=None
        if rerank and self.reranker_provider and ids:
            values=self.reranker_provider.scores(query,[combined[k]['text'] for k in ids])
            if len(values)!=len(ids) or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
                raise CoreError('Invalid reranker output')
            ranked_scores=dict(zip(ids,values));ids.sort(key=lambda k:(-ranked_scores[k],k))
        results=[]
        for sid in ids[:top_k]:
            # Recheck source rights and integrity immediately before returning.
            proof=self.evidence(sid)
            results.append({**proof,'retrieval_score':scores[sid],'score_type':'reciprocal_rank_fusion',
                           'rerank_score':ranked_scores[sid] if ranked_scores else None,
                           'embedding_model_id':encoder.identity})
        return {'mode':'hybrid','model_id':encoder.identity,'vector_backend':'embedded_exact_scan',
                'eligible_vectors':eligible,'results':results,'semantic_support':'not_evaluated'}

    def search(self,query,*,concepts=(),revision=None,top_k=5):
        return self.hybrid_search(query,concepts=concepts,revision=revision,top_k=top_k)['results']

    def prune_vector_index(self):
        with self.transaction():
            rows=self.db.execute('SELECT model_id,segment_id,revision_id FROM vectors WHERE tenant=?',(self.tenant,)).fetchall()
            removed=0
            for row in rows:
                try:self.require_source_use(row['revision_id'],'retrieve')
                except CoreError:
                    self.db.execute('DELETE FROM vectors WHERE tenant=? AND model_id=? AND segment_id=?',
                                    (self.tenant,row['model_id'],row['segment_id']));removed+=1
            return {'removed':removed}
