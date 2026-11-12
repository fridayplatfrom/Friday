import {readFileSync} from 'node:fs';
/** Native Settings endpoint. Uses Harness owner authentication, never exposes the pairing token. */
export function modelsHandler(connection, bridge) {
  return async (req, res) => {
    const admission = connection.admit(req);
    if ('rejection' in admission || admission.peer.principal.kind !== 'owner') {
      return bridge.json(res, admission.rejection || 403, { error: 'Harness owner sign-in required.' });
    }
    if(/^(?:127\.0\.0\.1|localhost):\d+$/.test(req.headers.host||''))bridge.harnessOrigin=`${req.socket?.encrypted?'https':'http'}://${req.headers.host}`;
    const url = new URL(req.url, 'http://localhost');
    if(req.method==='GET'&&['/browser-models/ag-ui-client.mjs','/browser-models/interactions.mjs','/browser-models/onboarding-client.mjs','/browser-models/models-navigation.mjs'].includes(url.pathname)){
      const bytes=readFileSync(new URL('./'+url.pathname.split('/').at(-1),import.meta.url));
      res.writeHead(200,{'Content-Type':'text/javascript; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin'});return res.end(bytes);
    }
    if(req.method==='GET'&&url.pathname==='/browser-models/brand/friday.png'){
      const bytes=readFileSync(new URL('./assets/friday.png',import.meta.url));
      res.writeHead(200,{'Content-Type':'image/png','Content-Length':bytes.length,'Cache-Control':'private, max-age=3600','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin'});return res.end(bytes);
    }
    if(req.method==='GET'&&url.pathname.startsWith('/browser-models/files/')) {
      const id=url.pathname.split('/').at(-1);const record=bridge.files.records[id];
      if(!record||record.status==='uploading')return bridge.json(res,404,{error:'File not available.'});
      const bytes=bridge.files.bytes(record);
      const preview=url.searchParams.get('preview')==='1'&&['image/png','image/jpeg','image/webp'].includes(record.mime);
      res.writeHead(200,{'Content-Type':preview?record.mime:'application/octet-stream','Content-Length':bytes.length,
        'Content-Disposition':`${preview?'inline':'attachment'}; filename*=UTF-8''${encodeURIComponent(record.name)}`,
        'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'",'Cross-Origin-Resource-Policy':'same-origin'});return res.end(bytes);
    }
    // Images use the same owner cookie and admission fence as Settings. img tags cannot set custom headers.
    if (req.method === 'GET' && url.pathname.startsWith('/browser-models/media/')) {
      const image = bridge.sessions.readImage(url.pathname.slice('/browser-models/media/'.length));
      if (!image) return bridge.json(res, 404, { error: 'Image not found.' });
      res.writeHead(200, { 'Content-Type': image.mime, 'Content-Length': image.bytes.length,
        'Cache-Control': 'private, max-age=86400', 'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': "default-src 'none'", 'Cross-Origin-Resource-Policy': 'same-origin' });
      return res.end(image.bytes);
    }
    // Custom header prevents cross-origin form submissions, including requests without Origin.
    if (req.headers['x-harness-models'] !== '1') return bridge.json(res, 403, { error: 'Settings request required.' });
    const action = new URL(req.url, 'http://localhost').pathname.split('/').at(-1);
    try {
      if(req.method==='POST'&&url.pathname==='/browser-models/recover-session'){
        const input=await bridge.body(req);
        if(!bridge.recoverSession)throw new Error('Native session recovery is not available yet.');
        return bridge.json(res,200,await bridge.recoverSession(input.sessionId));
      }
      if(req.method==='POST'&&url.pathname.startsWith('/browser-models/workspace-browser/')){
        if(!bridge.workspaceBrowser||!['status','open','review','preview','focus'].includes(action))throw new Error('Workspace browser is not enabled.');
        return bridge.json(res,200,await bridge.workspaceBrowser(action,await bridge.body(req)));
      }
      if(url.pathname==='/browser-models/ag-ui'&&req.method==='POST'){
        const after=Number(req.headers['last-event-id']||0);
        if(!Number.isSafeInteger(after)||after<0||after>bridge.agui.journal.sequence)throw new Error('Invalid event cursor.');
        if(bridge.agui.connections>=8)throw new Error('Too many AG-UI subscribers.');
        const input=await bridge.body(req);
        if(!bridge.resolveAgent?.(input.threadId)&&bridge.recoverSession)await bridge.recoverSession(input.threadId);
        const run=bridge.agui.admit(input);
        return await bridge.agui.serve(req,res,input.threadId,run.runId,after);
      }
      if(url.pathname==='/browser-models/ag-ui/capabilities'&&req.method==='GET')return bridge.json(res,200,{protocolVersion:'1.0',transports:['http-sse'],nativeExecution:true,clientTools:false,clientStateWrites:false,history:'Harness-owned; append one new user message, optionally echoing the exact saved AG-UI transcript',resume:'SSE cursor or same runId; no action replay'});
      if(url.pathname.startsWith('/browser-models/ag-ui/runs/')&&req.method==='GET')return await bridge.agui.serve(req,res,url.searchParams.get('threadId'),decodeURIComponent(action),Number(req.headers['last-event-id']||url.searchParams.get('after')||0));
      if(url.pathname==='/browser-models/ag-ui/cancel'&&req.method==='POST'){
        const input=await bridge.body(req),run=bridge.agui.run(input.threadId,input.runId);
        if(!run)throw new Error('Unknown AG-UI run.');
        if(run.status==='running')bridge.resolveAgent?.(input.threadId)?.cancel({kind:'user'});
        return bridge.json(res,200,{ok:true,alreadyFinished:run.status!=='running'});
      }
      if(req.method==='GET'&&url.pathname.startsWith('/browser-models/activity/')) {
        const after=Number(url.searchParams.get('after')||0);
        if(!Number.isSafeInteger(after)||after<0)throw new Error('Invalid activity cursor.');
        const snapshot=bridge.activity.snapshot(decodeURIComponent(action),after);
        return bridge.json(res,200,after===snapshot.revision?{revision:after,unchanged:true}:snapshot);
      }
      if (req.method === 'GET' && url.pathname.startsWith('/browser-models/session/')) {
        const sessionId=decodeURIComponent(action);
        const {activity,activityScreenshots,...saved}=bridge.sessions.get(sessionId)||{};
        const agent=bridge.resolveAgent?.(sessionId),route=agent?.session?.requestHeader?.()?.config;
        return bridge.json(res, 200, {...saved,site:saved?.site||'chatgpt-web',phase:saved?.phase||'unpaired',files:bridge.files.list(sessionId),nativeSession:{loaded:!!agent,status:agent?.status||'unloaded',provider:route?.provider||null,model:route?.model||null}});
      }
      if(req.method==='GET'&&url.pathname.startsWith('/browser-models/journal/'))return bridge.json(res,200,bridge.journal.list(decodeURIComponent(action)));
      if(req.method==='POST'&&url.pathname.startsWith('/browser-models/transfer/'))return bridge.json(res,200,bridge.fileAction(action,await bridge.body(req)));
      if (req.method === 'GET' && action === 'status') return bridge.json(res, 200, bridge.uiStatus());
      if (req.method !== 'POST' || !['open', 'connect', 'disconnect', 'new-chat', 'test', 'focus', 'two-way','health','refresh-provider','pair-provider'].includes(action)) {
        return bridge.json(res, 404, { error: 'Unknown connection action.' });
      }
      return bridge.json(res, 200, await bridge.uiAction(action, await bridge.body(req)));
    } catch (error) { if(res.headersSent){res.destroy();return;}return bridge.json(res, 409, { error: error.message }); }
  };
}
