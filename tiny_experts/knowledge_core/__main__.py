"""CLI: python -m tiny_experts.knowledge_core --root ./state/knowledge init"""
import argparse
import json
import mimetypes
from pathlib import Path
from . import KnowledgeCore, CoreError
from .store import KINDS, dumps


def main(argv=None):
    p=argparse.ArgumentParser(description='ExpertOS Knowledge Core — local, non-LLM shared registries')
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--tenant',default='local')
    p.add_argument('--actor',default='local-operator')
    p.add_argument('--curator',action='store_true',help='Trusted operator review/admin context; not web authentication')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('status');sub.add_parser('coverage')
    m=sub.add_parser('migrate');m.add_argument('repository',type=Path)
    i=sub.add_parser('import-file');i.add_argument('path',type=Path);i.add_argument('--title',required=True)
    i.add_argument('--source-key',required=True);i.add_argument('--concept',action='append',default=[])
    i.add_argument('--language',default='en');i.add_argument('--license-note',required=True)
    i.add_argument('--allow-training',action='store_true');i.add_argument('--allow-redistribution',action='store_true')
    s=sub.add_parser('search');s.add_argument('query');s.add_argument('--concept',action='append',default=[])
    s.add_argument('--top-k',type=int,default=5)
    e=sub.add_parser('evidence');e.add_argument('segment_id');e.add_argument('--quote')
    l=sub.add_parser('lookup');l.add_argument('form');l.add_argument('--language',default='en');l.add_argument('--concept')
    r=sub.add_parser('records');r.add_argument('kind',choices=sorted(KINDS));r.add_argument('--offset',type=int,default=0)
    d=sub.add_parser('dashboard');d.add_argument('--output',type=Path,required=True)
    w=sub.add_parser('withdraw');w.add_argument('revision_id');w.add_argument('--reason',required=True)
    f=sub.add_parser('freeze');f.add_argument('name');f.add_argument('assignments',type=Path);f.add_argument('--demo',action='store_true')
    x=sub.add_parser('export');x.add_argument('dataset_id');x.add_argument('--partition',choices=['train','validation','test'],default='train')
    x.add_argument('--pretraining',action='store_true');x.add_argument('--output',required=True,type=Path)
    v=sub.add_parser('review');v.add_argument('record_id');v.add_argument('decision',choices=['accepted','rejected']);v.add_argument('--note',required=True)
    q=sub.add_parser('impact');q.add_argument('record_id')
    sub.add_parser('demo')
    args=p.parse_args(argv)
    try:
        with KnowledgeCore(args.root,tenant=args.tenant,actor=args.actor,curator=args.curator) as core:
            cmd=args.command
            if cmd=='init':result=core.bootstrap()
            elif cmd=='status':result={'schema_version':1,'tenant':core.tenant,'counts':core.counts(),
                 'runtime_ready':len(core.discover(only_ready=True)),'automatic_training':False}
            elif cmd=='coverage':result=core.coverage()
            elif cmd=='migrate':result=core.migrate_repository(args.repository)
            elif cmd=='import-file':
                path=args.path.resolve()
                if not path.is_file() or path.stat().st_size>20*1024*1024:raise CoreError('Source missing or over 20 MiB')
                rights={'store':True,'retrieve':True,'train':args.allow_training,'redistribute':args.allow_redistribution}
                raw=path.read_bytes();ext=path.suffix.lower();mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                if ext in {'.jpg','.jpeg','.png','.webp'}:
                    result=core.ingest_image(args.source_key,args.title,raw,rights=rights,license_note=args.license_note,concepts=args.concept)
                else:
                    body=None
                    if ext in {'.txt','.md','.csv','.py','.json'}:
                        body=raw.decode('utf-8-sig')
                    elif ext in {'.pdf','.docx','.epub'}:
                        from ..pipeline.ingestion import LiteratureIngestionPipeline
                        body,_=LiteratureIngestionPipeline.extract_text_from_file(str(path))
                    else:raise CoreError('Use the media API for timed recordings or unsupported formats')
                    with core.transaction():
                        artifact=core.register_source(args.source_key,args.title,language=args.language,concept_ids=args.concept)
                        result=core.ingest(artifact,raw,media_type=mime,extracted_text=body,rights=rights,
                                license_note=args.license_note,concept_ids=args.concept,
                                extraction_method='local-file-text-extraction-v1',metadata={'original_filename':path.name})
            elif cmd=='search':result=core.search(args.query,concepts=args.concept,top_k=args.top_k)
            elif cmd=='evidence':result=core.evidence(args.segment_id,quote=args.quote)
            elif cmd=='lookup':result=core.resolve_term(args.form,args.language,concept=args.concept)
            elif cmd=='records':result=core.records(args.kind,include_inactive=True,offset=args.offset)
            elif cmd=='dashboard':
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(core.report_html(),encoding='utf-8');result={'written':str(args.output)}
            elif cmd=='withdraw':result=core.withdraw_source(args.revision_id,reason=args.reason)
            elif cmd=='review':core.review(args.record_id,decision=args.decision,note=args.note);result={'review_recorded':True}
            elif cmd=='freeze':result={'dataset_id':core.freeze_dataset(args.name,json.loads(args.assignments.read_text()),demo=args.demo)}
            elif cmd=='export':
                fn=core.export_pretraining if args.pretraining else core.export_dataset
                rows=fn(args.dataset_id,partition=args.partition)
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(''.join(dumps(r)+'\n' for r in rows),encoding='utf-8');result={'records':len(rows),'output':str(args.output)}
            elif cmd=='impact':result=core.impact(args.record_id)
            else:
                from .demo import run_demo
                result=run_demo(core)
            print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
        return 0
    except (CoreError,OSError,ValueError,ImportError) as error:
        print(json.dumps({'status':'failed','error':str(error)},ensure_ascii=False));return 1


if __name__=='__main__':raise SystemExit(main())
