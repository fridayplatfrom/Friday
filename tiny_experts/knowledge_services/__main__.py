"""Explicit local operations for neural source services and bounded workers."""
import argparse
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from . import EnhancedCore,Limits,CoreError
from .models import SentenceEmbeddingProvider,CrossEncoderProvider,FasterWhisperProvider,Seq2SeqTranslationProvider,write_model_manifest


def core_from_args(args):
    providers={};limits=Limits()
    if args.config:
        path=Path(args.config).resolve()
        config=json.loads(path.read_text(encoding='utf-8'))
        if set(config)-{'limits','models'}:raise CoreError('Unknown service configuration fields')
        limits=Limits(**config.get('limits',{}))
        models=config.get('models',{})
        constructors={'embedding':SentenceEmbeddingProvider,'reranker':CrossEncoderProvider,
                      'asr':FasterWhisperProvider,'translation':Seq2SeqTranslationProvider}
        if set(models)-set(constructors):raise CoreError('Unknown model kind')
        for kind,relative in models.items():
            if not isinstance(relative,str):raise CoreError('Model path must be text')
            location=(path.parent/relative).resolve()
            providers[kind+'_provider']=constructors[kind](location)
    return EnhancedCore(args.root,tenant=args.tenant,actor='services-cli',curator=True,limits=limits,
                        allow_network=args.allow_network,**providers)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True);p.add_argument('--tenant',default='local')
    p.add_argument('--config');p.add_argument('--allow-network',action='store_true')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    im=sub.add_parser('import');im.add_argument('path');im.add_argument('--key',required=True);im.add_argument('--title',required=True)
    im.add_argument('--mime',default='text/plain');im.add_argument('--language',default='en');im.add_argument('--license-note',required=True)
    ix=sub.add_parser('index');ix.add_argument('--after',default='');ix.add_argument('--max-segments',type=int,default=10000)
    se=sub.add_parser('search');se.add_argument('query');se.add_argument('--top-k',type=int,default=5)
    a=sub.add_parser('transcribe');a.add_argument('revision');a.add_argument('--language')
    t=sub.add_parser('translate');t.add_argument('segment');t.add_argument('target_language')
    c=sub.add_parser('crawl-config');c.add_argument('url');c.add_argument('--license-note',required=True);c.add_argument('--max-pages',type=int,default=100)
    cr=sub.add_parser('crawl');cr.add_argument('website');cr.add_argument('--max-pages',type=int,default=10)
    e=sub.add_parser('enqueue');e.add_argument('kind');e.add_argument('payload_file');e.add_argument('--key',required=True)
    cancel=sub.add_parser('cancel');cancel.add_argument('operation')
    op=sub.add_parser('operation');op.add_argument('operation')
    sub.add_parser('worker-once');sub.add_parser('worker-child')
    server=sub.add_parser('serve');server.add_argument('--port',type=int,default=8765)
    m=sub.add_parser('manifest');m.add_argument('directory');m.add_argument('task');m.add_argument('--source',required=True);m.add_argument('--license-note',required=True);m.add_argument('--source-language');m.add_argument('--target-language')
    args=p.parse_args(argv)
    try:
        if args.command=='manifest':
            result=write_model_manifest(args.directory,args.task,source=args.source,license_note=args.license_note,
                    source_language=args.source_language,target_language=args.target_language)
        elif args.command=='worker-once':
            # Separate process so a blocked model/codec can be terminated. POSIX
            # process groups include FFmpeg children; Windows requires a Job Object
            # or container for equivalent complete descendant containment.
            timeout=Limits().worker_timeout_seconds
            if args.config:timeout=Limits(**json.loads(Path(args.config).read_text()).get('limits',{})).worker_timeout_seconds
            command=[sys.executable,'-m','tiny_experts.knowledge_services','--root',args.root,'--tenant',args.tenant]
            if args.config:command+=['--config',args.config]
            if args.allow_network:command+=['--allow-network']
            command+=['worker-child']
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=os.name!='nt')
            try:
                stdout,stderr=child.communicate(timeout=timeout)
                print(stdout.decode('utf-8',errors='replace')[:300000],end='')
                if child.returncode:print(json.dumps({'status':'worker_failed','exit_code':child.returncode}))
                return child.returncode
            except subprocess.TimeoutExpired:
                if os.name!='nt':os.killpg(child.pid,signal.SIGKILL)
                else:child.kill()
                child.communicate();print(json.dumps({'status':'worker_timeout','retry_after_lease_expiry':True}));return 1
        else:
            with core_from_args(args) as core:
                if args.command=='doctor':
                    result=core.service_health()
                    result['dependencies']={n:importlib.util.find_spec(n) is not None for n in ['sentence_transformers','faster_whisper','transformers','boto3']}
                elif args.command=='import':
                    rights={'store':True,'retrieve':True,'train':False,'redistribute':False}
                    if args.mime.startswith(('audio/','video/')):
                        result=core.import_recording_file(args.key,args.title,args.path,media_type=args.mime,rights=rights,license_note=args.license_note)
                    else:
                        artifact=core.register_source(args.key,args.title,language=args.language)
                        with Path(args.path).open('rb') as stream:
                            result=core.ingest_stream(artifact,stream,rights=rights,license_note=args.license_note,media_type=args.mime)
                elif args.command=='index':result=core.index_semantic(max_segments=args.max_segments,after=args.after)
                elif args.command=='search':result=core.hybrid_search(args.query,top_k=args.top_k)
                elif args.command=='transcribe':result=core.transcribe(args.revision,language=args.language)
                elif args.command=='translate':result=core.translate_segment(args.segment,args.target_language)
                elif args.command=='crawl-config':
                    site=core.add_website(args.url,args.url,crawl_allowed=True)
                    result={'website_id':site,'configuration':core.configure_crawl(site,rights={'store':True,'retrieve':True},license_note=args.license_note,max_pages=args.max_pages)}
                elif args.command=='crawl':result=core.crawl(args.website,max_pages=args.max_pages)
                elif args.command=='enqueue':result={'operation_id':core.enqueue_operation(args.kind,json.loads(Path(args.payload_file).read_text()),idempotency_key=args.key)}
                elif args.command=='cancel':result=core.cancel_operation(args.operation)
                elif args.command=='operation':result=core.operation(args.operation);result.pop('lease_token',None)
                elif args.command=='worker-child':
                    value=core.work_once();result={k:value.get(k) for k in ('id','state','status','error') if k in value}
                elif args.command=='serve':
                    from ..knowledge_core.bridge import CoreBridgeServer
                    core.bind_services()
                    token=os.environ.get('EXPERTOS_BRIDGE_TOKEN','')
                    token_file=os.environ.get('EXPERTOS_BRIDGE_TOKEN_FILE')
                    if token_file:
                        secret=Path(token_file)
                        if secret.stat().st_size>1024:raise CoreError('Secret file exceeds budget')
                        token=secret.read_text().strip()
                    with CoreBridgeServer(core,token,port=args.port) as server:
                        server.serve_forever(poll_interval=.1)
                    return 0
                else:raise CoreError('Unsupported command')
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False));return 0
    except (CoreError,OSError,ValueError,TypeError,ImportError) as exc:
        print(json.dumps({'status':'failed','error_type':type(exc).__name__,'error':str(exc)}));return 1


if __name__=='__main__':raise SystemExit(main())
