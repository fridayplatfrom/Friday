"""Loopback JSON API sharing the core with the existing Harness plugin.

The plugin's /v1/experts and /v1/source/read paths are preserved. Browser rule
routes delegate only to an installed trusted expertos_bridge package. No model
or network action is enabled automatically. Never expose this as a public API.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
import os
import secrets
from . import KnowledgeCore, CoreError, HarnessCoreAdapter, CoreBookView


class CoreBridgeServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=False
    request_queue_size=8
    def __init__(self,core,token,*,host='127.0.0.1',port=8765):
        if host!='127.0.0.1':raise CoreError('Only IPv4 loopback is allowed')
        if not isinstance(token,str) or len(token)<32 or len(token)>512:raise CoreError('A 32..512-character bearer token is required')
        self.core=core;self.token=token;self.adapter=HarnessCoreAdapter(core)
        super().__init__((host,port),Handler)


class Handler(BaseHTTPRequestHandler):
    server_version='ExpertOSCore/0.1'
    sys_version=''
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass
    def send(self,status,value):
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
        if len(raw)>262144:status=413;raw=b'{"status":"response_budget_exceeded"}'
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(raw)
    def authorized(self):
        host=f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host')!=host or self.headers.get('Origin') or '?' in self.path or '#' in self.path:
            self.send(403,{'status':'origin_or_host_rejected'});return False
        value=self.headers.get('Authorization','').encode()
        if not secrets.compare_digest(value,('Bearer '+self.server.token).encode()):
            self.send(401,{'status':'unauthorized'});return False
        return True
    def do_GET(self):
        if not self.authorized():return
        if self.path=='/health':
            health=self.server.core.service_health() if hasattr(self.server.core,'service_health') else {'status':'ok'}
            self.send(200,{**health,'service':'expertos-knowledge-core','schema_version':1})
        elif self.path=='/v1/experts':
            entries=[]
            for r in self.server.core.discover():
                entries.append({'id':r['id'],'name':r['data']['name'],'task':r['data']['task'],
                     'kind':'registered_capability','ready':r['runtime']['ready'],'experimental':r['runtime']['experimental']})
            self.send(200,{'status':'ok','experts':entries})
        else:self.send(404,{'status':'not_found'})
    def do_POST(self):
        if not self.authorized():return
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:
            self.send(400,{'status':'invalid_framing'});return
        if self.headers.get('Content-Type','').split(';',1)[0].strip().lower()!='application/json':
            self.send(415,{'status':'json_required'});return
        try:length=int(self.headers.get('Content-Length',''))
        except ValueError:length=-1
        if not 2<=length<=64000:self.send(413,{'status':'request_budget_exceeded'});return
        try:
            def pairs(items):
                result={}
                for k,v in items:
                    if k in result:raise CoreError('Duplicate JSON key')
                    result[k]=v
                return result
            def reject_constant(value):raise CoreError('Non-finite JSON constant')
            raw=self.rfile.read(length)
            if len(raw)!=length:raise CoreError('Incomplete JSON body')
            value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject_constant)
            if not isinstance(value,dict):raise CoreError('Object required')
            if any(k in value for k in ('tenant','actor','curator','permissions','approval')):
                raise CoreError('Caller cannot select trusted execution context')
            routes={'/v1/core/directory':'directory','/v1/core/search':'search',
                    '/v1/core/lookup':'lookup','/v1/core/evidence':'evidence'}
            if self.path in routes:
                result={'status':'ok','result':self.server.adapter.handle(routes[self.path],value)}
            elif self.path=='/v1/source/read':
                result=CoreBookView(self.server.core).lookup_document(value['document_id'],value['question'],3)
                result['model_status']='retrieval_only'
            elif self.path=='/v1/action/propose':
                result={'status':'model_unavailable','action':None}
            elif self.path in {'/v1/route','/v1/plan','/v1/form/map','/v1/form/verify','/v1/recover'}:
                names={'/v1/route':'task.task_router','/v1/plan':'task.browser_planner',
                       '/v1/form/map':'task.form_mapper','/v1/form/verify':'task.browser_verifier',
                       '/v1/recover':'task.recovery'}
                capability=self.server.core.maybe(names[self.path])
                if not capability or not self.server.core.capability_health(capability['id'])['ready']:
                    self.send(503,{'status':'browser_rules_not_bound'});return
                result=self.server.core.execute(capability['id'],value,permissions=('local_compute',))['result']
            else:
                self.send(404,{'status':'not_found'});return
            self.send(200,result)
        except (CoreError,ValueError,KeyError,TypeError,UnicodeError,OSError):
            self.send(422,{'status':'rejected'})
        except Exception:
            self.send(500,{'status':'internal_error'})


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True);p.add_argument('--tenant',default='local');p.add_argument('--port',type=int,default=8765)
    p.add_argument('--enable-browser-rules',action='store_true',help='Explicitly bind installed deterministic Harness specialists')
    args=p.parse_args(argv)
    token=os.environ.get('EXPERTOS_BRIDGE_TOKEN','')
    with KnowledgeCore(args.root,tenant=args.tenant,actor='harness-bridge',curator=args.enable_browser_rules) as core:
        core.bootstrap()
        if args.enable_browser_rules:
            from .adapters import bind_browser_rules
            bind_browser_rules(core)
        with CoreBridgeServer(core,token,port=args.port) as server:
            print(f'ExpertOS core bridge on 127.0.0.1:{server.server_port}',flush=True)
            try:server.serve_forever(poll_interval=.1)
            except KeyboardInterrupt:pass


if __name__=='__main__':main()
