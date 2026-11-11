"""Registry-driven dispatch, bounded task graphs, approvals, and leased local jobs.

Only explicitly bound Python callables execute. Registry content is never imported
or evaluated as code. Execution is synchronous: call-count and payload budgets are
hard limits; an adapter must sandbox/time-limit a potentially blocking handler.
"""
from datetime import datetime, timedelta, timezone
import secrets
import time
from .store import CoreError, AccessDenied, digest, dumps, now, text


def order_steps(steps):
    if not isinstance(steps,list) or not 1<=len(steps)<=32: raise CoreError('Workflow needs 1 to 32 steps')
    nodes={}
    for step in steps:
        if not isinstance(step,dict) or not isinstance(step.get('id'),str) or not step['id'] or step['id'] in nodes:
            raise CoreError('Each workflow step needs a unique ID')
        if not isinstance(step.get('depends_on',[]),list) or not all(isinstance(x,str) for x in step.get('depends_on',[])):
            raise CoreError('Dependencies must be step IDs')
        nodes[step['id']]=step
    if any(d not in nodes for s in steps for d in s.get('depends_on',[])):
        raise CoreError('Unknown workflow dependency')
    ordered=[];pending=set(nodes)
    while pending:
        ready=sorted(n for n in pending if set(nodes[n].get('depends_on',[]))<=set(ordered))
        if not ready: raise CoreError('Workflow cycle rejected')
        ordered.extend(ready);pending.difference_update(ready)
    return [nodes[n] for n in ordered]


class Runtime:
    def declare_capability(self, alias, *, name, task, concepts=(), permissions=('local_compute',),
                           implemented=False, lifecycle='declared', implementation=None, input_fields=()):
        text(alias,'alias',256);text(name,'name',256);text(task,'task',128)
        if any(not isinstance(x,str) or not x for x in (*permissions,*input_fields)):
            raise CoreError('Permission and input names must be strings')
        with self.transaction():
            existing=self.maybe(alias)
            if existing: return existing['id']
            ids=[self.get(c,'concept')['id'] for c in concepts]
            id=self._new('capability',{'name':name,'task':task,'concept_ids':ids,
                 'permissions':sorted(set(permissions)),'implemented':implemented is True,
                 'lifecycle':lifecycle,'implementation':implementation or {},'input_fields':list(input_fields)},alias=alias)
            for cid in ids: self._edge(id,'requires_concept',cid)
            return id

    def bind(self, capability, handler, *, model_id=None, experimental=False):
        if type(experimental) is not bool:raise CoreError('experimental must be boolean')
        if not callable(handler): raise CoreError('Explicit callable required')
        row=self.get(capability,'capability')
        if row['status']!='active' or not row['data']['implemented'] or row['data']['lifecycle'] in {'planned','retired'}:
            raise CoreError('Planned or unavailable capabilities cannot be bound')
        if model_id:
            model=self.get(model_id,'model')
            self.read_asset(model['data']['weights_sha256'])
            if model['status']!='active' or (model['data']['approval']!='approved' and not experimental):
                raise CoreError('Unapproved model is unavailable without experimental opt-in')
        with self.transaction():
            deployment=self._new('deployment',{'capability_id':row['id'],'model_id':model_id,
                    'runtime_id':self.runtime_id,'health_observed_at':now(),
                    'handler_bound_in_current_process':True,'experimental':experimental is True,
                    'model_bytes_verified':model_id is not None,'framework_load_verified':False})
            self._edge(deployment,'deployment_of',row['id'])
            if model_id:self._edge(deployment,'deployment_of',model_id)
        self._handlers[row['id']]={'deployment_id':deployment,'callable':handler,'model':model_id,'experimental':experimental is True,
                                   'bound_at':now()}
        return self.capability_health(row['id'])

    def capability_health(self, capability):
        row=self.get(capability,'capability'); bound=self._handlers.get(row['id'])
        ready=bool(bound) and row['status']=='active'
        reason='bound_in_this_process' if ready else 'not_bound_in_this_process'
        if bound and self.get(bound['deployment_id'])['status']!='active':
            ready=False;reason='deployment_invalidated'
        if bound and bound['model']:
            m=self.get(bound['model'],'model')
            try: self.read_asset(m['data']['weights_sha256'])
            except (CoreError,OSError): ready=False;reason='model_integrity_failure'
            if m['status']!='active':ready=False;reason='model_affected_by_source_change'
        return {'capability_id':row['id'],'ready':ready,'reason':reason,
                'experimental':bool(bound and bound['experimental']), 'observed_at':now(),
                'independent_accuracy_verified':False}

    def discover(self, *, task=None, concepts=(), only_ready=False):
        ids={self.get(c,'concept')['id'] for c in concepts};out=[]
        for row in self.iter_records('capability'):
            if task and row['data']['task']!=task: continue
            if ids and not ids.intersection(row['data']['concept_ids']): continue
            health=self.capability_health(row['id'])
            if not only_ready or health['ready']: out.append({**row,'runtime':health})
        return out

    def approve_action(self, capability, inputs, *, ttl_seconds=300):
        self.require_curator()
        if type(ttl_seconds) is not int or not 1<=ttl_seconds<=600:
            raise CoreError('Approval lifetime must be 1..600 seconds')
        cap=self.get(capability,'capability')
        token=secrets.token_urlsafe(32)
        with self.transaction():
            self.db.execute('''CREATE TABLE IF NOT EXISTS approvals
                (tenant TEXT NOT NULL,token_hash TEXT NOT NULL,payload_hash TEXT NOT NULL,
                 expires_at TEXT NOT NULL,used INTEGER NOT NULL,PRIMARY KEY(tenant,token_hash))''')
            signature=digest(dumps([cap['id'],cap['version'],inputs]).encode())
            self.db.execute('INSERT INTO approvals VALUES (?,?,?,?,0)',(self.tenant,digest(token.encode()),signature,
                       (datetime.now(timezone.utc)+timedelta(seconds=ttl_seconds)).isoformat()))
            self._audit('action_approved',cap['id'],payload_sha256=signature)
        return token

    def execute(self, capability, inputs, *, permissions=(), approval=None):
        if not isinstance(inputs,dict) or len(dumps(inputs).encode())>64000:
            raise CoreError('Inputs must be a bounded JSON object')
        with self.transaction():
            cap=self.get(capability,'capability');health=self.capability_health(cap['id'])
            if not health['ready']: raise CoreError('Capability is not available: '+health['reason'])
            if not set(cap['data']['permissions'])<=set(permissions):
                raise AccessDenied('Execution permissions are missing')
            if not set(cap['data']['input_fields'])<=inputs.keys(): raise CoreError('Required inputs missing')
            sensitive=bool(set(cap['data']['permissions'])&{'browser_submit','purchase','delete','external_write','shell'})
            if sensitive:
                if not isinstance(approval,str): raise AccessDenied('Explicit one-use human approval required')
                signature=digest(dumps([cap['id'],cap['version'],inputs]).encode())
                try:
                    token=self.db.execute('SELECT * FROM approvals WHERE tenant=? AND token_hash=?',
                                          (self.tenant,digest(approval.encode()))).fetchone()
                except Exception as exc:
                    raise AccessDenied('No approval exists') from exc
                if not token or token['used'] or token['payload_hash']!=signature or token['expires_at']<=now():
                    raise AccessDenied('Approval expired, already consumed, or bound to a different action')
                self.db.execute('UPDATE approvals SET used=1 WHERE tenant=? AND token_hash=?',
                                (self.tenant,digest(approval.encode())))
            self._audit('execution_started',cap['id'],input_sha256=digest(dumps(inputs).encode()))
        start=time.monotonic()
        try:
            value=self._handlers[cap['id']]['callable'](inputs)
            if len(dumps(value).encode())>256000: raise CoreError('Output budget exceeded')
        except Exception as error:
            with self.transaction(): self._audit('execution_failed',cap['id'],error_type=type(error).__name__)
            raise CoreError('Capability execution failed: '+type(error).__name__) from error
        with self.transaction(): self._audit('execution_completed',cap['id'],elapsed_seconds=time.monotonic()-start)
        return {'capability_id':cap['id'],'result':value,'experimental':health['experimental'],
                'execution_recorded':True,'claims_verified':False}

    def create_workflow(self, name, steps):
        text(name,'workflow name',256)
        ordered=order_steps(steps)
        for step in ordered:
            cap=self.get(step.get('capability'),'capability')
            if not cap['data']['implemented']:raise CoreError('Workflow contains unimplemented capability')
            if not isinstance(step.get('inputs',{}),dict):raise CoreError('Step inputs must be an object')
        with self.transaction():
            return self._new('workflow',{'name':name,'steps':ordered,'execution_mode':'bounded_synchronous'})

    def run_workflow(self, workflow, *, permissions=(), approvals=None, cancelled=lambda:False):
        row=self.get(workflow,'workflow');results={};trace=[]
        for step in row['data']['steps']:
            if cancelled(): return {'status':'cancelled','results':results,'trace':trace}
            inputs=dict(step.get('inputs',{}))
            # Explicit dependency handoff; source text cannot add steps or code.
            inputs['upstream']={d:results[d] for d in step.get('depends_on',[])}
            try:
                result=self.execute(step['capability'],inputs,permissions=permissions,
                                    approval=(approvals or {}).get(step['id']))
            except CoreError as exc:
                trace.append({'step':step['id'],'status':'failed','reason':str(exc)})
                return {'status':'failed','results':results,'trace':trace}
            results[step['id']]=result['result'];trace.append({'step':step['id'],'status':'completed'})
        return {'status':'completed','results':results,'trace':trace}

    def enqueue(self, workflow, idempotency_key, *, max_attempts=3):
        self.get(workflow,'workflow');text(idempotency_key,'idempotency_key',256)
        if type(max_attempts) is not int or not 1<=max_attempts<=10:raise CoreError('Invalid retry budget')
        with self.transaction():
            key='job:'+idempotency_key;old=self.maybe(key)
            wid=self.get(workflow)['id']
            if old:
                if old['data']['workflow_id']!=wid:raise CoreError('Idempotency key already used for different workflow')
                return old['id']
            return self._new('job',{'workflow_id':wid,'attempts':0,'max_attempts':max_attempts,
                    'lease':None,'lease_expires':None},alias=key,status='queued')

    def claim_job(self, job, *, lease_seconds=60):
        if type(lease_seconds) is not int or not 1<=lease_seconds<=3600:raise CoreError('Invalid lease')
        with self.transaction():
            row=self.get(job,'job');data=row['data']
            reclaim=row['status']=='running' and data['lease_expires']<=now()
            if row['status'] not in {'queued','retry'} and not reclaim:raise CoreError('Job is not claimable')
            if data['attempts']>=data['max_attempts']:raise CoreError('Retry budget exhausted')
            token=secrets.token_urlsafe(24)
            self._change(job,data={**data,'attempts':data['attempts']+1,'lease':digest(token.encode()),
                 'lease_expires':(datetime.now(timezone.utc)+timedelta(seconds=lease_seconds)).isoformat()},status='running')
            return token

    def finish_job(self, job, lease, *, success):
        if type(success) is not bool:raise CoreError('success must be boolean')
        with self.transaction():
            row=self.get(job,'job');data=row['data']
            if row['status']!='running' or data['lease_expires']<=now() or digest(lease.encode())!=data['lease']:
                raise CoreError('Stale job lease or job cancelled')
            self._change(job,data={**data,'lease':None,'lease_expires':None},
                         status='completed' if success else 'retry' if data['attempts']<data['max_attempts'] else 'failed')

    def cancel_job(self, job):
        with self.transaction():
            row=self.get(job,'job')
            if row['status'] in {'queued','retry','running'}:self._change(job,status='cancelled')

    def mark_implemented(self,capability,*,implementation,validation_reference):
        """Operator records an installed implementation; does not bind or promote a model."""
        self.require_curator();text(validation_reference,'validation reference',4096)
        if not isinstance(implementation,dict) or not implementation:
            raise CoreError('Implementation identity is required')
        with self.transaction():
            row=self.get(capability,'capability')
            if row['status']!='active':raise CoreError('Capability is retired or unavailable')
            self._change(row['id'],data={**row['data'],'implemented':True,'lifecycle':'implemented',
                         'implementation':implementation,'implementation_validation':validation_reference})
            self._audit('implementation_registered',row['id'])
