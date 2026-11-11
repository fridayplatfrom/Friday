"""Explicit local-only neural providers. No implicit downloads or remote code.

A manifest verifies the installed bytes; it does not independently verify training
rights, linguistic accuracy, or the identity of the manifest's author.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re
from ..knowledge_core.store import CoreError, digest, dumps


class ModelUnavailable(CoreError):
    pass


def hash_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class ModelProfile:
    directory: Path
    task: str
    identity: str
    metadata: dict

    @classmethod
    def load(cls, directory, task):
        root=Path(directory).expanduser().resolve()
        manifest=root/'expertos-model.json'
        if not root.is_dir() or not manifest.is_file() or manifest.stat().st_size>1024*1024:
            raise ModelUnavailable('Local model directory and expertos-model.json are required')
        try: data=json.loads(manifest.read_text(encoding='utf-8'))
        except (ValueError,UnicodeError) as exc: raise ModelUnavailable('Invalid model manifest') from exc
        if data.get('schema_version')!=1 or data.get('task')!=task or not data.get('license_note'):
            raise ModelUnavailable('Model task/schema/permission metadata mismatch')
        files=data.get('files')
        if not isinstance(files,dict) or not files or len(files)>10000:
            raise ModelUnavailable('Manifest must enumerate model files')
        actual=set()
        for item in root.rglob('*'):
            if item.is_symlink(): raise ModelUnavailable('Model symlinks are not permitted')
            if item.is_file() and item!=manifest: actual.add(item.relative_to(root).as_posix())
        if actual!=set(files): raise ModelUnavailable('Model files do not match manifest')
        for name,sha in files.items():
            path=(root/name).resolve()
            if not path.is_relative_to(root) or not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):
                raise ModelUnavailable('Invalid model artifact path/hash')
            if hash_file(path)!=sha: raise ModelUnavailable('Model checksum mismatch')
        return cls(root,task,digest(dumps(data).encode()),data)


def write_model_manifest(directory, task, *, license_note, source, source_language=None,
                         target_language=None, revision=None):
    if task not in {'embedding','rerank','asr','translation'} or not license_note or not source:
        raise CoreError('Explicit task, provenance and permission note required')
    root=Path(directory).resolve(); files={}
    for path in root.rglob('*'):
        if path.is_symlink(): raise CoreError('Symlink in model directory')
        if path.is_file() and path.name!='expertos-model.json':
            files[path.relative_to(root).as_posix()]=hash_file(path)
    if not files: raise CoreError('Empty model directory')
    data={'schema_version':1,'task':task,'source':source,'revision':revision,
          'license_note':license_note,'source_language':source_language,
          'target_language':target_language,'files':files,
          'independent_quality_verified':False}
    target=root/'expertos-model.json'
    with target.open('x',encoding='utf-8') as stream: json.dump(data,stream,indent=2)
    return data


class SentenceEmbeddingProvider:
    def __init__(self, directory, *, device='cpu', max_tokens=384):
        self.profile=ModelProfile.load(directory,'embedding'); self.identity=self.profile.identity
        try: from sentence_transformers import SentenceTransformer
        except ImportError as exc: raise ModelUnavailable('Install the semantic optional dependencies') from exc
        self.model=SentenceTransformer(str(self.profile.directory),device=device,
               local_files_only=True,trust_remote_code=False,model_kwargs={'use_safetensors':True})
        self.model.max_seq_length=max_tokens
        self.max_tokens=max_tokens

    def _check(self, texts):
        for text in texts:
            if len(self.model.tokenizer.encode(text,add_special_tokens=True))>self.max_tokens:
                raise CoreError('Embedding passage exceeds model token budget; segment more finely instead of truncating')

    def chunk_spans(self, text):
        """Token-budget windows with exact original-character offsets."""
        tokenizer=self.model.tokenizer
        reserve=max([len(tokenizer.encode(p,add_special_tokens=False)) for p in self.model.prompts.values()]+[0])+8
        budget=self.max_tokens-reserve
        if budget<32:raise CoreError('Model prompt leaves insufficient passage budget')
        if len(tokenizer.encode(text,add_special_tokens=True))<=budget:return [(0,len(text))]
        if not getattr(tokenizer,'is_fast',False):
            # Exact whitespace boundaries; fail rather than cutting a giant token.
            spans=[];start=None;end=None
            for match in re.finditer(r'\S+',text):
                if start is None:start=match.start()
                if len(tokenizer.encode(text[start:match.end()],add_special_tokens=True))>budget:
                    if end is None or end<=start:raise CoreError('Unsegmentable over-budget token')
                    spans.append((start,end));start=match.start()
                end=match.end()
            if start is not None:spans.append((start,end))
            return spans
        offsets=tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
        spans=[]
        for i in range(0,len(offsets),max(1,budget-32)):
            window=offsets[i:i+budget]
            if window:spans.append((window[0][0],window[-1][1]))
            if i+budget>=len(offsets):break
        return list(dict.fromkeys(spans))

    def encode_documents(self, texts):
        self._check(texts)
        return self.model.encode_document(texts,batch_size=min(32,len(texts)),normalize_embeddings=True,
                    show_progress_bar=False,convert_to_numpy=True).tolist()

    def encode_query(self, query):
        self._check([query])
        return self.model.encode_query([query],normalize_embeddings=True,show_progress_bar=False,
                    convert_to_numpy=True)[0].tolist()


class CrossEncoderProvider:
    def __init__(self,directory):
        self.profile=ModelProfile.load(directory,'rerank');self.identity=self.profile.identity
        try: from sentence_transformers import CrossEncoder
        except ImportError as exc: raise ModelUnavailable('Install semantic optional dependencies') from exc
        self.model=CrossEncoder(str(self.profile.directory),local_files_only=True,
                   trust_remote_code=False,model_kwargs={'use_safetensors':True},device='cpu')

    def scores(self,question,passages):
        return self.model.predict([(question,p) for p in passages],show_progress_bar=False).tolist()


class FasterWhisperProvider:
    def __init__(self, directory, *, device='cpu', compute_type='int8'):
        self.profile=ModelProfile.load(directory,'asr');self.identity=self.profile.identity
        try: from faster_whisper import WhisperModel
        except ImportError as exc: raise ModelUnavailable('Install the speech optional dependencies') from exc
        self.model=WhisperModel(str(self.profile.directory),device=device,compute_type=compute_type,
                              local_files_only=True,cpu_threads=2,num_workers=1)

    def transcribe_chunk(self,path,*,language=None):
        segments,info=self.model.transcribe(str(path),language=language,task='transcribe',
             beam_size=3,vad_filter=True,condition_on_previous_text=False,word_timestamps=False)
        return {'language':info.language,'segments':[
            {'start':s.start,'end':s.end,'text':s.text,
             'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob} for s in segments]}


class Seq2SeqTranslationProvider:
    """A dedicated translation model, not a general conversational agent.

    One explicitly configured language pair per profile; no implicit language
    detection, token truncation, arbitrary model code, or source rewriting.
    """
    def __init__(self,directory,*,max_input_tokens=384,max_new_tokens=512):
        self.profile=ModelProfile.load(directory,'translation');self.identity=self.profile.identity
        self.source_language=self.profile.metadata.get('source_language')
        self.target_language=self.profile.metadata.get('target_language')
        if not self.source_language or not self.target_language:
            raise ModelUnavailable('Translation profile must declare both languages')
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        except ImportError as exc: raise ModelUnavailable('Install translation optional dependencies') from exc
        self.torch=torch
        self.tokenizer=AutoTokenizer.from_pretrained(str(self.profile.directory),local_files_only=True,trust_remote_code=False)
        self.model=AutoModelForSeq2SeqLM.from_pretrained(str(self.profile.directory),local_files_only=True,
                    trust_remote_code=False,use_safetensors=True).eval()
        self.max_input_tokens=max_input_tokens;self.max_new_tokens=max_new_tokens

    def translate(self,text,*,source_language,target_language):
        if (source_language,target_language)!=(self.source_language,self.target_language):
            raise CoreError('This translation profile does not support the requested language pair')
        encoded=self.tokenizer(text,return_tensors='pt',truncation=False)
        if encoded['input_ids'].shape[1]>self.max_input_tokens:
            raise CoreError('Translation input exceeds token budget; no silent truncation')
        with self.torch.inference_mode():
            output=self.model.generate(**encoded,max_new_tokens=self.max_new_tokens,
                                       num_beams=3,do_sample=False)
        ids=output[0].tolist();eos=self.tokenizer.eos_token_id
        if len(ids)>=self.max_new_tokens and eos is not None and ids[-1]!=eos:
            raise CoreError('Translation generation reached its output budget')
        return self.tokenizer.decode(output[0],skip_special_tokens=True)
