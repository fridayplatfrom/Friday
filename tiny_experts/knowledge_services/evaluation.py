"""Measured task metrics. Supply reviewed held-out examples; no fabricated scores."""
import re
from ..knowledge_core.store import CoreError,now


def word_error_rate(reference,hypothesis):
    """Whitespace-word WER after case folding; punctuation is retained explicitly."""
    if not isinstance(reference,str) or not isinstance(hypothesis,str):raise CoreError('Text required')
    ref=reference.casefold().split();hyp=hypothesis.casefold().split()
    if len(ref)>10000 or len(hyp)>10000:raise CoreError('WER comparison budget exceeded')
    previous=list(range(len(hyp)+1))
    for i,r in enumerate(ref,1):
        row=[i]
        for j,h in enumerate(hyp,1):
            row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(r!=h)))
        previous=row
    errors=previous[-1]
    return {'edit_errors':errors,'reference_words':len(ref),
            'wer':errors/len(ref) if ref else None,'empty_reference':not bool(ref),
            'tokenization':'casefold_then_whitespace; punctuation retained'}


def retrieval_report(core,examples,*,k=5):
    if not isinstance(examples,list) or not examples:raise CoreError('Nonempty reviewed retrieval test set required')
    if type(k) is not int or not 1<=k<=100:raise CoreError('Invalid k')
    reciprocals=[];recalls=[];ids=set()
    for item in examples:
        if not isinstance(item,dict) or item.get('reviewed') is not True or not item.get('reviewer'):
            raise CoreError('Every relevance judgment requires explicit review metadata')
        if not isinstance(item.get('id'),str) or not item['id'] or item['id'] in ids:raise CoreError('Unique evaluation IDs required')
        ids.add(item['id']);gold=item.get('relevant_segment_ids')
        if not isinstance(gold,list) or not gold or not all(isinstance(x,str) for x in gold):raise CoreError('Relevant evidence IDs required')
        gold={core.evidence(x)['segment_id'] for x in gold}
        results=core.hybrid_search(item['query'],top_k=k)['results']
        found=[r['segment_id'] for r in results]
        recalls.append(len(gold.intersection(found))/len(gold))
        reciprocals.append(next((1/(i+1) for i,x in enumerate(found) if x in gold),0))
    return {'evaluated_at':now(),'count':len(examples),'k':k,
            'mean_recall_at_k':sum(recalls)/len(recalls),'mrr_at_k':sum(reciprocals)/len(reciprocals),
            'model_id':getattr(core.embedding_provider,'identity',None),'review_identity_independently_verified':False}
