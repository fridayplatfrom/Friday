import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,rmSync } from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {BrowserBridge} from '../bridge.mjs';
const collect=async stream=>{const events=[];for await(const event of stream)events.push(event);return events;};

const token='synthetic-image-jobs-token-01234567890123456789';
const png=Buffer.from('89504e470d0a1a0a00000000','hex');
async function fixture(t,{fail=false,empty=false}={}) {
 let release;const gate=new Promise(resolve=>release=resolve);
 const controller={status:()=>({enabled:true}),isConnected:()=>true,close:async()=>{},async run(job,emit,signal){
   await Promise.race([gate,new Promise(resolve=>signal.addEventListener('abort',resolve,{once:true}))]);
   if(signal.aborted)return;
   if(fail){emit({type:'error',message:'synthetic failure'});return;}
   if(!empty){emit({type:'progress',percent:42,message:'Making the first draft'});emit({type:'image-start',mime:'image/png'});
   emit({type:'image-chunk',index:0,data:png.toString('base64')});emit({type:'image-end'});}
   emit({type:'done',text:''});
 }};
 const directory=mkdtempSync(join(tmpdir(),'harness-image-api-'));
 const bridge=await new BrowserBridge({token,port:0,controller,stateDirectory:directory}).start();
 t.after(async()=>{await bridge.close();rmSync(directory,{recursive:true,force:true});});
 const api=(path,body,headers={})=>fetch(`http://127.0.0.1:${bridge.port}${path}`,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',...headers},...(body?{body:JSON.stringify(body)}:{})});
 return {bridge,api,release,directory};
}
test('local image API authenticates, rejects web origins, validates input and never exposes credentials',async t=>{
 const f=await fixture(t);
 assert.equal((await f.api('/image-jobs',{prompt:'test'},{Authorization:''})).status,401);
 assert.equal((await f.api('/image-jobs',{prompt:'test'},{Origin:'http://evil.test'})).status,403);
 for(const body of [{prompt:''},{prompt:'x'.repeat(1501)},{prompt:'dog',url:'http://evil.test'}])assert.equal((await f.api('/image-jobs',body)).status,400);
 const response=await f.api('/image-jobs',{prompt:'synthetic dog portrait'});assert.equal(response.status,202);const job=await response.json();
 assert.equal((await f.api('/image-jobs',{prompt:'second'})).status,409);
 assert.equal((await f.api('/image-jobs/'+job.id)).status,200);
 assert.equal(JSON.stringify(await (await f.api('/image-jobs/'+job.id)).json()).includes(token),false);
 f.release();await f.bridge.imageJobs.running;
});
test('image API returns real progress and exact saved bytes scoped to its own job; receipts survive restart',async t=>{
 const f=await fixture(t);const job=await(await f.api('/image-jobs',{prompt:'synthetic turtle'})).json();
 f.release();await f.bridge.imageJobs.running;
 const result=await(await f.api('/image-jobs/'+job.id)).json();assert.equal(result.status,'complete');assert.equal(result.percent,42);assert.equal(result.images.length,1);
 const response=await f.api(`/image-jobs/${job.id}/images/${result.images[0].id}`);assert.equal(response.status,200);assert.equal(response.headers.get('content-type'),'image/png');assert.deepEqual(Buffer.from(await response.arrayBuffer()),png);
 assert.equal((await f.api(`/image-jobs/${job.id}/images/00000000-0000-0000-0000-000000000000.png`)).status,404);
 const other=new BrowserBridge({token,stateDirectory:f.directory});assert.equal(other.imageJobs.view(job.id).status,'complete');
 assert.equal((await f.api('/image-jobs/00000000-0000-0000-0000-000000000000')).status,404);
});
test('website errors and image-free completion are honest failures, never successful generated images',async t=>{
 for(const options of [{fail:true},{empty:true}]){const f=await fixture(t,options);const job=await(await f.api('/image-jobs',{prompt:'test'})).json();f.release();await f.bridge.imageJobs.running;const result=f.bridge.imageJobs.view(job.id);assert.equal(result.status,'error');assert.deepEqual(result.images,[]);}
});
test('image jobs respect an active Harness task and a bounded hourly request budget',async t=>{
 const f=await fixture(t);f.bridge.jobs.set('native-task',{});
 assert.equal((await f.api('/image-jobs',{prompt:'test'})).status,409);f.bridge.jobs.clear();
 for(let i=0;i<20;i++)f.bridge.imageJobs.records[i]={createdAt:Date.now(),status:'complete',images:[]};
 assert.equal((await f.api('/image-jobs',{prompt:'test'})).status,429);
});
test('restart marks interrupted image jobs for review without replaying them',async t=>{
 const f=await fixture(t);const job=await(await f.api('/image-jobs',{prompt:'test'})).json();
 const restarted=new BrowserBridge({token,stateDirectory:f.directory});
 assert.equal(restarted.imageJobs.view(job.id).status,'error');assert.match(restarted.imageJobs.view(job.id).message,/not replayed/);
 assert.equal(restarted.jobs.size,0);f.release();await f.bridge.imageJobs.running;
});

test('native continuation waits for the owned image job and submits once after its slot is released',async t=>{
 const f=await fixture(t);const job=await(await f.api('/image-jobs',{prompt:'synthetic portrait'})).json();
 const continuation=collect(f.bridge.request('chatgpt-web','Inspect the existing image job',undefined,{sessionId:'store-agent'}));
 assert.equal(f.bridge.jobs.size,1);assert.match(f.bridge.sessions.get('store-agent').message,/waiting for the browser/);
 assert.equal(f.bridge.journal.events.filter(e=>e.type==='request'&&e.sessionId==='store-agent').length,0);
 f.release();await continuation;
 assert.equal(f.bridge.imageJobs.view(job.id).status,'complete');
 assert.equal(f.bridge.journal.events.filter(e=>e.type==='request'&&e.sessionId==='store-agent').length,1);
 assert.equal(f.bridge.jobs.size,0);
});

test('cancelled continuation does not cancel an accepted image job or submit a later prompt',async t=>{
 const f=await fixture(t);const job=await(await f.api('/image-jobs',{prompt:'synthetic portrait'})).json();
 const controller=new AbortController();const continuation=collect(f.bridge.request('chatgpt-web','Must not submit',controller.signal,{sessionId:'cancel-agent'}));
 controller.abort();await assert.rejects(continuation,{name:'AbortError'});
 assert.equal(f.bridge.jobs.size,1);assert.equal(f.bridge.imageJobs.view(job.id).status,'running');
 f.release();await f.bridge.imageJobs.running;assert.equal(f.bridge.imageJobs.view(job.id).status,'complete');
 assert.equal(f.bridge.journal.events.filter(e=>e.type==='request'&&e.sessionId==='cancel-agent').length,0);
});

test('bridge shutdown settles image waiters without launching a replacement request',async t=>{
 const f=await fixture(t);await f.api('/image-jobs',{prompt:'synthetic portrait'});
 const continuation=collect(f.bridge.request('chatgpt-web','Must not submit after shutdown',undefined,{sessionId:'closing-agent'}));
 const rejected=assert.rejects(continuation,{code:'FRIDAY_BRIDGE_STOPPED'});
 await f.bridge.close();await rejected;
 assert.equal(f.bridge.jobs.size,0);assert.equal(f.bridge.journal.events.filter(e=>e.type==='request'&&e.sessionId==='closing-agent').length,0);
});
