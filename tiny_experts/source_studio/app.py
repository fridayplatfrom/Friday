"""Local, authenticated Source Studio HTTP API and single-page interface.

This is a trusted-operator development service. It binds loopback only; do not
expose to a public network without a dedicated identity/tenant gateway.
"""
from __future__ import annotations

from contextlib import contextmanager
import io
import mimetypes
import os
from pathlib import Path
import tempfile
import re
import secrets
from urllib.parse import urlsplit

from .director import TrainingDirector
from ..cognition import CognitiveEngine, DefinitionLibrary
from ..knowledge_core.store import CoreError, AccessDenied
from ..knowledge_services import EnhancedCore

try:
    from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Request, Depends
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel, Field
except ImportError as e:
    raise ImportError('Install Source Studio extras: fastapi, uvicorn, python-multipart') from e

SUPPORTED={'.txt','.md','.csv','.json','.pdf','.docx','.epub','.png','.jpg','.jpeg','.webp','.wav','.mp3','.mp4','.webm'}
TEXTUAL={'.txt','.md','.csv','.json'}
MAX_UI_UPLOAD=64*1024*1024
MAX_EXTRACTED=32*1024*1024

class PolicyRequest(BaseModel):
    mode:str
    research_preapproved:bool=False

class ReviewRequest(BaseModel):
    record_id:str
    decision:str
    note:str=Field(min_length=3,max_length=4096)
    candidate:bool=False

class RightsRequest(BaseModel):
    revision_id:str
    store:bool=True
    retrieve:bool=True
    train:bool=False
    redistribute:bool=False
    reason:str=Field(min_length=3,max_length=1024)

class ReleaseRequest(BaseModel):
    name:str
    assignments:dict[str,str]
    demo:bool=False
    trainer:str|None=None
    config:dict|None=None

class TrainRequest(BaseModel):
    dataset_id:str
    trainer:str
    config:dict

class AnnotationRequest(BaseModel):
    task:str
    segment_id:str
    case_id:str
    question:str|None=None
    answer:str|None=None
    text:str|None=None
    labels:dict[str,str]|None=None


class GoalRequest(BaseModel):
    title:str
    success:list[str]
    constraints:dict=Field(default_factory=dict)
    budget:dict=Field(default_factory=lambda:{'max_steps':16})

class ObservationRequest(BaseModel):
    scope:str
    snapshot:dict
    expected_version:int|None=None

class ChoiceRequest(BaseModel):
    goal_id:str
    options:list[dict]
    weights:dict[str,float]
    minimum_score:float=0.0
    minimum_margin:float=0.0

class PlanRequest(BaseModel):
    goal_id:str
    steps:list[dict]
    permissions:list[str]=Field(default_factory=lambda:['local_compute'])

class DefinitionRequest(BaseModel):
    concept_id:str
    wording:str
    evidence_ids:list[str]
    scope:str

class DefinitionReviewRequest(BaseModel):
    definition_id:str
    accept:bool
    note:str

class RevisionTargetRequest(BaseModel):
    revision_id:str
    book_title:str="Source Book"
    default_subdomain:str|None=None

class GSTWorkflowRequest(BaseModel):
    supplier_gstin:str
    return_period:str="2026-10"
    invoices:list[dict]=Field(default_factory=list)
    itc_available:float=0.0

class SynthesisExecuteRequest(BaseModel):
    mode:str="code"
    query:str=""
    sheet_title:str="Generated_Sheet"
    rows_data:list[dict]|None=None
    tone:str="formal_business"
    recipient_name:str="Respected Officer"
    key_facts:list[str]=Field(default_factory=list)

def create_app(root, *, token:str, tenant='local', max_upload=MAX_UI_UPLOAD):
    if not isinstance(token,str) or len(token)<24:
        raise ValueError('Studio requires a random bearer token of at least 24 characters')
    if type(max_upload) is not int or not 1<=max_upload<=MAX_UI_UPLOAD:
        raise ValueError('Upload cap must be 1..64 MiB')
    root=Path(root).resolve()
    app=FastAPI(title='ExpertOS Source Studio',docs_url=None,redoc_url=None,openapi_url=None)

    @app.middleware('http')
    async def boundaries(request:Request,call_next):
        host=request.headers.get('host','').split(':')[0].strip('[]').casefold()
        if host not in {'localhost','127.0.0.1','::1','testserver'}:
            return JSONResponse(status_code=403,content={'detail':'Loopback host required'})
        origin=request.headers.get('origin')
        if origin:
            try:
                parsed=urlsplit(origin)
                origin_host=(parsed.hostname or '').casefold()
            except ValueError:
                origin_host=''
            if origin_host not in {'localhost','127.0.0.1','::1','testserver'} or parsed.scheme not in {'http','https'}:
                return JSONResponse(status_code=403,content={'detail':'Cross-site request rejected'})
            # Even another local web service may have a different port.
            referer_origin=origin.rstrip('/')
            allowed=f'{request.url.scheme}://{request.headers.get("host")}'
            if referer_origin != allowed:
                return JSONResponse(status_code=403,content={'detail':'Cross-port origin rejected'})
        length=request.headers.get('content-length')
        if length:
            try:
                if int(length)>max_upload+1024*1024:raise ValueError()
            except ValueError:
                return JSONResponse(status_code=413,content={'detail':'Request size limit exceeded'})
        if request.url.path.startswith('/api/'):
            provided=request.headers.get('authorization','')
            if not secrets.compare_digest(provided,'Bearer '+token):
                return JSONResponse(status_code=401,content={'detail':'Bearer token required'})
        try:
            return await call_next(request)
        except (CoreError,AccessDenied) as exc:
            status=403 if isinstance(exc,AccessDenied) else 400
            return JSONResponse(status_code=status,content={'detail':str(exc)})

    @contextmanager
    def session():
        with EnhancedCore(root,tenant=tenant,actor='studio-operator',curator=True,allow_network=False) as core:
            core.bootstrap()
            yield core,TrainingDirector(core)

    @app.get('/',response_class=HTMLResponse)
    async def home():
        return (Path(__file__).parent/'web'/'index.html').read_text(encoding='utf-8')

    @app.get('/api/health')
    async def health():
        with session() as (core,director):
            return {'status':'ok','service':'source_studio','policy':director.policy(),
                    'sources':len(core.records('revision')),'pending_candidates':sum(c['status']=='proposed' for c in director.candidates(limit=500)),
                    'training_jobs':len(director.jobs()),'models':core.service_health()['models'],
                    'automatic_deployment':False}

    @app.get('/api/policy')
    async def policy():
        with session() as (_,director):return director.policy()

    @app.post('/api/policy')
    async def update_policy(payload:PolicyRequest):
        with session() as (_,director):return director.set_policy(payload.mode,research_preapproved=payload.research_preapproved)

    @app.get('/api/sources')
    async def sources():
        with session() as (core,_):
            return [{'revision_id':x['id'],'title':x['data'].get('title'),
                     'type':x['data'].get('media_type'),'status':x['status'],
                     'review':x['data'].get('review_state'),'rights':x['data'].get('rights'),
                     'bytes':x['data'].get('byte_count'),'created':x.get('created_at')}
                    for x in core.records('revision',limit=500)]

    @app.get('/api/component-catalog')
    async def component_catalog():
        from ..capability_registry import load_catalog
        return load_catalog()

    @app.get('/api/concepts')
    async def concepts(q:str='',limit:int=60):
        if not 1<=limit<=100 or len(q)>80:raise CoreError('Invalid concept lookup')
        with session() as (core,_):
            result=[]
            for c in core.iter_records('concept'):
                label=c['data'].get('labels',{}).get('en','')
                if q.casefold() in label.casefold():
                    result.append({'id':c['id'],'label':label})
                if len(result)>=limit:break
            return result

    @app.get('/api/search')
    async def search(q:str,top_k:int=5):
        with session() as (core,_):return core.hybrid_search(q,top_k=top_k)

    @app.post('/api/sources/upload')
    async def upload(file:UploadFile=File(...),title:str=Form(...),source_key:str=Form(...),
                     license_note:str=Form(...),language:str=Form('en'),allow_train:bool=Form(False),
                     concept_ids:str=Form('')):
        if not 1<=len(title.strip())<=256 or not 1<=len(source_key.strip())<=256 or not 1<=len(license_note.strip())<=4096:
            raise CoreError('Title, source key, and actual rights note are required')
        filename=Path(file.filename or 'upload').name
        extension=Path(filename).suffix.casefold()
        if extension not in SUPPORTED:raise CoreError('Unsupported source format')
        if any(x in filename for x in ('\x00','\n','\r')):raise CoreError('Invalid filename')
        concepts=[x.strip() for x in concept_ids.split(',') if x.strip()]
        if len(concepts)>20:raise CoreError('Too many subject links')
        target=None
        try:
            with tempfile.NamedTemporaryFile('wb',delete=False,prefix='expertos-upload-',suffix=extension) as out:
                target=Path(out.name);count=0
                while True:
                    chunk=await file.read(1024*1024)
                    if not chunk:break
                    count+=len(chunk)
                    if count>max_upload:raise CoreError('File exceeds configured upload budget')
                    out.write(chunk)
            if not count:raise CoreError('Empty upload')
            mime=mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            # Common text types must use the exact recognized stream encodings.
            if extension in TEXTUAL: mime='text/plain'
            extracted_stream=None
            if extension in {'.pdf','.epub','.docx'}:
                from ..pipeline.ingestion import LiteratureIngestionPipeline
                body,_=LiteratureIngestionPipeline.extract_text_from_file(str(target))
                if not isinstance(body,str) or len(body.encode('utf-8'))>MAX_EXTRACTED:
                    raise CoreError('Extracted text exceeds Studio safety limit')
                if not body.strip():raise CoreError('No extractable text; OCR is a separate workflow')
                extracted_stream=io.BytesIO(body.encode('utf-8'))
            rights={'store':True,'retrieve':True,'train':bool(allow_train),'redistribute':False}
            with session() as (core,director):
                with core.transaction():
                    artifact=core.register_source(source_key,title,language=language,concept_ids=concepts)
                    with target.open('rb') as stream:
                        result=core.ingest_stream(artifact,stream,media_type=mime,rights=rights,
                            license_note=license_note,concept_ids=concepts,extracted_stream=extracted_stream,
                            metadata={'original_filename':filename,'upload_channel':'source_studio'},
                            extraction_method='studio-upload-v1')
                proposals=director.propose(result['revision_id']) if result.get('segments') else {'created':0}
                return {**result,'suggestions':proposals,'training_started':False,'review_required':True}
        finally:
            if target:target.unlink(missing_ok=True)
            await file.close()

    @app.get('/api/candidates')
    async def candidates(revision:str|None=None):
        with session() as (_,director):return director.candidates(revision=revision)

    @app.post('/api/review')
    async def review(payload:ReviewRequest):
        with session() as (core,director):
            if payload.candidate:
                return director.review_candidate(payload.record_id,accept=payload.decision=='accepted',note=payload.note)
            if payload.decision not in {'accepted','rejected'}:raise CoreError('Invalid decision')
            core.review(payload.record_id,decision=payload.decision,note=payload.note)
            return {'status':payload.decision,'record_id':payload.record_id}

    @app.post('/api/sources/rights')
    async def rights(payload:RightsRequest):
        with session() as (core,_):
            core.set_rights(payload.revision_id,{'store':payload.store,'retrieve':payload.retrieve,
                                                'train':payload.train,'redistribute':payload.redistribute},reason=payload.reason)
            return {'status':'updated','revision_id':payload.revision_id}

    @app.get('/api/jobs')
    async def jobs():
        with session() as (_,director):return director.jobs()

    @app.get('/api/annotations')
    async def annotations(task:str|None=None):
        with session() as (_,director):return director.reviewed_annotations(task=task)

    @app.get('/api/datasets/suggest-splits')
    async def suggest_splits(task:str='span_qa'):
        with session() as (_,director):return director.suggest_splits(task=task)

    @app.post('/api/annotations')
    async def annotate(payload:AnnotationRequest):
        with session() as (_,director):
            return director.propose_manual_annotation(task=payload.task,segment_id=payload.segment_id,
                case_id=payload.case_id,question=payload.question,answer=payload.answer,
                text=payload.text,labels=payload.labels)

    @app.post('/api/datasets/release')
    async def release(payload:ReleaseRequest):
        with session() as (_,director):return director.release_dataset(payload.name,payload.assignments,
            demo=payload.demo,trainer=payload.trainer,config=payload.config)

    @app.post('/api/jobs/queue')
    async def queue_job(payload:TrainRequest):
        with session() as (_,director):return {'job_id':director.queue_job(payload.dataset_id,
                                                     trainer=payload.trainer,config=payload.config)}
    # Cognition is opt-in and authorization-bound; the Studio deliberately does
    # not expose automatic plan execution or an arbitrary callable loader.
    @app.post('/api/cognition/goals')
    async def create_goal(payload:GoalRequest):
        with session() as (core,_):
            return {'id':CognitiveEngine(core).goal(payload.title,success=payload.success,
                constraints=payload.constraints,budget=payload.budget)}

    @app.get('/api/cognition/goals/{goal_id}')
    async def get_goal(goal_id:str):
        with session() as (core,_):return CognitiveEngine(core).get_goal(goal_id)

    @app.post('/api/cognition/observe')
    async def observe(payload:ObservationRequest):
        with session() as (core,_):
            v=CognitiveEngine(core).observe(payload.scope,payload.snapshot,
                expected_version=payload.expected_version)
            return {'scope':payload.scope,'version':v}

    @app.get('/api/cognition/state')
    async def state(scope:str):
        with session() as (core,_):return CognitiveEngine(core).state(scope)

    @app.post('/api/cognition/compare')
    async def compare(payload:ChoiceRequest):
        with session() as (core,_):
            return CognitiveEngine(core).compare(payload.goal_id,payload.options,
                weights=payload.weights,minimum_score=payload.minimum_score,
                minimum_margin=payload.minimum_margin)

    @app.post('/api/cognition/plan')
    async def preflight_plan(payload:PlanRequest):
        with session() as (core,_):
            return CognitiveEngine(core).plan(payload.goal_id,payload.steps,
                permissions=payload.permissions)

    @app.get('/api/cognition/capabilities')
    async def choices(task:str,concept_id:str|None=None):
        with session() as (core,_):
            return CognitiveEngine(core).capability_choices(task=task,
                concept_ids=[concept_id] if concept_id else [])

    @app.post('/api/cognition/definitions')
    async def create_definition(payload:DefinitionRequest):
        with session() as (core,_):
            return {'id':DefinitionLibrary(core).propose(payload.concept_id,payload.wording,
                evidence_ids=payload.evidence_ids,scope=payload.scope),'review_required':True}

    @app.post('/api/cognition/definitions/review')
    async def review_definition(payload:DefinitionReviewRequest):
        with session() as (core,_):
            return DefinitionLibrary(core).review(payload.definition_id,accept=payload.accept,note=payload.note)

    @app.get('/api/cognition/definitions')
    async def concept_definitions(concept_id:str):
        with session() as (core,_):
            return DefinitionLibrary(core).for_concept(concept_id)

    @app.get('/api/cognition/readiness')
    async def readiness():
        with session() as (core,_):
            return {'cognition':{'goal_contracts':True,'observed_state':True,
                'decision_method':'deterministic_multicriteria',
                'plan_preflight':True,'plan_auto_execution_exposed':False,
                'verified_skills':True,'learned_planning_policy':False,
                'causal_model_trained':False},
                'services':core.service_health(),'models_automatically_deployed':False}

    @app.post('/api/director/inspect-quality')
    async def inspect_quality(payload:RevisionTargetRequest):
        with session() as (_,director):
            return director.inspect_source_quality(payload.revision_id)

    @app.post('/api/director/leech-bus', deprecated=True)
    @app.post('/api/director/extract-source-candidates')
    async def extract_source_candidates(payload:RevisionTargetRequest):
        with session() as (_,director):
            return director.extract_source_candidates(payload.revision_id,book_title=payload.book_title,default_subdomain=payload.default_subdomain)

    @app.get('/api/director/replay-buffer')
    async def replay_buffer(max_per_subdomain:int=10):
        with session() as (_,director):
            return director.sample_replay_buffer(max_per_subdomain=max_per_subdomain)

    @app.post('/api/cognition/gst-workflow')
    async def gst_workflow(payload:GSTWorkflowRequest):
        with session() as (core,_):
            return CognitiveEngine(core).prepare_gst_return_workflow(
                supplier_gstin=payload.supplier_gstin,
                return_period=payload.return_period,
                invoices=payload.invoices,
                itc_available=payload.itc_available,
            )

    @app.post('/api/synthesis/execute')
    async def execute_synthesis(payload:SynthesisExecuteRequest):
        from ..pipeline.structured_synthesis import StructuredSynthesisCore
        if payload.mode=='excel':
            return StructuredSynthesisCore.build_excel_form_spec(sheet_title=payload.sheet_title,rows_data=payload.rows_data)
        if payload.mode in {'email','chat'}:
            return StructuredSynthesisCore.compose_email_or_chat(
                mode=payload.mode,
                tone=payload.tone,
                recipient_name=payload.recipient_name,
                subject_topic=payload.query or payload.sheet_title,
                key_facts=payload.key_facts or [payload.query],
            )
        return StructuredSynthesisCore.synthesize_code(payload.query)

    return app
