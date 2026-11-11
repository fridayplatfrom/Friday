"""Multimodal registration and timestamp alignment; no invented transcription."""
from pathlib import Path
import io
import json
import math
import shutil
import subprocess
import tempfile
from .store import CoreError, digest


class Media:
    def ingest_image(self,source_key,title,raw,*,rights,license_note,concepts=()):
        from PIL import Image
        if not isinstance(raw,bytes) or len(raw)>20*1024*1024:raise CoreError('Image exceeds budget')
        with Image.open(io.BytesIO(raw)) as image:
            if image.width*image.height>20000000:raise CoreError('Image pixel budget exceeded')
            image.verify()
            dims={'width':image.width,'height':image.height,'dimensions_observed_by':'Pillow'}
            media_type=Image.MIME.get(image.format,'application/octet-stream')
        with self.transaction():
            artifact=self.register_source(source_key,title,source_type='image',concept_ids=concepts)
            return self.ingest(artifact,raw,media_type=media_type,rights=rights,license_note=license_note,
                               concept_ids=concepts,metadata=dims,extraction_method='image-dimensions-v1')

    def ingest_recording(self,source_key,title,raw,*,media_type,rights,license_note,duration_seconds,concepts=()):
        if not media_type.startswith(('audio/','video/')) or type(duration_seconds) not in (int,float) or not math.isfinite(duration_seconds) or not 0<duration_seconds<=86400:
            raise CoreError('Valid media type and duration in (0,86400] required')
        with self.transaction():
            artifact=self.register_source(source_key,title,source_type='recording',concept_ids=concepts)
            return self.ingest(artifact,raw,media_type=media_type,rights=rights,license_note=license_note,
                 concept_ids=concepts,metadata={'duration_seconds':duration_seconds,'duration_origin':'caller_supplied'},
                 extraction_method='original-recording-v1')

    def import_transcript(self,recording,segments,*,language='en',method='human_supplied'):
        """Preserve timed transcript and original media ancestry; remain unreviewed."""
        parent=self.require_source_use(recording,'retrieve')
        if not parent['data']['media_type'].startswith(('audio/','video/')):
            raise CoreError('Transcript requires an original recording')
        if not isinstance(segments,list) or not 1<=len(segments)<=5000:
            raise CoreError('Transcript must contain 1 to 5000 timed segments')
        with self.transaction():
            timed=[];last=-1;lines=[]
            for s in segments:
                if not isinstance(s,dict) or not isinstance(s.get('text'),str) or not s['text'].strip():
                    raise CoreError('Transcript segment needs text')
                selector={'type':'time','start_seconds':s.get('start'),'end_seconds':s.get('end')}
                media_segment=self.add_segment(recording,selector)
                if s['start']<last:raise CoreError('Transcript starts must be ordered')
                last=s['start'];timed.append(media_segment);lines.append(s['text'])
            body='\n'.join(lines)
            artifact=self.register_source('transcript:'+parent['id']+':'+language+':'+digest(body.encode()),
                   parent['data']['title']+' — transcript',source_type='transcript',language=language,
                   family_id=parent['data']['family_id'])
            result=self.ingest(artifact,json.dumps(segments,ensure_ascii=False).encode(),media_type='application/json',
                   extracted_text=body,rights=parent['data']['rights'],license_note=parent['data']['license_note'],
                   parent_revisions=[parent['id']],extraction_method='timed-transcript:'+method,
                   metadata={'timed_segments':segments,'transcription_verified':False})
            start=0;alignments=[]
            for line,media_segment in zip(lines,timed):
                sid=self.add_segment(result['revision_id'],{'type':'text','start':start,'end':start+len(line)})
                self._edge(sid,'aligned_to',media_segment,{'method':method,'review_state':'proposed'})
                alignments.append({'text_segment':sid,'media_segment':media_segment});start+=len(line)+1
            return {**result,'alignments':alignments,'automatic_speech_recognition_performed':False}

    def extract_video_frames(self,revision,*,interval_seconds=5,max_frames=12):
        """Optional bounded FFmpeg extraction, retaining parent timestamps.

        FFmpeg must be installed by the operator. Host OS sandboxing is still
        recommended for hostile media; this is not a codec security sandbox.
        """
        parent=self.require_source_use(revision,'retrieve')
        if not parent['data']['media_type'].startswith('video/'):
            raise CoreError('Video source required')
        if type(interval_seconds) is not int or not 1<=interval_seconds<=3600 or type(max_frames) is not int or not 1<=max_frames<=100:
            raise CoreError('Invalid frame extraction budget')
        program=shutil.which('ffmpeg')
        if not program:raise CoreError('FFmpeg unavailable; no extraction performed')
        duration=parent['data']['metadata'].get('duration_seconds')
        if not duration:raise CoreError('Recording duration required')
        output=[]
        with tempfile.TemporaryDirectory(prefix='expertos-media-') as td:
            if hasattr(self,'verify_asset'):
                source=self.verify_asset(parent['data']['sha256'])
            else:
                source=Path(td)/'input.media';source.write_bytes(self.read_asset(parent['data']['sha256']))
            # One explicitly timed seek per frame; store the requested timestamp,
            # not a claim of frame-accurate decoded PTS.
            for i in range(max_frames):
                timestamp=i*interval_seconds
                if timestamp>=duration:break
                dest=Path(td)/'frame.png'
                cmd=[program,'-nostdin','-v','error','-y','-protocol_whitelist','file,pipe',
                     '-ss',str(timestamp),'-i',str(source),'-frames:v','1','-vf','scale=1024:-2',str(dest)]
                try:subprocess.run(cmd,check=True,capture_output=True,timeout=20)
                except (OSError,subprocess.SubprocessError) as exc:raise CoreError('FFmpeg frame extraction failed') from exc
                if not dest.exists() or dest.stat().st_size>8*1024*1024:raise CoreError('Invalid frame output')
                raw=dest.read_bytes();dest.unlink()
                with self.transaction():
                    from PIL import Image
                    with Image.open(io.BytesIO(raw)) as image:width,height=image.size
                    artifact=self.register_source('frame:'+parent['id']+':'+str(timestamp),
                           parent['data']['title']+' — frame',source_type='video_frame',family_id=parent['data']['family_id'])
                    result=self.ingest(artifact,raw,media_type='image/png',rights=parent['data']['rights'],
                         license_note=parent['data']['license_note'],parent_revisions=[parent['id']],
                         metadata={'width':width,'height':height,'requested_timestamp_seconds':timestamp,
                                   'timestamp_precision':'requested_seek_not_decoded_pts'},extraction_method='ffmpeg-seek-v1')
                    output.append(result)
        return output
