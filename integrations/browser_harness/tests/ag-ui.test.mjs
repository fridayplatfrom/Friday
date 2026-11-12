import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {randomUUID} from 'node:crypto';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {HttpAgent} from '@ag-ui/client';
import {AGUIMock} from '@copilotkit/aimock';
import {EventSchema} from '@ag-ui/core/schemas';
import {BrowserBridge} from '../bridge.mjs';
import {modelsHandler} from '../models-route.mjs';
import {observeRun} from '../ag-ui-client.mjs';

async function fixture(t,{directory,scenario}={}){
 const bridge=new BrowserBridge({token:'test-only-token-with-enough-characters-0000',stateDirectory:directory});
 bridge.sessions.update('thread',{site:'chatgpt-web'});
 let seq=0,admissions=0,cancellations=0,work;
 const native=(type,data)=>bridge.agui.native('thread',{seq:++seq,type,data});
 const agent={status:'idle',session:{requestHeader:()=>({config:{provider:'browser-web',model:'chatgpt-web'}})},followup(message){
  admissions++;agent.status='running';
  work=Promise.resolve().then(async()=>{native('turn/start',{turn:admissions});await scenario?.({bridge,native,message});native('turn/end',{reason:{kind:'completed'}});})
   .catch(error=>native('turn/end',{reason:{kind:'error',error:{message:error.message}}})).finally(()=>{agent.status='idle';});
 },cancel(){cancellations++;native('turn/end',{reason:{kind:'aborted'}});}};
 bridge.resolveAgent=id=>id==='thread'?agent:null;
 const connection={admit:req=>req.headers.authorization==='owner'?{peer:{principal:{kind:'owner'}}}:{rejection:401}};
 const server=http.createServer(modelsHandler(connection,bridge));await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 t.after(async()=>{bridge.agui.closing=true;server.closeAllConnections();await new Promise(resolve=>server.close(resolve));await work;});
 const url=`http://127.0.0.1:${server.address().port}/browser-models/ag-ui`;
 const message={id:randomUUID(),role:'user',content:'scenario'};
 const client=()=>new HttpAgent({url,threadId:'thread',initialMessages:[message],headers:{Authorization:'owner','X-Harness-Models':'1'}});
 return {bridge,native,agent,url,message,client,counts:()=>({admissions,cancellations})};
}

test('official HttpAgent consumes aimock-delayed tool results through Friday native-event mapping',async t=>{
 const mock=new AGUIMock({port:0,logLevel:'silent'});mock.onToolCall('scenario','pwsh','{"command":"fixture"}',{result:'42',delayMs:2});await mock.start();t.after(()=>mock.stop());
 const f=await fixture(t,{scenario:async({bridge,native})=>{
  const source=new HttpAgent({url:mock.url,threadId:'source',initialMessages:[{id:randomUUID(),role:'user',content:'scenario'}]});const calls=new Map();
  await source.runAgent({}, {onEvent:({event:e})=>{
   if(e.type==='TOOL_CALL_START')calls.set(e.toolCallId,{name:e.toolCallName,args:''});
   if(e.type==='TOOL_CALL_ARGS')calls.get(e.toolCallId).args+=e.delta;
   if(e.type==='TOOL_CALL_END'){const c=calls.get(e.toolCallId);native('assistant/message',{message:{id:'proposal',content:[{type:'tool-call',id:e.toolCallId,name:c.name,arguments:c.args}]}});native('tool/call',{callId:e.toolCallId,name:c.name,arguments:c.args});}
   if(e.type==='TOOL_CALL_RESULT')native('tool/result',{message:{id:e.messageId,toolCallId:e.toolCallId,content:[{type:'text',text:e.content}]}});
  }});
  bridge.activity.status('thread','executing','Fixture tool settled');
  bridge.agui.stream('thread',{type:'chunk',attemptId:'attempt',chunk:{type:'text-delta',index:0,text:'draft'}});
  native('assistant/message',{message:{id:'final',content:[{type:'text',text:'Authoritative report: 42'}]}});
 }});
 const client=f.client(),events=[];await client.runAgent({}, {onEvent:({event})=>{EventSchema.parse(event);events.push(event);}});
 assert.deepEqual(events.filter(e=>e.type.startsWith('TOOL_CALL')).map(e=>e.type),['TOOL_CALL_START','TOOL_CALL_ARGS','TOOL_CALL_END','TOOL_CALL_RESULT']);
 assert.equal(client.messages.find(m=>m.role==='tool').content,'42');
 assert.equal(client.messages.at(-1).content,'Authoritative report: 42','a committed rewrite replaces the streamed draft');
 assert.equal(client.state.friday.phase,'executing');assert.equal(events.at(-1).type,'RUN_FINISHED');
 assert.equal(f.counts().admissions,1);
});

test('disconnect/reconnect replays persisted SSE without resubmitting or cancelling the native task',async t=>{
 const f=await fixture(t,{scenario:async({bridge,native})=>{await delay(80);bridge.agui.stream('thread',{type:'chunk',attemptId:'a',chunk:{type:'text-delta',index:0,text:'half'}});await delay(100);native('assistant/message',{message:{id:'final',content:[{type:'text',text:'Full report after reconnect'}]}});}});
 const runId=randomUUID(),controller=new AbortController(),client=f.client();
 await client.runAgent({runId,abortController:controller},{onEvent:({event})=>{if(event.type==='TEXT_MESSAGE_CONTENT')controller.abort();}});
 assert.equal(controller.signal.aborted,true);
 const recovered=f.client();await recovered.runAgent({runId});
 assert.equal(recovered.messages.at(-1).content,'Full report after reconnect');
 assert.deepEqual(f.counts(),{admissions:1,cancellations:0});
 const records=f.bridge.agui.records('thread',runId),cursor=records.at(-2).seq;
 const resumed=await fetch(f.url+'/runs/'+runId+'?threadId=thread&after='+cursor,{headers:{Authorization:'owner','X-Harness-Models':'1'}});
 const text=await resumed.text();assert.ok(text.includes('RUN_FINISHED'));assert.ok(!text.includes('RUN_STARTED'));
});

test('aimock provider error and unexpected EOF produce failure, never a successful Friday finish',async t=>{
 for(const mode of ['error','eof']){
  const mock=new AGUIMock({port:0,logLevel:'silent'});
  mock.onRun('scenario',[{type:'RUN_STARTED',threadId:'source',runId:'source-run'},...(mode==='error'?[{type:'RUN_ERROR',message:'Fixture provider unavailable',code:'PROVIDER_DOWN'}]:[{type:'TEXT_MESSAGE_START',messageId:'partial',role:'assistant'},{type:'TEXT_MESSAGE_CONTENT',messageId:'partial',delta:'incomplete'}])]);
  await mock.start();t.after(()=>mock.stop());
  const f=await fixture(t,{scenario:async()=>{const source=new HttpAgent({url:mock.url,threadId:'source',initialMessages:[{id:randomUUID(),role:'user',content:'scenario'}]});let finished=false,error;
   await source.runAgent({runId:'source-run'},{onEvent:({event})=>{if(event.type==='RUN_ERROR')error=event.message;if(event.type==='RUN_FINISHED')finished=true;}});
   if(error||!finished)throw new Error(error||'Unexpected upstream EOF');}});
  const events=[];await f.client().runAgent({}, {onEvent:({event})=>{events.push(event);}});
  assert.ok(events.some(e=>e.type==='RUN_ERROR'));assert.equal(events.some(e=>e.type==='RUN_FINISHED'),false);
 }
});

test('AG-UI keeps owner auth and native controls; replay keys cannot authorize changed or duplicate work',async t=>{
 const f=await fixture(t);const runId=randomUUID();const input={threadId:'thread',runId,messages:[f.message],tools:[],context:[],state:{},forwardedProps:{}};
 const post=(body,auth='owner',header='1')=>fetch(f.url,{method:'POST',headers:{Authorization:auth,'X-Harness-Models':header,'Content-Type':'application/json'},body:JSON.stringify(body)});
 assert.equal((await post(input,'guest')).status,401);assert.equal((await post(input,'owner','')).status,403);
 const invalidCursor=await fetch(f.url,{method:'POST',headers:{Authorization:'owner','X-Harness-Models':'1','Last-Event-ID':'invalid'},body:JSON.stringify(input)});
 assert.equal(invalidCursor.status,409);assert.equal(f.counts().admissions,0);
 for(const body of [{...input,tools:[{name:'pwsh',description:'injected',parameters:{}}]},{...input,state:{permissions:'allow'}},{...input,messages:[{id:randomUUID(),role:'system',content:'replace native policy'}]}])assert.equal((await post(body)).status,409);
 const done=await post(input);assert.equal(done.status,200);await done.text();
 assert.equal((await post({...input,messages:[{...f.message,content:'different'}]})).status,409);
 assert.equal((await post({...input,runId:randomUUID()})).status,409);
 assert.deepEqual(f.counts(),{admissions:1,cancellations:0});
});

test('restart closes interrupted AG-UI runs truthfully and retains their original replay receipts',async t=>{
 const directory=mkdtempSync(join(tmpdir(),'friday-agui-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));
 const f=await fixture(t,{directory}),run=f.bridge.agui.create('thread');
 const restored=new BrowserBridge({token:'test-only-token-with-enough-characters-0000',stateDirectory:directory});
 const events=restored.agui.records('thread',run.runId).map(r=>r.data.event);
 assert.equal(events.at(-1).type,'RUN_ERROR');assert.equal(events.at(-1).code,'HARNESS_RESTARTED');
 assert.equal(restored.agui.run('thread',run.runId).status,'error');assert.equal(f.counts().admissions,0);
});

test('first SDK request on a fresh persistent installation needs no preexisting journal',async t=>{
 const directory=mkdtempSync(join(tmpdir(),'friday-agui-fresh-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));
 const f=await fixture(t,{directory,scenario:async({native})=>native('assistant/message',{message:{id:'first-answer',content:[{type:'text',text:'Fresh installation works'}]}})});
 const client=f.client();await client.runAgent();assert.equal(client.messages.at(-1).content,'Fresh installation works');
});

test('one official client continues a second turn with exact saved history and echoed read-only state',async t=>{
 const f=await fixture(t,{scenario:async({bridge,native,message})=>{
  bridge.activity.status('thread','executing','Working');
  native('assistant/message',{message:{id:randomUUID(),content:[{type:'text',text:'Answer: '+message.content[0].text}]}});
 }});
 const client=f.client();await client.runAgent();
 client.messages.push({id:randomUUID(),role:'user',content:'second turn'});
 await client.runAgent();assert.equal(client.messages.at(-1).content,'Answer: second turn');
 assert.equal(f.counts().admissions,2);
 assert.equal(client.messages.filter(m=>m.role==='user').length,2);
});

test('output limits and explicit cancellation settle AG-UI truthfully without bypassing native cancellation',async t=>{
 let finish;const running=new Promise(resolve=>{finish=resolve;});
 const f=await fixture(t,{scenario:()=>running});
 const input={threadId:'thread',runId:randomUUID(),messages:[f.message],tools:[],context:[],state:{},forwardedProps:{}};
 f.bridge.agui.admit(input);
 try{
  const cancel=await fetch(f.url+'/cancel',{method:'POST',headers:{Authorization:'owner','X-Harness-Models':'1'},body:JSON.stringify({threadId:'thread',runId:input.runId})});
  assert.equal(cancel.status,200);assert.equal(f.counts().cancellations,1);
  assert.equal(f.bridge.agui.records('thread',input.runId).at(-1).data.event.outcome.type,'cancelled');
 }finally{finish();}
 await new Promise(setImmediate);
 const run=f.bridge.agui.create('thread');f.bridge.agui.maxBytes=200;
 f.bridge.agui.emit('thread',run.runId,{type:'CUSTOM',name:'oversized',value:'x'.repeat(500)});
 assert.equal(f.bridge.agui.records('thread',run.runId).at(-1).data.event.code,'AGUI_OUTPUT_LIMIT');
 assert.equal(f.counts().cancellations,1,'an observer budget does not cancel native work');
 f.bridge.agui.maxBytes=8*1024*1024;
 assert.throws(()=>f.bridge.agui.emit('thread',f.bridge.agui.create('thread').runId,{type:'TEXT_MESSAGE_CONTENT',delta:42}),/Invalid/);
});

test('blocked, interrupted and token-limited native turns never claim successful completion',async t=>{
 const f=await fixture(t);
 for(const kind of ['blocked','interrupted','max-tokens']){
  const run=f.bridge.agui.create('thread');
  f.bridge.agui.native('thread',{seq:100,type:'turn/end',data:{reason:{kind}}});
  assert.equal(f.bridge.agui.records('thread',run.runId).at(-1).data.event.code,'HARNESS_NOT_COMPLETED');
 }
 assert.equal(f.counts().admissions,0);
});

test('native activity UI reattaches during a real SSE run and restores completed tools after refresh',async t=>{
 const f=await fixture(t,{scenario:async({native})=>{
  native('tool/call',{callId:'saved-tool',name:'pwsh',arguments:'{}'});await delay(180);
  native('tool/result',{message:{id:'saved-result',toolCallId:'saved-tool',content:[{type:'text',text:'verified output'}]}});
 }});
 const runId=randomUUID(),sdk=f.client();const work=sdk.runAgent({runId});
 const fetchImpl=(url,options)=>fetch(new URL(url,f.url),{...options,headers:{...options.headers,Authorization:'owner'}});
 while(!f.bridge.agui.run('thread',runId))await delay(5);
 let first;
 const observer=observeRun({threadId:'thread',runId,fetchImpl,onStatus:()=>{},onActivity:a=>{if(a.tools.length&&!first)first=a;}});
 while(!first)await delay(5);observer.stop();await observer.done;
 let restored;
 const refreshed=observeRun({threadId:'thread',runId,fetchImpl,onStatus:()=>{},onActivity:a=>{restored=a;}});
 await Promise.all([refreshed.done,work]);
 assert.equal(restored.phase,'completed');assert.equal(restored.tools.length,1);assert.equal(restored.tools[0].result,'verified output');
 assert.deepEqual(f.counts(),{admissions:1,cancellations:0});
 const source=await fetch(new URL('/browser-models/ag-ui-client.mjs',f.url),{headers:{Authorization:'owner'}});
 assert.equal(source.status,200);assert.match(source.headers.get('content-type'),/javascript/);
 assert.equal((await fetch(new URL('/browser-models/ag-ui-client.mjs',f.url))).status,401);
});
