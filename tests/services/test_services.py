"""Offline infrastructure/contract tests. Fake providers DO NOT measure neural accuracy."""
import hashlib
import io
import json
import math
from pathlib import Path
import socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import wave

import pytest
from tiny_experts.knowledge_services import EnhancedCore,Limits,CoreError
from tiny_experts.knowledge_core import AccessDenied
from tiny_experts.knowledge_core.bridge import CoreBridgeServer
from tiny_experts.knowledge_services.models import ModelProfile,ModelUnavailable,write_model_manifest
from tiny_experts.knowledge_services.network import SecureFetcher,safe_url,Response,FetchError
from tiny_experts.knowledge_services.crawl import Robots
from tiny_experts.knowledge_services.language import protect_terms,restore_terms,probe_duration
from tiny_experts.knowledge_services.retrieval import unit_vector

RIGHTS={'store':True,'retrieve':True,'train':False,'redistribute':False}


class TestEmbedding:
    identity='synthetic-contract-embedding-v1'
    def v(self,text):
        t=text.casefold()
        return [1.0 if any(w in t for w in ['feline','cat','kitten']) else .01,
                1.0 if any(w in t for w in ['thermal','heat','temperature','warmth']) else .01,
                1.0 if any(w in t for w in ['form','browser']) else .01]
    def encode_documents(self,texts):return [self.v(t) for t in texts]
    def encode_query(self,q):return self.v(q)


class TestASR:
    identity='synthetic-contract-asr-v1'
    def transcribe_chunk(self,path,*,language=None):
        with wave.open(str(path)) as f:
            assert f.getframerate()==16000 and f.getnchannels()==1
            duration=f.getnframes()/f.getframerate()
        return {'language':'en','segments':[{'start':0,'end':min(.5,duration),'text':'A synthetic transcript for plumbing tests.'}]}


class TestTranslator:
    identity='synthetic-contract-translator-v1'
    def translate(self,text,*,source_language,target_language):
        assert source_language=='en' and target_language=='hi'
        return text.replace('Heat','ऊष्मा').replace(' at ',' पर ').replace(' with ',' के साथ ')


class FakeFetcher:
    allow_network=False
    def __init__(self,responses):self.responses=responses;self.calls=[]
    def fetch(self,url,**kwargs):
        self.calls.append((url,kwargs));value=self.responses[url]
        if isinstance(value,Exception):raise value
        return value


@pytest.fixture
def core(tmp_path):
    with EnhancedCore(tmp_path/'core',curator=True) as c:
        c.bootstrap();yield c


def add(core,key='a',body='Heat at 300 K.',**kwargs):
    a=core.register_source(key,key,language=kwargs.pop('language','en'),concept_ids=['concept.thermodynamics'])
    return core.ingest_stream(a,io.BytesIO(body.encode()),rights=kwargs.pop('rights',RIGHTS),
                  license_note='Original synthetic software fixture',**kwargs)


def segments(core,rid):
    return [core.get(e['src']) for e in core.edges(rid,relation='segment_of',reverse=True)]


@pytest.mark.parametrize('field,value',[('stream_bytes',0),('audio_chunk_seconds',True),('chunk_characters',100),('embedding_batch',257),('crawl_depth',21)])
def test_limits_validate(field,value):
    with pytest.raises(CoreError):Limits(**{field:value})


def test_old_api_stays_bounded_and_large_stream_succeeds(core):
    raw=b'x'*(20*1024**2+1)
    with pytest.raises(CoreError):core.put_asset(raw)
    output=core.put_stream(io.BytesIO(raw))
    assert output['bytes']>20*1024**2
    assert core.verify_asset(output['sha256']).stat().st_size==len(raw)
    with pytest.raises(CoreError):core.read_asset(output['sha256'])


def test_stream_rollback_and_empty_inputs(core):
    before=core.counts().get('revision',0)
    a=core.register_source('empty','Empty')
    for body in (b'',b'\xff',b' \n ',b'abc\0def'):
        with pytest.raises((CoreError,UnicodeError)):
            core.ingest_stream(a,io.BytesIO(body),rights=RIGHTS,license_note='fixture')
    assert core.get(a)['data']['current_revision'] is None
    assert core.counts().get('revision',0)==before


def test_stream_limit(core):
    with pytest.raises(CoreError,match='budget'):
        core.put_stream(io.BytesIO(b'a'*4097),max_bytes=4096)
    assert not list(core.asset_root.glob('.incoming-*'))


def test_utf8_segments_offsets_and_lookup(core):
    body=('ऊष्मा at 300 K. 🦊\n'*600)
    row=add(core,body=body)
    ss=sorted(segments(core,row['revision_id']),key=lambda x:x['data']['selector']['start'])
    assert len(ss)>1
    assert ''.join(core.evidence(s['id'])['text'] for s in ss)==body
    crossing=core.add_segment(row['revision_id'],{'type':'text','start':4080,'end':4110})
    assert core.evidence(crossing)['text']==body[4080:4110]
    assert core.search('ऊष्मा')[0]['source_consistency']
    assert not row['neural_training_started']


def test_large_extracted_text_over_old_8mib_limit(core):
    # Full ingestion, not merely configuration: bounded chunks and FTS persist.
    body=('thermal source record 300 K\n'*325000)
    assert len(body.encode())>8*1024**2
    r=add(core,key='large',body=body)
    assert r['segments']>2000
    hit=core.search('thermal',revision=r['revision_id'],top_k=1)[0]
    assert '300 K' in hit['text']


def test_revision_replacement_invalidates_vectors(core):
    core.embedding_provider=TestEmbedding()
    a=add(core,body='The cat is a feline.');core.index_semantic()
    assert core.hybrid_search('kitten')['results']
    b=add(core,body='A browser form changed.')
    assert b['revision_id']!=a['revision_id']
    assert core.service_health()['stored_vectors']==0
    assert not core.search('feline')
    core.index_semantic();assert core.hybrid_search('form')['results'][0]['revision_id']==b['revision_id']


def test_stream_idempotency_cancel_and_corruption(core):
    a=add(core);b=add(core)
    assert b['idempotent'] and a['revision_id']==b['revision_id']
    artifact=core.get(a['artifact_id'])
    with pytest.raises(CoreError,match='cancel'):
        core.ingest_stream(a['artifact_id'],io.BytesIO(b'new'),rights=RIGHTS,license_note='fixture',cancelled=lambda:True)
    assert core.get(a['artifact_id'])['data']==artifact['data']
    path=core.verify_asset(core.get(a['revision_id'])['data']['sha256']);path.write_bytes(b'corrupt')
    with pytest.raises(CoreError,match='checksum'):
        core.evidence(segments(core,a['revision_id'])[0]['id'])


def test_stream_permissions_and_parent_revocation(core):
    source=add(core,key='parent')
    a=core.register_source('child','child')
    child=core.ingest_stream(a,io.BytesIO(b'child heat'),rights=RIGHTS,license_note='fixture',parent_revisions=[source['revision_id']])
    core.set_rights(source['revision_id'],{'store':True,'retrieve':False},reason='fixture revoke')
    assert not core.search('child')
    with pytest.raises(AccessDenied):core.evidence(segments(core,child['revision_id'])[0]['id'])


def test_semantic_hybrid_and_resume(core):
    core.embedding_provider=TestEmbedding()
    add(core,key='cat',body='A feline rests.');add(core,key='heat',body='Thermal energy matters.')
    a=core.index_semantic(max_segments=1)
    assert a['indexed']==1 and not a['complete']
    b=core.index_semantic(after=a['cursor'])
    assert b['indexed']==1 and b['complete']
    assert core.index_semantic()['indexed']==0
    hits=core.hybrid_search('kitten',top_k=1)
    assert hits['mode']=='hybrid' and 'feline' in hits['results'][0]['text']
    assert hits['semantic_support']=='not_evaluated'


def test_embedding_version_acl_tenant_and_bad_numbers(core,tmp_path):
    core.embedding_provider=TestEmbedding();a=add(core);core.index_semantic()
    count=core.service_health()['stored_vectors']
    encoder=TestEmbedding();encoder.identity='different-version';core.embedding_provider=encoder
    assert core.hybrid_search('heat')['eligible_vectors']==0
    core.embedding_provider=TestEmbedding()
    core.set_rights(a['revision_id'],{'store':True,'retrieve':False},reason='withdraw access')
    assert core.hybrid_search('heat')['results']==[]
    with EnhancedCore(core.root,tenant='other',curator=True,embedding_provider=TestEmbedding()) as other:
        assert other.hybrid_search('heat')['results']==[] and other.service_health()['stored_vectors']==0
    assert core.prune_vector_index()['removed']==count
    for vector in ([0,0],[float('nan'),1],[float('inf')],[True,1],[]):
        with pytest.raises(CoreError):unit_vector(vector)


def test_reranker_and_source_purge(core):
    core.embedding_provider=TestEmbedding()
    first=add(core,key='one',body='Heat from first source.')
    second=add(core,key='two',body='Heat from second source.')
    core.index_semantic()
    class Rerank:
        identity='fixture-rerank'
        def scores(self,q,ps):return [100 if 'second' in p else 0 for p in ps]
    core.reranker_provider=Rerank()
    assert core.hybrid_search('heat',top_k=1)['results'][0]['revision_id']==second['revision_id']
    core.purge_source(second['revision_id'],reason='fixture purge')
    assert all(x['revision_id']!=second['revision_id'] for x in core.search('heat'))
    assert core.db.execute('SELECT count(*) FROM text_chunks WHERE revision_id=?',(second['revision_id'],)).fetchone()[0]==0


def test_local_profile_checks_hash_extra_files_and_task(tmp_path):
    path=tmp_path/'model';path.mkdir();(path/'weights.safetensors').write_bytes(b'fixture-not-weights')
    write_model_manifest(path,'embedding',license_note='synthetic test',source='test suite')
    profile=ModelProfile.load(path,'embedding');assert len(profile.identity)==64
    with pytest.raises(ModelUnavailable):ModelProfile.load(path,'asr')
    (path/'extra.py').write_text('print("must never run")')
    with pytest.raises(ModelUnavailable):ModelProfile.load(path,'embedding')
    (path/'extra.py').unlink();(path/'weights.safetensors').write_bytes(b'tamper')
    with pytest.raises(ModelUnavailable,match='checksum'):ModelProfile.load(path,'embedding')


def make_wav(path):
    import struct
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        f.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(2*math.pi*440*i/16000))) for i in range(16000)))


def test_actual_media_processing_with_contract_asr(core,tmp_path):
    path=tmp_path/'one.wav';make_wav(path)
    recording=core.import_recording_file('recording','Recording',path,media_type='audio/wav',rights=RIGHTS,license_note='synthetic waveform')
    core.asr_provider=TestASR()
    result=core.transcribe(recording['revision_id'])
    assert result['automatic_speech_recognition_performed'] and result['word_error_rate'] is None
    assert core.get(result['revision_id'])['data']['review_state']=='unreviewed'
    assert core.source_ancestry(result['revision_id'])[0]
    assert core.search('synthetic transcript')
    assert result['alignments']
    before=core.counts()['revision']
    with pytest.raises(CoreError,match='cancel'):core.transcribe(recording['revision_id'],cancelled=lambda:True)
    assert core.counts()['revision']==before


def test_asr_unavailable_silence_bad_timestamps(core,tmp_path):
    path=tmp_path/'two.wav';make_wav(path)
    recording=core.import_recording_file('record','Recording',path,media_type='audio/wav',rights=RIGHTS,license_note='fixture')
    with pytest.raises(ModelUnavailable):core.transcribe(recording['revision_id'])
    class Silent:
        identity='fixture-silence'
        def transcribe_chunk(self,*a,**k):return {'language':'en','segments':[]}
    core.asr_provider=Silent()
    assert core.transcribe(recording['revision_id'])['status']=='no_speech_detected'
    class Bad:
        identity='fixture-invalid'
        def transcribe_chunk(self,*a,**k):return {'language':'en','segments':[{'start':0,'end':99,'text':'bad'}]}
    core.asr_provider=Bad()
    with pytest.raises(CoreError,match='timestamp'):core.transcribe(recording['revision_id'])


def test_translation_ancestry_numeric_glossary_and_no_auto_review(core):
    parent=add(core,body='Heat at 300 K with Rust.')
    sid=segments(core,parent['revision_id'])[0]['id']
    with pytest.raises(ModelUnavailable):core.translate_segment(sid,'hi')
    core.translation_provider=TestTranslator()
    result=core.translate_segment(sid,'hi',glossary={'Rust':'Rust','K':'K'})
    proof=core.evidence(result['segment_id'])
    assert 'ऊष्मा' in proof['text'] and '300 K' in proof['text'] and 'Rust' in proof['text']
    assert core.get(result['translation_id'])['data']['review_state']=='proposed'
    assert core.get(result['revision_id'])['data']['family_id']==core.get(parent['revision_id'])['data']['family_id']
    core.withdraw_source(parent['revision_id'],reason='fixture')
    with pytest.raises(AccessDenied):core.evidence(result['segment_id'])


def test_translation_rejects_changed_numbers_and_markers(core):
    parent=add(core,body='Heat at 300 K.');sid=segments(core,parent['revision_id'])[0]['id']
    class Wrong:
        identity='fixture-bad'
        def translate(self,*a,**k):return 'ऊष्मा 999 K.'
    core.translation_provider=Wrong()
    with pytest.raises(CoreError,match='numeric'):core.translate_segment(sid,'hi')
    value,protected=protect_terms('Rust with `x=2`.',{'Rust':'Rust'})
    with pytest.raises(CoreError):restore_terms('lost terms',protected)
    assert restore_terms(value,protected)=='Rust with `x=2`.'


@pytest.mark.parametrize('url',['http://example.org/','https://example.org@localhost/',
 'https://127.0.0.1/','https://example.org:444/','https://example.org/?token=secret',
 'https://example.org/a%QQ','https://evil.org/','https://example.org\\@evil.org/'])
def test_network_url_rejections(url):
    with pytest.raises(AccessDenied):safe_url(url,{'example.org'})


def test_network_disabled_and_private_dns(monkeypatch):
    with pytest.raises(AccessDenied):SecureFetcher().fetch('https://example.org',allowed_hosts={'example.org'},max_bytes=100)
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))])
    with pytest.raises(AccessDenied,match='non-public'):
        SecureFetcher(allow_network=True).fetch('https://example.org',allowed_hosts={'example.org'},max_bytes=100)


def test_robots_longest_match_wildcard_and_specific_agent():
    rules=Robots('User-agent: *\nDisallow: /private\nAllow: /private/public\nDisallow: /*.pdf$\nCrawl-delay: 2')
    assert not rules.allows('https://example.org/private/x')
    assert rules.allows('https://example.org/private/public/x')
    assert not rules.allows('https://example.org/file.pdf')
    assert rules.allows('https://example.org/file.pdf?x=1') and rules.delay==2
    specific=Robots('User-agent: *\nDisallow: /\nUser-agent: ExpertOSBot\nAllow: /')
    assert specific.allows('https://example.org/a')


def setup_crawl(core,responses):
    site=core.add_website('https://example.org/','Fixture',crawl_allowed=True)
    core.configure_crawl(site,rights=RIGHTS,license_note='Synthetic test responses',max_pages=10)
    core.fetcher=FakeFetcher(responses)
    return site


def test_crawl_index_discovery_noindex_and_crosshost(core,monkeypatch):
    root='https://example.org/'
    responses={root+'robots.txt':Response(root+'robots.txt',200,{},b'User-agent: *\nDisallow: /private'),
     root:Response(root,200,{'content-type':'text/html'},b'<title>Thermal</title><p>Heat engine</p><a href="/two">Next</a><a href="https://evil.org/">Out</a><a href="/private">Private</a>'),
     root+'two':Response(root+'two',200,{'content-type':'text/html'},b'<meta name="robots" content="noindex"><p>Secret fixture</p>')}
    site=setup_crawl(core,responses);monkeypatch.setattr(core,'_request_slot',lambda *a:0)
    result=core.crawl(site,max_pages=10)
    assert result['processed']==3
    assert any(o['state']=='noindex' for o in result['outcomes'])
    assert any(o['state']=='blocked' for o in result['outcomes'])
    assert core.search('engine') and not core.search('Secret')
    assert not any('evil' in u or '/private' in u for u,k in core.fetcher.calls)


@pytest.mark.parametrize('status',[401,403,500,503,301])
def test_robots_unavailable_fail_closed(core,monkeypatch,status):
    root='https://example.org/'
    site=setup_crawl(core,{root+'robots.txt':Response(root+'robots.txt',status,{},b'')})
    monkeypatch.setattr(core,'_request_slot',lambda *a:0)
    with pytest.raises(AccessDenied):core.crawl(site)
    assert len(core.fetcher.calls)==1 and not core.search('anything')


def test_crawl_redirect_and_rate_limit(core,monkeypatch):
    root='https://example.org/'
    site=setup_crawl(core,{root+'robots.txt':Response(root+'robots.txt',404,{},b''),root:Response(root,302,{'location':'https://127.0.0.1/'},b'')})
    # The first real rate reservation is robots; the page is delayed.
    result=core.crawl(site)
    assert result['processed']==0 and len(core.fetcher.calls)==1
    monkeypatch.setattr(core,'_request_slot',lambda *a:0)
    with core.transaction():core.db.execute('UPDATE crawl_frontier SET available_at=0')
    result=core.crawl(site)
    assert result['outcomes'][0]['state']=='failed'
    assert len(core.fetcher.calls)==2


def test_queue_idempotency_lease_recovery_cancel(core,monkeypatch):
    job=core.enqueue_operation('semantic_index',{},idempotency_key='one')
    assert core.enqueue_operation('semantic_index',{},idempotency_key='one')==job
    with pytest.raises(CoreError):core.enqueue_operation('transcribe',{},idempotency_key='one')
    first=core.claim_operation(lease_seconds=10)
    assert core.claim_operation() is None
    with core.transaction():core.db.execute('UPDATE operations SET lease_until=0 WHERE id=?',(job,))
    second=core.claim_operation();assert second['lease_token']!=first['lease_token']
    with pytest.raises(AccessDenied):core.finish_operation(job,first['lease_token'],result={})
    core.cancel_operation(job)
    with pytest.raises(AccessDenied):core.finish_operation(job,second['lease_token'],result={})
    assert core.operation(job)['state']=='cancelled'


def test_worker_real_index_task_and_retries(core):
    core.embedding_provider=TestEmbedding();add(core)
    id=core.enqueue_operation('semantic_index',{},idempotency_key='index')
    completed=core.work_once();assert completed['id']==id and completed['state']=='succeeded'
    id=core.enqueue_operation('transcribe',{'revision':'missing'},idempotency_key='failure',max_attempts=1)
    failed=core.work_once();assert failed['state']=='failed' and failed['error']=='ModelUnavailable'


def test_backup_restore_services_and_cross_tenant_queue(core,tmp_path):
    core.embedding_provider=TestEmbedding();row=add(core);core.index_semantic()
    job=core.enqueue_operation('semantic_index',{},idempotency_key='job')
    target=tmp_path/'backup';core.backup_to(target)
    with EnhancedCore(target,curator=True,embedding_provider=TestEmbedding()) as restored:
        assert restored.search('warmth')[0]['revision_id']==row['revision_id']
        assert restored.operation(job)['state']=='pending'
    with EnhancedCore(core.root,tenant='other',curator=True) as other:
        with pytest.raises(CoreError):other.operation(job)
        assert other.claim_operation() is None


def test_actual_authenticated_bridge_hybrid_search(core):
    core.embedding_provider=TestEmbedding();add(core,body='A feline sleeps.');core.index_semantic()
    token='x'*40
    with CoreBridgeServer(core,token,port=0) as server:
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with pytest.raises(HTTPError):urlopen(base+'/health',timeout=3)
            req=Request(base+'/v1/core/search',data=json.dumps({'query':'kitten'}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            result=json.load(urlopen(req,timeout=3))
            assert 'feline' in json.dumps(result)
            req=Request(base+'/v1/core/search',data=b'{"query":"kitten","tenant":"other"}',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            with pytest.raises(HTTPError):urlopen(req,timeout=3)
        finally:server.shutdown();thread.join(timeout=3)


def test_s3_replication_contract(core):
    from tiny_experts.knowledge_services.object_storage import S3Mirror
    class Client:
        def __init__(self):self.objects={}
        def upload_fileobj(self,f,bucket,key,ExtraArgs):self.objects[key]=(f.read(),ExtraArgs)
        def head_object(self,*,Bucket,Key):
            raw,extra=self.objects[Key];return {'ContentLength':len(raw),'Metadata':extra['Metadata']}
    source=add(core);client=Client();mirror=S3Mirror(bucket='private-fixture',client=client)
    result=mirror.replicate(core,source['revision_id'])
    assert result['replicated'] and not result['metadata_distributed']
    assert all(extra['ServerSideEncryption']=='AES256' for raw,extra in client.objects.values())


def test_unknown_service_schema_refused(core):
    root=core.root
    core.db.execute('UPDATE service_schema SET version=99')
    with pytest.raises(CoreError,match='schema'):EnhancedCore(root)


def test_token_budget_chunking_preserves_exact_evidence(core):
    class SplitEncoder(TestEmbedding):
        identity='synthetic-window-contract'
        def chunk_spans(self,text):
            return [(i,min(i+30,len(text))) for i in range(0,len(text),30)] if len(text)>30 else [(0,len(text))]
        def encode_documents(self,texts):
            assert all(len(t)<=30 for t in texts)
            return super().encode_documents(texts)
    core.embedding_provider=SplitEncoder()
    row=add(core,body='Thermal energy is connected to heat. A feline is a cat. More thermal words.')
    indexed=core.index_semantic()
    assert indexed['indexed']>=3
    results=core.hybrid_search('kitten')['results']
    assert results and all(r['source_consistency'] for r in results)
    assert core.get(row['revision_id'])['status']=='active'


@pytest.mark.parametrize('url',['https://example.org/../private','https://example.org/%2e%2e/private',
                                'https://example.org/a%2fprivate','https://example.org/%252e%252e/private'])
def test_ambiguous_paths_rejected(url):
    with pytest.raises(AccessDenied):safe_url(url,{'example.org'})


def test_unicode_robots_rules():
    rules=Robots('User-agent: *\nDisallow: /café')
    assert not rules.allows('https://example.org/caf%C3%A9')


def test_translation_retry_is_idempotent(core):
    row=add(core,body='Heat at 300 K.');sid=segments(core,row['revision_id'])[0]['id']
    core.translation_provider=TestTranslator()
    a=core.translate_segment(sid,'hi');counts=core.counts()
    b=core.translate_segment(sid,'hi')
    assert a['translation_id']==b['translation_id'] and counts==core.counts()


def test_crawl_permission_change_during_fetch_cannot_publish(core,monkeypatch):
    root='https://example.org/'
    site=setup_crawl(core,{root+'robots.txt':Response(root+'robots.txt',404,{},b''),root:Response(root,200,{'content-type':'text/html'},b'<p>Do not publish</p>')})
    monkeypatch.setattr(core,'_request_slot',lambda *a:0)
    fetch=core.fetcher.fetch
    def changed(url,**kwargs):
        response=fetch(url,**kwargs)
        if url==root:
            with core.transaction():
                record=core.get(site);core._change(site,data={**record['data'],'crawl_allowed':False})
        return response
    core.fetcher.fetch=changed
    result=core.crawl(site)
    assert result['outcomes'][0]['state']=='failed' and not core.search('publish')


def test_full_pipeline_transcript_translation_search_and_withdrawal(core,tmp_path):
    path=tmp_path/'pipeline.wav';make_wav(path)
    core.asr_provider=TestASR();core.translation_provider=TestTranslator();core.embedding_provider=TestEmbedding()
    recording=core.import_recording_file('pipeline','Pipeline recording',path,media_type='audio/wav',rights=RIGHTS,license_note='Synthetic workflow')
    transcript=core.transcribe(recording['revision_id'])
    text_segment=transcript['alignments'][0]['text_segment']
    translated=core.translate_segment(text_segment,'hi')
    assert translated['status']=='translated'
    core.index_semantic()
    assert core.hybrid_search('synthetic transcript')['results']
    core.withdraw_source(recording['revision_id'],reason='End-to-end revocation test')
    assert not core.hybrid_search('synthetic transcript')['results']


def test_retrieval_and_wer_metrics_are_measured(core):
    from tiny_experts.knowledge_services.evaluation import retrieval_report,word_error_rate
    r=add(core,body='Heat at 300 kelvin.');sid=segments(core,r['revision_id'])[0]['id']
    report=retrieval_report(core,[{'id':'q1','query':'Heat','reviewed':True,'reviewer':'synthetic-fixture',
                                 'relevant_segment_ids':[sid]}],k=1)
    assert report['count']==1 and report['mrr_at_k']==1
    assert word_error_rate('the cat sat','the dog sat')['wer']==pytest.approx(1/3)
    assert word_error_rate('','unwanted speech')['wer'] is None
    with pytest.raises(CoreError):retrieval_report(core,[{'id':'q','query':'Heat','reviewed':False}])


def test_worker_cli_isolated_process(tmp_path):
    import subprocess,sys
    root=tmp_path/'worker'
    with EnhancedCore(root,curator=True) as c:
        id=c.enqueue_operation('semantic_index',{},idempotency_key='will-report-missing-model',max_attempts=1)
    run=subprocess.run([sys.executable,'-m','tiny_experts.knowledge_services','--root',str(root),'worker-once'],
                       capture_output=True,text=True,timeout=15)
    assert run.returncode==0,run.stderr
    with EnhancedCore(root,curator=True) as c:
        assert c.operation(id)['state']=='failed'
        assert c.operation(id)['error']=='CoreError'


def test_observed_word_locations_are_exact(core):
    body='Heat is observed at 300 kelvin.'
    row=add(core,body=body)
    occurrence=core.db.execute('SELECT example_start FROM occurrences WHERE tenant=? AND revision_id=? AND form=?',
                              (core.tenant,row['revision_id'],'kelvin')).fetchone()
    assert occurrence[0]==body.index('kelvin')


def test_provider_directory_is_connected_but_not_approved(core):
    core.embedding_provider=TestEmbedding()
    result=core.bind_services()
    capability=core.get('service.hybrid_search','capability')
    linked=core.edges(capability['id'],relation='implemented_by')
    assert result['bound'] and len(linked)==1
    assert core.get(linked[0]['dst'])['data']['entity_type']=='installed_external_model'
    assert not core.service_health()['models']['embedding']['independent_accuracy_verified']
    assert core.capability_health(capability['id'])['experimental']
    assert not core.capability_health('service.speech_recognition')['ready']


def test_streaming_pretraining_export_obeys_split_and_revocation(core):
    assignments={};revisions=[]
    for i,partition in enumerate(('train','validation','test')):
        rights={**RIGHTS,'train':True}
        row=add(core,key=f'train-source-{i}',body=f'Unique synthetic example {i} with thermal energy.',rights=rights)
        sid=segments(core,row['revision_id'])[0]['id']
        annotation=core.annotate('classification',{'text':f'Independent task {i}'},{'topic':'heat'},[sid],case_id=f'case-{i}')
        core.review(row['revision_id'],decision='accepted',note='Synthetic test only')
        core.review(annotation,decision='accepted',note='Synthetic test only')
        assignments[annotation]=partition;revisions.append(row['revision_id'])
    ds=core.freeze_dataset('synthetic-test',assignments)
    output=list(core.iter_pretraining(ds,partition='train'))
    assert output and {x['revision_id'] for x in output}=={revisions[0]}
    core.set_rights(revisions[0],{'store':True,'retrieve':True,'train':False},reason='Training permission removed')
    with pytest.raises(CoreError):list(core.iter_pretraining(ds,partition='train'))
