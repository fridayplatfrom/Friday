"""Opt-in source services on the existing Knowledge Core.

No models, network access, training or production promotion activate implicitly.
"""
from ..knowledge_core import KnowledgeCore
from ..knowledge_core.store import CoreError
from .config import Limits, SCHEMA
from .streaming import Streaming
from .retrieval import Retrieval
from .language import Language
from .queue import Operations
from .crawl import Crawling
from .network import SecureFetcher


class EnhancedCore(Streaming, Retrieval, Language, Operations, Crawling, KnowledgeCore):
    def __init__(self,root,*,tenant='local',actor='local-operator',curator=False,limits=None,
                 embedding_provider=None,reranker_provider=None,asr_provider=None,translation_provider=None,
                 fetcher=None,allow_network=False):
        self.limits=limits or Limits()
        if not isinstance(self.limits,Limits):raise CoreError('A validated Limits instance is required')
        self._verified_assets={}
        self.embedding_provider=embedding_provider;self.reranker_provider=reranker_provider
        self.asr_provider=asr_provider;self.translation_provider=translation_provider
        self.fetcher=fetcher or SecureFetcher(allow_network=allow_network)
        super().__init__(root,tenant=tenant,actor=actor,curator=curator)
        existing=self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='service_schema'").fetchone()
        if existing:
            versions=self.db.execute('SELECT version FROM service_schema').fetchall()
            if len(versions)!=1 or versions[0][0]!=1:
                self.close();raise CoreError('Unsupported services schema')
        self.root.chmod(0o700)
        (self.root/'knowledge.sqlite3').chmod(0o600)
        self.db.executescript(SCHEMA)
        with self.transaction():self.db.execute('INSERT OR IGNORE INTO service_schema VALUES (1)')

    def service_health(self):
        with self.lock:
            database=self.db.execute('SELECT 1').fetchone()[0]==1
            queued={r['state']:r['n'] for r in self.db.execute('SELECT state,count(*) n FROM operations WHERE tenant=? GROUP BY state',(self.tenant,))}
            vectors=self.db.execute('SELECT count(*) FROM vectors WHERE tenant=?',(self.tenant,)).fetchone()[0]
        models={}
        for kind,provider in [('embedding',self.embedding_provider),('reranker',self.reranker_provider),
                              ('asr',self.asr_provider),('translation',self.translation_provider)]:
            models[kind]={'status':'loaded' if provider is not None else 'not_configured',
                          'identity':provider.identity if provider is not None else None,
                          'independent_accuracy_verified':False}
        return {'status':'ok' if database else 'degraded','metadata_backend':'sqlite_single_host',
                'models':models,'queued_operations':queued,'stored_vectors':vectors,
                'network_enabled':bool(getattr(self.fetcher,'allow_network',False)),
                'stream_asset_limit_bytes':self.limits.stream_bytes,
                'extracted_text_limit_bytes':self.limits.extracted_bytes,
                'automatically_trains_models':False}

    def bind_services(self):
        self.bootstrap();bound=[]
        specs=[('service.hybrid_search','Hybrid source retrieval','retrieve',self.embedding_provider,
                lambda p:self.hybrid_search(p['query'],top_k=p.get('top_k',5)),('query',)),
               ('service.speech_recognition','Timed speech transcription','transcribe',self.asr_provider,
                lambda p:self.transcribe(p['revision'],language=p.get('language')),('revision',)),
               ('service.learned_translation','Source-aligned translation','translate',self.translation_provider,
                lambda p:self.translate_segment(p['segment'],p['target_language'],glossary=p.get('glossary')),('segment','target_language'))]
        for alias,name,task,provider,handler,fields in specs:
            cap=self.declare_capability(alias,name=name,task=task,implemented=True,lifecycle='implemented',
                implementation={'adapter':'knowledge_services','model_available':provider is not None},input_fields=fields)
            if provider is not None or task=='retrieve':
                self.bind(cap,handler,experimental=provider is not None);bound.append(cap)
                if provider is not None:
                    alias='provider:'+provider.identity
                    record=self.maybe(alias,'entity')
                    if record is None:
                        profile=getattr(provider,'profile',None)
                        reference=profile.metadata.get('source') if profile else 'test_or_operator_provider'
                        entity=self.add_entity(name+' model','installed_external_model',alias=alias,
                            metadata={'profile_id':provider.identity,'task':task,'source':reference,'independent_accuracy_verified':False})
                    else:entity=record['id']
                    with self.transaction():self._edge(cap,'implemented_by',entity)
        return {'bound':bound,'quality_validated':False}


__all__=['EnhancedCore','Limits','CoreError']
