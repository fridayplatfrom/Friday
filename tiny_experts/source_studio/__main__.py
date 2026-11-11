"""Launch ExpertOS Source Studio or one bounded local training job.

EXPERTOS_STUDIO_TOKEN must be a 24+ character secret for the web application.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from ..knowledge_core.store import CoreError
from ..knowledge_services import EnhancedCore
from .director import TrainingDirector


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--tenant',default='local')
    sub=p.add_subparsers(dest='cmd',required=True)
    server=sub.add_parser('serve')
    server.add_argument('--port',type=int,default=8766)
    server.add_argument('--without-worker',action='store_true')
    sub.add_parser('worker-once')
    sub.add_parser('doctor')
    a=p.parse_args(argv)
    if a.cmd=='serve':
        if not 1<=a.port<=65535:p.error('port out of range')
        token=os.environ.get('EXPERTOS_STUDIO_TOKEN','')
        if len(token)<24:p.error('Set EXPERTOS_STUDIO_TOKEN to a random secret of at least 24 characters')
        from .app import create_app
        app=create_app(a.root,token=token,tenant=a.tenant)
        if not a.without_worker:
            def poller():
                while True:
                    args=[sys.executable,'-m','tiny_experts.source_studio','--root',str(a.root),
                          '--tenant',a.tenant,'worker-once']
                    try:
                        subprocess.run(args,check=False,timeout=900,stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    except (OSError,subprocess.TimeoutExpired):
                        pass
                    time.sleep(4)
            threading.Thread(target=poller,daemon=True,name='source-studio-worker').start()
        import uvicorn
        uvicorn.run(app,host='127.0.0.1',port=a.port,access_log=False,proxy_headers=False,server_header=False)
        return 0
    try:
        with EnhancedCore(a.root,tenant=a.tenant,actor='studio-local-worker',curator=True,allow_network=False) as core:
            core.bootstrap(); director=TrainingDirector(core)
            result=(director.worker_once() if a.cmd=='worker-once' else
                    {'status':'ok','policy':director.policy(),'sources':len(core.records('revision')),
                     'queued_jobs':sum(x['state']=='queued' for x in director.jobs()),
                     'models':core.service_health()['models'],'automatic_deployment':False})
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
            return 1 if result.get('status')=='failed' else 0
    except (CoreError,OSError,ValueError) as error:
        print(json.dumps({'status':'failed','error_type':type(error).__name__,'detail':str(error)[:500]}))
        return 1

if __name__=='__main__':raise SystemExit(main())
