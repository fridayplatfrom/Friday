import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { modelsHandler } from '../models-route.mjs';
import { BrowserBridge } from '../bridge.mjs';

test('native Models connection controls use the existing extension and cannot alter an active request',async()=>{
 const bridge=new BrowserBridge({token:'test-token-long-enough-for-local-auth-0000'});
 bridge.lastSeen=Date.now();bridge.enabledSites=['chatgpt-web'];
 assert.equal(bridge.uiStatus().connected,true);assert.deepEqual(bridge.uiStatus().enabledSites,['chatgpt-web']);
 assert.deepEqual(await bridge.uiAction('disconnect',{site:'chatgpt-web'}),{ok:true,queued:true});
 assert.deepEqual(bridge.actions,[{type:'configure-site',site:'chatgpt-web',enabled:false}]);
 for(const site of ['unknown',null,['chatgpt-web']])await assert.rejects(bridge.uiAction('connect',{site}),/Unknown/);
 bridge.jobs.set('running',{});await assert.rejects(bridge.uiAction('connect',{site:'chatgpt-web'}),/active website request/);
 assert.equal(bridge.actions.length,1);
});

test('native Models route requires authenticated owner and Settings header', async t => {
  let calls = 0;
  const bridge = new BrowserBridge({ token: 'test-token-long-enough-for-local-auth-0000', controller: {
    status: () => ({ enabled: false }), open: async site => { calls++; return { site }; }, close: async () => {},
  } });
  const connection = { admit: req => req.headers.authorization === 'owner' ? { peer: { principal: { kind: 'owner' } } }
    : req.headers.authorization === 'guest' ? { peer: { principal: { kind: 'guest' } } } : { rejection: 401 } };
  const server = http.createServer(modelsHandler(connection, bridge));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}/browser-models/`;
  const request = (auth, settings = '1') => fetch(base + 'open', { method: 'POST',
    headers: { Authorization: auth, 'X-Harness-Models': settings }, body: JSON.stringify({ site: 'chatgpt-web' }) });
  assert.equal((await request('none')).status, 401);
  assert.equal((await request('guest')).status, 403);
  assert.equal((await request('owner', '')).status, 403);
  assert.equal(calls, 0);
  const result = await request('owner'); assert.equal(result.status, 200);
  assert.deepEqual(await result.json(), { site: 'chatgpt-web' }); assert.equal(calls, 1);
  const status = await fetch(base + 'status', { headers: { Authorization: 'owner', 'X-Harness-Models': '1' } });
  assert.equal(JSON.stringify(await status.json()).includes(bridge.token), false);
  const image = bridge.sessions.saveImage(Buffer.from('89504e470d0a1a0a', 'hex'), 'image/png');
  const media = auth => fetch(base + 'media/' + image.id, { headers: { Authorization: auth } });
  assert.equal((await media('none')).status, 401);
  assert.equal((await media('guest')).status, 403);
  const ownerImage = await media('owner'); assert.equal(ownerImage.status, 200);
  assert.equal(ownerImage.headers.get('content-type'), 'image/png');
  assert.equal(ownerImage.headers.get('cross-origin-resource-policy'), 'same-origin');
  const file=bridge.files.put('one','page.html',Buffer.from('<script>never execute</script>'));
  const getFile=auth=>fetch(base+'files/'+file.id,{headers:{Authorization:auth}});
  assert.equal((await getFile('none')).status,401);assert.equal((await getFile('guest')).status,403);
  const download=await getFile('owner');assert.equal(download.status,200);
  assert.equal(download.headers.get('content-type'),'application/octet-stream');assert.match(download.headers.get('content-disposition'),/^attachment/);
  assert.equal(await download.text(),'<script>never execute</script>');
  const svg=bridge.files.put('one','drawing.svg',Buffer.from('<svg/>'));
  const preview=await fetch(base+'files/'+svg.id+'?preview=1',{headers:{Authorization:'owner'}});assert.equal(preview.headers.get('content-type'),'application/octet-stream');
  const journal=await fetch(base+'journal/one',{headers:{Authorization:'guest','X-Harness-Models':'1'}});assert.equal(journal.status,403);
  bridge.activity.ensure('one');
  const activity=(auth,settings='1',cursor=0)=>fetch(base+'activity/one?after='+cursor,{headers:{Authorization:auth,'X-Harness-Models':settings}});
  assert.equal((await activity('none')).status,401);
  assert.equal((await activity('guest')).status,403);
  assert.equal((await activity('owner','')).status,403);
  const snapshot=await (await activity('owner')).json();
  assert.equal(snapshot.events[0].type,'RUN_STARTED');assert.equal(JSON.stringify(snapshot).includes(bridge.token),false);
  assert.deepEqual(await (await activity('owner','1',snapshot.revision)).json(),{revision:snapshot.revision,unchanged:true});
  assert.equal((await activity('owner','1','-1')).status,409);
  bridge.resolveAgent=id=>id==='one'?{status:'idle',session:{requestHeader:()=>({config:{provider:'browser-web',model:'gemini-web'}})}}:null;
  const native=await(await fetch(base+'session/one',{headers:{Authorization:'owner','X-Harness-Models':'1'}})).json();
  assert.deepEqual(native.nativeSession,{loaded:true,status:'idle',provider:'browser-web',model:'gemini-web'});
  const unloaded=await(await fetch(base+'session/missing',{headers:{Authorization:'owner','X-Harness-Models':'1'}})).json();assert.equal(unloaded.nativeSession.loaded,false);
  let restored=0;bridge.recoverSession=async id=>{assert.equal(id,'one');restored++;return {ok:true,replayed:false};};
  const recover=(auth,header='1')=>fetch(base+'recover-session',{method:'POST',headers:{Authorization:auth,'X-Harness-Models':header},body:JSON.stringify({sessionId:'one'})});
  assert.equal((await recover('guest')).status,403);assert.equal((await recover('owner','')).status,403);assert.equal(restored,0);
  assert.deepEqual(await(await recover('owner')).json(),{ok:true,replayed:false});assert.equal(restored,1);
});

test('workspace recovery controls require the native owner and cannot be invoked as a connection action',async t=>{
 let calls=0;const bridge=new BrowserBridge({token:'test-token-long-enough-for-local-auth-0000'});
 bridge.workspaceBrowser=async(action,input)=>{calls++;return {action,sessionId:input.sessionId,persistent:true};};
 const connection={admit:req=>req.headers.authorization==='owner'?{peer:{principal:{kind:'owner'}}}:req.headers.authorization==='guest'?{peer:{principal:{kind:'guest'}}}:{rejection:401}};
 const server=http.createServer(modelsHandler(connection,bridge));await new Promise(r=>server.listen(0,'127.0.0.1',r));t.after(()=>new Promise(r=>server.close(r)));
 const url=`http://127.0.0.1:${server.address().port}/browser-models/workspace-browser/review`;
 const request=(auth,header='1')=>fetch(url,{method:'POST',headers:{Authorization:auth,'X-Harness-Models':header},body:JSON.stringify({sessionId:'native',id:'uncertain',decision:'confirmed-applied',revision:2})});
 assert.equal((await request('none')).status,401);assert.equal((await request('guest')).status,403);assert.equal((await request('owner','')).status,403);assert.equal(calls,0);
 assert.equal((await request('owner')).status,200);assert.equal(calls,1);
});
