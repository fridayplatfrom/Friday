"""ASR and learned translation as source-derived, unreviewed representations."""
from pathlib import Path
import io
import json
import math
import re
import shutil
import subprocess
import tempfile
from ..knowledge_core.store import CoreError, digest, dumps
from .models import ModelUnavailable


def probe_duration(path, *, maximum, timeout=20):
    ffprobe=shutil.which('ffprobe')
    if not ffprobe: raise ModelUnavailable('FFprobe is required for recorded-media inspection')
    try:
        result=subprocess.run([ffprobe,'-v','error','-protocol_whitelist','file,pipe',
             '-show_entries','format=duration','-of','json',str(path)],
             check=True,capture_output=True,timeout=timeout)
        duration=float(json.loads(result.stdout)['format']['duration'])
    except (OSError,subprocess.SubprocessError,ValueError,KeyError) as exc:
        raise CoreError('Recording duration could not be measured') from exc
    if not math.isfinite(duration) or not 0<duration<=maximum:
        raise CoreError('Recording exceeds permitted duration')
    return duration


def protect_terms(value, glossary):
    if not isinstance(glossary,dict) or len(glossary)>100:
        raise CoreError('Glossary must be a bounded source-to-target phrase mapping')
    if re.search(r'XQZTERM\d+ZQX',value): raise CoreError('Input contains reserved terminology marker')
    protected={};output=value
    # Protect explicit formula/code blocks first, then longest glossary terms.
    targets={m.group():m.group() for m in re.finditer(r'`[^`\n]{1,512}`|\$[^$\n]{1,512}\$',value)}
    for source,target in glossary.items():
        if not isinstance(source,str) or not source or not isinstance(target,str) or not target or len(source)>256 or len(target)>256:
            raise CoreError('Invalid terminology entry')
        targets[source]=target
    for source in sorted(targets,key=len,reverse=True):
        pattern=re.compile(r'(?<!\w)'+re.escape(source)+r'(?!\w)')
        def replace(match):
            marker=f'XQZTERM{len(protected)}ZQX';protected[marker]=targets[source];return marker
        output=pattern.sub(replace,output)
    return output,protected


def restore_terms(value,protected):
    if not isinstance(value,str) or not value.strip() or len(value)>65536:
        raise CoreError('Translation returned empty or oversized text')
    for marker,target in protected.items():
        if value.count(marker)!=1: raise CoreError('Translation altered a protected term; review required')
        value=value.replace(marker,target)
    if re.search(r'XQZTERM\d+ZQX',value): raise CoreError('Unexpected translation marker')
    return value


def numeric_tokens(value):
    return sorted(re.findall(r'(?<!\w)[+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?',value))


class Language:
    def import_recording_file(self,source_key,title,path,*,media_type,rights,license_note,concepts=()):
        path=Path(path).resolve()
        if not media_type.startswith(('audio/','video/')):raise CoreError('Audio/video MIME type required')
        if path.is_symlink() or not path.is_file() or path.stat().st_size>self.limits.stream_bytes:
            raise CoreError('Recording missing or too large')
        duration=probe_duration(path,maximum=self.limits.audio_duration_seconds)
        artifact=self.register_source(source_key,title,source_type='recording',concept_ids=concepts)
        with path.open('rb') as stream:
            return self.ingest_stream(artifact,stream,media_type=media_type,rights=rights,license_note=license_note,
                concept_ids=concepts,metadata={'duration_seconds':duration,'duration_origin':'ffprobe'},
                extraction_method='stream-recording-v1')

    def transcribe(self,revision,*,language=None,cancelled=lambda:False):
        provider=self.asr_provider
        if provider is None:raise ModelUnavailable('ASR model is not configured; no transcription was performed')
        parent=self.require_source_use(revision,'retrieve')
        if not parent['data']['media_type'].startswith(('audio/','video/')):raise CoreError('Recording required')
        source=self.verify_asset(parent['data']['sha256'])
        measured=probe_duration(source,maximum=self.limits.audio_duration_seconds)
        declared=parent['data']['metadata'].get('duration_seconds')
        if type(declared) not in (int,float) or abs(measured-declared)>max(1.0,.01*measured):
            raise CoreError('Declared and measured recording duration differ')
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg:raise ModelUnavailable('FFmpeg is required for bounded audio extraction')
        segments=[];start=0.0;detected=language
        with tempfile.TemporaryDirectory(prefix='expertos-asr-') as td:
            while start<measured:
                if cancelled():raise CoreError('Operation cancelled')
                self.require_source_use(parent['id'],'retrieve')
                length=min(self.limits.audio_chunk_seconds,measured-start)
                clip=Path(td)/'chunk.wav'
                try:
                    subprocess.run([ffmpeg,'-nostdin','-v','error','-y','-protocol_whitelist','file,pipe',
                         '-ss',str(start),'-i',str(source),'-t',str(length),'-vn','-ac','1','-ar','16000',
                         '-acodec','pcm_s16le',str(clip)],check=True,capture_output=True,timeout=60)
                except (OSError,subprocess.SubprocessError) as exc:raise CoreError('Audio extraction failed') from exc
                if clip.stat().st_size>int(length*32000)+65536:raise CoreError('Unexpected audio output size')
                result=provider.transcribe_chunk(clip,language=language)
                if not isinstance(result,dict) or not isinstance(result.get('segments'),list):raise CoreError('Malformed ASR output')
                observed=result.get('language')
                if not isinstance(observed,str) or not observed or len(observed)>32:raise CoreError('Invalid ASR language')
                if detected is None:detected=observed
                last=-1.0
                for item in result['segments']:
                    if not isinstance(item,dict):raise CoreError('Invalid ASR segment')
                    a,b,value=item.get('start'),item.get('end'),item.get('text')
                    if not all(type(x) in (int,float) and math.isfinite(x) for x in (a,b)) or not 0<=a<b<=length+.15 or a<last:
                        raise CoreError('ASR timestamp outside chunk or out of order')
                    if not isinstance(value,str) or not value.strip() or len(value)>8192:raise CoreError('Invalid ASR text')
                    segments.append({'start':start+a,'end':min(start+b,measured),'text':value.strip()})
                    last=a
                    if len(segments)>self.limits.max_transcript_segments:raise CoreError('Transcript segment budget exceeded')
                start+=length
        if not segments:return {'status':'no_speech_detected','revision_id':parent['id'],
                                'model_id':provider.identity,'indexed':False}
        if len(dumps(segments).encode())>2*1024**2:raise CoreError('Transcript publication budget exceeded')
        if cancelled():raise CoreError('Operation cancelled')
        with self.transaction():
            self.require_source_use(parent['id'],'retrieve')
            result=self.import_transcript(parent['id'],segments,language=detected,method='asr-'+provider.identity[:24])
            record=self.get(result['revision_id'])
            self._change(record['id'],data={**record['data'],'metadata':{**record['data']['metadata'],
                'model_id':provider.identity,'automatic_speech_recognition_performed':True,
                'measured_duration_seconds':measured,'chunk_seconds':self.limits.audio_chunk_seconds,
                'word_error_rate':None,'human_verified':False}})
            self._audit('asr_completed',record['id'],model_id=provider.identity,segment_count=len(segments))
        return {**result,'status':'transcribed','automatic_speech_recognition_performed':True,
                'model_id':provider.identity,'word_error_rate':None,'review_state':'unreviewed'}

    def translate_segment(self,segment,target_language,*,glossary=None,cancelled=lambda:False):
        provider=self.translation_provider
        if provider is None:raise ModelUnavailable('Translation model is not configured')
        proof=self.evidence(segment)
        if not proof['text']:raise CoreError('Translation requires a text segment')
        parent=self.require_source_use(proof['revision_id'],'retrieve')
        source_language=parent['data']['language']
        if source_language==target_language:raise CoreError('Source and target languages must differ')
        if not isinstance(target_language,str) or not target_language or len(target_language)>32:raise CoreError('Invalid language')
        # Use small existing source segments. Never discard tokens to fit a model.
        protected,terms=protect_terms(proof['text'],glossary or {})
        if cancelled():raise CoreError('Operation cancelled')
        generated=provider.translate(protected,source_language=source_language,target_language=target_language)
        generated=restore_terms(generated,terms)
        if numeric_tokens(proof['text'])!=numeric_tokens(generated):
            raise CoreError('Translation changed numeric values; no translated source published')
        if cancelled():raise CoreError('Operation cancelled')
        key='translation:'+proof['segment_id']+':'+target_language+':'+provider.identity+':'+digest(dumps(glossary or {}).encode())
        with self.transaction():
            parent=self.require_source_use(parent['id'],'retrieve')
            artifact=self.register_source(key,parent['data']['title']+' — machine translation',
                  source_type='machine_translation',language=target_language,family_id=parent['data']['family_id'])
            result=self.ingest(artifact,generated.encode(),rights=parent['data']['rights'],
                  license_note=parent['data']['license_note'],parent_revisions=[parent['id']],
                  metadata={'model_id':provider.identity,'source_segment_id':proof['segment_id'],
                            'source_language':source_language,'target_language':target_language,
                            'numeric_check':'matched','semantic_equivalence':'not_verified','generated':True},
                  extraction_method='seq2seq-translation-v1',
                  concept_ids=[x['id'] for x in self.concepts_for(proof['segment_id'])])
            sid=self.add_segment(result['revision_id'],{'type':'text','start':0,'end':len(generated)})
            existing=[e for e in self.edges(sid,relation='aligned_to') if e['dst']==proof['segment_id']]
            if not existing:self._edge(sid,'aligned_to',proof['segment_id'],{'model_id':provider.identity,'review_state':'proposed'})
            translation=None
            for edge in self.edges(sid,relation='derived_from',reverse=True):
                row=self.get(edge['src'])
                if row['kind']=='translation' and row['data'].get('from_id')==proof['segment_id'] and row['data'].get('provenance',{}).get('model_id')==provider.identity:
                    translation=row['id'];break
            if translation is None:
                translation=self.align_translation(proof['segment_id'],sid,method='neural-seq2seq',
                      provenance={'model_id':provider.identity,'source_revision_id':parent['id']})
        return {**result,'status':'translated','translation_id':translation,'segment_id':sid,
                'source_segment_id':proof['segment_id'],'model_id':provider.identity,
                'review_state':'unreviewed','semantic_equivalence':'not_verified'}
