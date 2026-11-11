"""Persistent bounded operations with idempotency, leases, retries and cancellation.

This queue coordinates workers on ONE host using SQLite. Run workers as isolated
processes. It does not provide a cross-host distributed transaction manager.
"""
import json
import secrets
import time
import uuid
from ..knowledge_core.store import CoreError, AccessDenied, dumps, digest, now, text

KINDS={'semantic_index','transcribe','translate','crawl'}


class Operations:
    def enqueue_operation(self,kind,payload,*,idempotency_key,max_attempts=3):
        self.require_curator()
        if kind not in KINDS or not isinstance(payload,dict) or len(dumps(payload).encode())>32000:
            raise CoreError('Invalid operation or payload')
        text(idempotency_key,'idempotency key',256)
        if type(max_attempts) is not int or not 1<=max_attempts<=10:raise CoreError('Invalid attempt budget')
        signature=digest(dumps([kind,payload]).encode())
        with self.transaction():
            row=self.db.execute('SELECT * FROM operations WHERE tenant=? AND idempotency_key=?',
                                (self.tenant,idempotency_key)).fetchone()
            if row:
                if row['payload_hash']!=signature:raise CoreError('Idempotency key reused for different operation')
                return row['id']
            id='operation:'+str(uuid.uuid4());at=now()
            self.db.execute('''INSERT INTO operations(tenant,id,kind,payload,idempotency_key,payload_hash,
                state,attempts,max_attempts,available_at,created_at,updated_at) VALUES(?,?,?,?,?,?,'pending',0,?,?,?,?)''',
                (self.tenant,id,kind,dumps(payload),idempotency_key,signature,max_attempts,time.time(),at,at))
            self._audit('operation_enqueued',id,kind=kind,payload_sha256=signature)
            return id

    def operation(self,id):
        with self.lock:
            row=self.db.execute('SELECT * FROM operations WHERE tenant=? AND id=?',(self.tenant,id)).fetchone()
            if not row:raise CoreError('Operation not found in tenant')
            result=dict(row)
            for k in ('payload','result'):
                result[k]=json.loads(result[k]) if result[k] is not None else None
            return result

    def claim_operation(self,*,lease_seconds=60):
        self.require_curator()
        if type(lease_seconds) is not int or not 1<=lease_seconds<=86400:raise CoreError('Invalid lease')
        clock=time.time()
        with self.transaction():
            self.db.execute('''UPDATE operations SET state='failed',error='attempt_budget_exhausted',updated_at=?
                WHERE tenant=? AND attempts>=max_attempts AND
                (state='pending' OR (state='running' AND lease_until<=?))''',(now(),self.tenant,clock))
            row=self.db.execute('''SELECT id FROM operations WHERE tenant=? AND attempts<max_attempts AND
                ((state='pending' AND available_at<=?) OR (state='running' AND lease_until<=?))
                ORDER BY available_at,created_at,id LIMIT 1''',(self.tenant,clock,clock)).fetchone()
            if not row:return None
            token=secrets.token_hex(24)
            self.db.execute('''UPDATE operations SET state='running',attempts=attempts+1,lease_token=?,
                lease_until=?,updated_at=? WHERE tenant=? AND id=?''',(token,clock+lease_seconds,now(),self.tenant,row['id']))
            self._audit('operation_claimed',row['id'])
            return self.operation(row['id'])

    def _lease(self,id,token):
        row=self.operation(id)
        if row['state']!='running' or not secrets.compare_digest(row['lease_token'] or '',token or '') or row['lease_until']<=time.time():
            raise AccessDenied('Operation cancelled, lease expired, or owned by another worker')
        return row

    def heartbeat_operation(self,id,token,*,lease_seconds=60):
        if type(lease_seconds) is not int or not 1<=lease_seconds<=86400:raise CoreError('Invalid lease')
        with self.transaction():
            self._lease(id,token)
            self.db.execute('UPDATE operations SET lease_until=?,updated_at=? WHERE tenant=? AND id=?',
                            (time.time()+lease_seconds,now(),self.tenant,id))

    def finish_operation(self,id,token,*,result=None,error=None):
        if result is not None and len(dumps(result).encode())>256000:raise CoreError('Operation result exceeds budget')
        with self.transaction():
            row=self._lease(id,token)
            state='succeeded' if error is None else 'pending' if row['attempts']<row['max_attempts'] else 'failed'
            self.db.execute('''UPDATE operations SET state=?,result=?,error=?,available_at=?,
                lease_token=NULL,lease_until=NULL,updated_at=? WHERE tenant=? AND id=?''',
                (state,dumps(result) if result is not None else None,
                 str(error)[:128] if error is not None else None,
                 time.time()+min(300,2**row['attempts']),now(),self.tenant,id))
            self._audit('operation_finished',id,state=state)
        return self.operation(id)

    def cancel_operation(self,id):
        self.require_curator()
        with self.transaction():
            row=self.operation(id)
            if row['state'] in {'succeeded','failed','cancelled'}:return row
            self.db.execute("UPDATE operations SET state='cancelled',lease_token=NULL,lease_until=NULL,updated_at=? WHERE tenant=? AND id=?",(now(),self.tenant,id))
            self._audit('operation_cancelled',id)
        return self.operation(id)

    def work_once(self,*,lease_seconds=None):
        lease_seconds=lease_seconds or self.limits.worker_timeout_seconds+60
        row=self.claim_operation(lease_seconds=lease_seconds)
        if row is None:return {'status':'idle'}
        id,token=row['id'],row['lease_token']
        def cancelled():
            try:self._lease(id,token);return False
            except AccessDenied:return True
        try:
            p=row['payload'];kind=row['kind']
            allowed={'semantic_index':{'max_segments','after'},'transcribe':{'revision','language'},
                     'translate':{'segment','target_language','glossary'},'crawl':{'website','max_pages'}}[kind]
            if set(p)-allowed:raise CoreError('Unexpected operation fields')
            if kind=='semantic_index':result=self.index_semantic(**p,cancelled=cancelled)
            elif kind=='transcribe':result=self.transcribe(**p,cancelled=cancelled)
            elif kind=='translate':result=self.translate_segment(**p,cancelled=cancelled)
            else:result=self.crawl(**p,cancelled=cancelled)
            return self.finish_operation(id,token,result=result)
        except AccessDenied:
            raise
        except Exception as exc:
            # Do not record raw content, credentials or traceback in durable jobs.
            return self.finish_operation(id,token,error=type(exc).__name__)
