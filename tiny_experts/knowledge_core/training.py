"""Reviewed, immutable dataset releases and explicit model promotion gates.

Records document observed runs. This module never invents training metrics or
starts training/deployment merely because a source was uploaded.
"""
import math
from .store import CoreError, AccessDenied, digest, dumps, now, text

TASKS=frozenset('classification retrieval span_qa grammar translation image_labels code_tests browser_trace pretraining'.split())
SPLITS=('train','validation','test')


class Training:
    def annotate(self, task, inputs, target, segment_ids, *, case_id, generated=False):
        if type(generated) is not bool:
            raise CoreError('generated must be boolean')
        if task not in TASKS or not isinstance(inputs,dict) or not segment_ids:
            raise CoreError('Known task, input object, and evidence segments are required')
        text(case_id,'case_id',256)
        if len(dumps([inputs,target]))>64000:
            raise CoreError('Annotation exceeds payload budget')
        with self.transaction():
            proofs=[self.evidence(s) for s in segment_ids]
            if task=='classification' and (not isinstance(target,dict) or not target or not all(isinstance(k,str) and isinstance(v,str) and v for k,v in target.items())):
                raise CoreError('Classification target must be a nonempty label map')
            if task=='classification':
                text(inputs.get('text'),'classification text',32000)
            if task=='span_qa':
                text(inputs.get('question'),'question',4096)
                if not isinstance(target,dict) or set(target)!={'answer','start','end'}:
                    raise CoreError('QA target requires answer,start,end')
                if target['answer'] is None:
                    if target['start'] is not None or target['end'] is not None:
                        raise CoreError('No-answer requires null offsets')
                else:
                    passage=proofs[0]['text'];start,end=target['start'],target['end']
                    if passage is None or type(start) is not int or type(end) is not int or not 0<=start<end<=len(passage) or passage[start:end]!=target['answer']:
                        raise CoreError('QA answer does not match source offsets')
            if task=='browser_trace':
                if inputs.get('redacted') is not True:
                    raise CoreError('Browser traces must be explicitly redacted before annotation')
                def inspect(value):
                    if isinstance(value,dict):
                        for key,item in value.items():
                            if any(s in key.casefold() for s in ('password','authorization','cookie','secret','access_token')):
                                raise CoreError('Credential-bearing trace field rejected')
                            inspect(item)
                    elif isinstance(value,list):
                        for item in value: inspect(item)
                inspect(inputs);inspect(target)
            id=self._new('annotation',{'task':task,'inputs':inputs,'target':target,
                        'segment_ids':[p['segment_id'] for p in proofs],'case_id':case_id,
                        'generated':generated is True,'review_state':'proposed'})
            for proof in proofs:
                self._edge(id,'derived_from',proof['segment_id'])
                self._edge(id,'uses',proof['revision_id'])
            return id

    def freeze_dataset(self, name, assignments, *, demo=False, protocol='source_disjoint'):
        self.require_curator();text(name,'dataset name',256)
        if type(demo) is not bool:raise CoreError('demo must be boolean')
        if not isinstance(assignments,dict) or not assignments or len(assignments)>5000:
            raise CoreError('Supply 1 to 5000 annotation-to-split assignments')
        if protocol!='source_disjoint':
            raise CoreError('Unsupported evaluation protocol; explicit source-disjoint protocol required')
        with self.transaction():
            manifests=[];tasks=set();groups={s:set() for s in SPLITS};cases={s:set() for s in SPLITS};pairs={s:set() for s in SPLITS}
            source_ids=set()
            for aid,split in sorted(assignments.items()):
                if split not in SPLITS: raise CoreError('Unknown split')
                a=self.get(aid,'annotation')
                if a['status']!='active' or (not demo and a['data']['review_state']!='accepted'):
                    raise CoreError('Annotation is inactive or not reviewed')
                task=a['data']['task'];tasks.add(task)
                cases[split].add(a['data']['case_id'])
                pair=digest(dumps([task,a['data']['inputs'],[self.evidence(sid)['text'] for sid in a['data']['segment_ids']]]).encode())
                pairs[split].add(pair)
                for sid in a['data']['segment_ids']:
                    proof=self.evidence(sid)
                    for r in self.source_ancestry(proof['revision_id']):
                        self.require_source_use(r['id'],'train')
                        if not demo and r['data']['review_state']!='accepted':
                            raise CoreError('Training source is not reviewed')
                        source_ids.add(r['id'])
                        groups[split].update({('family',r['data']['family_id']),('hash',r['data']['sha256'])})
                        if r['data'].get('text_sha256'):
                            groups[split].add(('text_hash',r['data']['text_sha256']))
                manifests.append({'annotation_id':a['id'],'annotation_version':a['version'],
                                  'split':split,'sha256':digest(dumps(a['data']).encode())})
            if len(tasks)!=1 or {x['split'] for x in manifests}!=set(SPLITS):
                raise CoreError('A release needs one task and nonempty train, validation, and test partitions')
            for a,b in (('train','validation'),('train','test'),('validation','test')):
                if cases[a]&cases[b] or pairs[a]&pairs[b]:
                    raise CoreError('Case or duplicate-input leakage across splits')
                if not demo and groups[a]&groups[b]:
                    raise CoreError('Source family, revision, or derived-content leakage across splits')
            manifest={'name':name,'task':next(iter(tasks)),'demo':demo is True,'protocol':protocol,
                      'examples':manifests,'source_revisions':sorted(source_ids),'frozen_at':now()}
            sha=self.put_asset(dumps(manifest).encode())
            id=self._new('dataset',{'name':name,'task':next(iter(tasks)),'manifest_sha256':sha,
                                  'demo':demo is True,'frozen':True,'source_revisions':sorted(source_ids)})
            for source in source_ids: self._edge(id,'uses',source)
            for aid in assignments: self._edge(id,'uses',self.get(aid)['id'])
            return id

    def dataset_manifest(self, dataset):
        import json
        row=self.get(dataset,'dataset')
        if row['status']!='active': raise CoreError('Dataset release is affected or unavailable')
        manifest=json.loads(self.read_asset(row['data']['manifest_sha256']))
        for rid in manifest['source_revisions']: self.require_source_use(rid,'train')
        for item in manifest['examples']:
            annotation=self.get(item['annotation_id'],'annotation')
            if annotation['status']!='active' or annotation['version']!=item['annotation_version'] or digest(dumps(annotation['data']).encode())!=item['sha256']:
                raise CoreError('Frozen annotation changed; create a new dataset release')
        return manifest

    def export_dataset(self, dataset, *, partition='train', for_redistribution=False):
        if partition not in SPLITS: raise CoreError('An explicit partition is required')
        with self.transaction():
            manifest=self.dataset_manifest(dataset)
            if for_redistribution:
                for rid in manifest['source_revisions']:
                    self.require_source_use(rid,'redistribute')
            rows=[]
            for item in manifest['examples']:
                if item['split']!=partition: continue
                a=self.get(item['annotation_id'])['data']
                proofs=[self.evidence(sid) for sid in a['segment_ids']]
                row={'id':item['annotation_id'],'task':a['task'],'inputs':a['inputs'],'target':a['target'],
                     'case_id':a['case_id'],'split':partition,'generated':a['generated'],
                     'evidence':proofs,'review':a.get('review'),'dataset_id':self.get(dataset)['id'],
                     'source_id':self.get(proofs[0]['revision_id'])['data']['artifact_id'],
                     'source_revision':proofs[0]['source_sha256'],
                     'source_family_id':self.get(proofs[0]['revision_id'])['data']['family_id']}
                row.update(reviewed=a['review_state']=='accepted',reviewer=(a.get('review') or {}).get('reviewer'))
                if a['task']=='classification':
                    row.update(text=a['inputs']['text'],labels=a['target'])
                if a['task']=='span_qa':
                    row.update(question=a['inputs']['question'],passage=proofs[0]['text'],
                               answer_text=a['target']['answer'],answer_start=a['target']['start'])
                if a['task']=='pretraining':
                    row['text']=proofs[0]['text']
                rows.append(row)
            self._audit('dataset_exported',dataset,partition=partition,records=len(rows),redistribution=for_redistribution)
            return rows

    def record_training_run(self, dataset, *, code_revision, config, tokenizer_sha256=None, observation):
        self.require_curator();text(code_revision,'code revision',256);text(observation,'observation',4096)
        self.dataset_manifest(dataset)
        if not isinstance(config,dict): raise CoreError('Training configuration must be an object')
        if tokenizer_sha256 is not None:
            import re
            if not re.fullmatch('[0-9a-f]{64}',tokenizer_sha256): raise CoreError('Invalid tokenizer checksum')
        with self.transaction():
            id=self._new('training_run',{'dataset_id':self.get(dataset)['id'],'code_revision':code_revision,
                         'config':config,'tokenizer_sha256':tokenizer_sha256,'observation':observation,
                         'reported_by':self.actor,'actual_training_executed_by_core':False})
            self._edge(id,'trained_on',dataset);return id

    def register_model(self, run, weights, *, architecture, metrics=None):
        self.require_curator();text(architecture,'architecture',256)
        r=self.get(run,'training_run')
        self.dataset_manifest(r['data']['dataset_id'])
        with self.transaction():
            sha=self.put_asset(weights)
            id=self._new('model',{'training_run':r['id'],'weights_sha256':sha,'architecture':architecture,
                         'metrics':metrics or {},'approval':'experimental','reported_by':self.actor})
            self._edge(id,'derived_from',r['id']);return id

    def record_evaluation(self, model, dataset, *, metrics, sample_count, protocol, report):
        self.require_curator();model_record=self.get(model,'model');m=self.dataset_manifest(dataset)
        if model_record['status']!='active':raise CoreError('Model is unavailable')
        training=self.get(model_record['data']['training_run'],'training_run')
        training_manifest=self.dataset_manifest(training['data']['dataset_id'])
        def sources_in(manifest,split):
            result=set()
            for row in manifest['examples']:
                if row['split']!=split:continue
                annotation=self.get(row['annotation_id'])['data']
                for sid in annotation['segment_ids']:
                    rid=self.get(sid)['data']['revision_id']
                    for source in self.source_ancestry(rid):
                        result.add(('family',source['data']['family_id']))
                        result.add(('hash',source['data']['sha256']))
            return result
        if not m['demo'] and sources_in(training_manifest,'train')&sources_in(m,'test'):
            raise CoreError('External evaluation overlaps model training sources')
        if type(sample_count) is not int or sample_count<=0 or sample_count>sum(x['split']=='test' for x in m['examples']):
            raise CoreError('Evaluation sample count must match available held-out test examples')
        if not isinstance(metrics,dict) or not metrics or not all(isinstance(k,str) and type(v) in (int,float) and math.isfinite(v) for k,v in metrics.items()):
            raise CoreError('Finite measured metrics required')
        text(protocol,'evaluation protocol',2048);text(report,'evaluation report',8000)
        with self.transaction():
            id=self._new('evaluation',{'model_id':self.get(model)['id'],'dataset_id':self.get(dataset)['id'],
                         'metrics':metrics,'sample_count':sample_count,'protocol':protocol,'report':report,
                         'reported_by':self.actor,'synthetic_or_demo':m['demo'],'executed_by_core':False,
                         'model_weights_sha256':model_record['data']['weights_sha256']})
            self._edge(id,'evaluates',model);self._edge(id,'uses',dataset);return id

    def approve_model(self, model, evaluation, *, criteria, minimum_samples, rationale):
        self.require_curator();text(rationale,'approval rationale',2048)
        if not isinstance(criteria,dict) or not criteria or type(minimum_samples) is not int or minimum_samples<1:
            raise CoreError('Explicit metric criteria and sample minimum required')
        with self.transaction():
            m,e=self.get(model,'model'),self.get(evaluation,'evaluation')
            if m['status']!='active' or e['status']!='active' or e['data']['model_id']!=m['id'] or e['data']['synthetic_or_demo']:
                raise CoreError('Model/evaluation unavailable or experimental evaluation cannot promote')
            self.dataset_manifest(e['data']['dataset_id'])
            if e['data']['model_weights_sha256']!=m['data']['weights_sha256']:
                raise CoreError('Evaluation does not match model artifact')
            run=self.get(m['data']['training_run'],'training_run')
            if self.dataset_manifest(run['data']['dataset_id'])['demo']:
                raise CoreError('Model trained only in demo mode cannot be promoted')
            self.read_asset(m['data']['weights_sha256'])
            if e['data']['sample_count']<minimum_samples: raise CoreError('Insufficient evaluation samples')
            for metric,bounds in criteria.items():
                value=e['data']['metrics'].get(metric)
                if value is None or not isinstance(bounds,dict) or not bounds or set(bounds)-{'min','max'}:
                    raise CoreError('Missing metric or invalid criteria')
                if any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds.values()):
                    raise CoreError('Criteria must be finite')
                if ('min' in bounds and value<bounds['min']) or ('max' in bounds and value>bounds['max']):
                    raise CoreError('Model does not meet promotion criteria')
            self._change(model,data={**m['data'],'approval':'approved','evaluation_id':e['id'],
                         'approved_by':self.actor,'criteria':criteria,'rationale':rationale})
            self._edge(model,'uses',e['data']['dataset_id'])
            self._audit('model_approved',model,evaluation_id=e['id'])

    def impact(self, id):
        with self.lock:
            pending=[self.get(id)['id']];seen=set()
            while pending:
                item=pending.pop()
                if item in seen: continue
                seen.add(item)
                pending.extend(e['src'] for e in self.edges(item,reverse=True)
                               if e['relation'] in {'derived_from','segment_of','uses','trained_on','evaluates','deployment_of'})
            return [{'id':x,'kind':self.get(x)['kind'],'status':self.get(x)['status']} for x in sorted(seen)]

    def export_pretraining(self,dataset,*,partition='train'):
        """Retokenizable original extracted text from only the selected split.

        Evaluation-source exclusion follows the frozen dataset. Cross-project
        benchmark contamination still requires a separately maintained denylist.
        """
        rows=self.export_dataset(dataset,partition=partition)
        revisions=sorted({p['revision_id'] for row in rows for p in row['evidence']})
        result=[]
        for rid in revisions:
            rev=self.require_source_use(rid,'train')
            sha=rev['data'].get('text_sha256')
            if sha:
                result.append({'revision_id':rid,'source_family_id':rev['data']['family_id'],
                    'text':self.read_asset(sha).decode('utf-8'),'sha256':sha,
                    'language':rev['data']['language'],'license_note':rev['data']['license_note'],
                    'partition':partition,'dataset_id':self.get(dataset)['id']})
        return result
