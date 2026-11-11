import test from 'node:test';
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';
import {BrowserBridge} from '../bridge.mjs';
import {RequestScheduler} from '../request-scheduler.mjs';

const token='parallel-admission-test-token-01234567890123456789';
const collect=async stream=>{const values=[];for await(const value of stream)values.push(value);return values;};
async function fixture(t,version='0.10.0'){
  const bridge=await new BrowserBridge({token,port:0,timeoutMs:10000,connectionGraceMs:3000}).start();t.after(()=>bridge.close());
  const api=async(route,body)=>{const r=await fetch(`http://127.0.0.1:${bridge.port}${route}`,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});const data=await r.json();if(!r.ok)throw Error(data.error);return data;};
  const poll=()=>api('/poll',{version,sites:['chatgpt-web','gemini-web']});await poll();
  const next=async()=>{for(let i=0;i<80;i++){const result=await poll();if(result.commands.length)return result.commands;await delay(10);}throw Error('Expected dispatch');};
  const run=(session,site='chatgpt-web',signal)=>collect(bridge.request(site,session,signal,{sessionId:session}));
  return {bridge,api,poll,next,run};
}
test('two slots serve mixed providers, queue the third, and keep out-of-order replies in their own chats',async t=>{
  const f=await fixture(t),a=f.run('alpha'),b=f.run('bravo','gemini-web'),c=f.run('charlie');
  const commands=await f.next();assert.equal(commands.length,2);
  assert.deepEqual(commands.map(c=>c.sessionId),['alpha','bravo']);
  assert.equal(f.bridge.sessions.get('charlie').phase,'queued');
  assert.deepEqual(await f.api('/status').then(s=>[s.activeRequests,s.queuedRequests,s.pending,s.maxConcurrentRequests]),[2,1,3,2]);
  const [ja,jb]=commands;
  await f.api('/event',{id:jb.id,type:'done',text:'BRAVO_ONLY'});assert.equal((await b).at(-1).text,'BRAVO_ONLY');
  const [jc]=await f.next();assert.equal(jc.sessionId,'charlie');
  await f.api('/event',{id:jc.id,type:'done',text:'CHARLIE_ONLY'});await f.api('/event',{id:ja.id,type:'done',text:'ALPHA_ONLY'});
  assert.equal((await a).at(-1).text,'ALPHA_ONLY');assert.equal((await c).at(-1).text,'CHARLIE_ONLY');
  assert.equal(f.bridge.journal.list('alpha').some(e=>e.type==='reply'&&e.data.text==='BRAVO_ONLY'),false);
  assert.equal((await f.api('/status')).pending,0);
});
test('two distinct ChatGPT sessions run together; a second request in one conversation cannot overlap',async t=>{
  const f=await fixture(t),a=f.run('chat-a'),b=f.run('chat-b');let sameDone=false;
  const same=f.run('chat-a','gemini-web').then(value=>{sameDone=true;return value;});
  const jobs=await f.next();assert.equal(jobs.length,2);assert.ok(jobs.every(j=>j.site==='chatgpt-web'));
  const ja=jobs.find(j=>j.sessionId==='chat-a'),jb=jobs.find(j=>j.sessionId==='chat-b');
  await f.api('/event',{id:jb.id,type:'done',text:'B'});await b;assert.deepEqual((await f.poll()).commands,[]);assert.equal(sameDone,false);
  await f.api('/event',{id:ja.id,type:'done',text:'A'});await a;const [next]=await f.next();assert.equal(next.sessionId,'chat-a');assert.equal(next.site,'gemini-web');
  await f.api('/event',{id:next.id,type:'done',text:'A handoff'});await same;
});
test('queued cancellation submits nothing; active cancellation frees only its own slot and rejects late events',async t=>{
  const f=await fixture(t),ac=new AbortController(),cc=new AbortController();
  const a=f.run('a','chatgpt-web',ac.signal),aError=assert.rejects(a,{name:'AbortError'}),b=f.run('b','gemini-web');
  const c=f.run('c','chatgpt-web',cc.signal),cError=assert.rejects(c,{name:'AbortError'});
  const jobs=await f.next();cc.abort();await cError;assert.equal(f.bridge.journal.list('c').some(e=>e.type==='request'),false);
  ac.abort();await aError;
  assert.equal(f.bridge.jobs.size,1);assert.equal(f.bridge.sessions.get('c').phase,'cancelled');
  await assert.rejects(f.api('/event',{id:jobs.find(j=>j.sessionId==='a').id,type:'done',text:'late'}),/expired/);
  await f.api('/event',{id:jobs.find(j=>j.sessionId==='b').id,type:'done',text:'B survived'});assert.equal((await b).at(-1).text,'B survived');
});
test('old Chrome workers remain serial while new requests wait rather than fail as busy',async t=>{
  const f=await fixture(t,'0.9.7'),a=f.run('old-a'),b=f.run('old-b');
  const [ja]=await f.next();assert.equal(f.bridge.scheduler.limit,1);assert.equal(f.bridge.scheduler.queue.length,1);
  await f.api('/event',{id:ja.id,type:'done',text:'a'});await a;
  const [jb]=await f.next();await f.api('/event',{id:jb.id,type:'done',text:'b'});await b;
});
test('cancellation at the instant a queued slot is granted clears queued UI and never creates a request',async t=>{
 const f=await fixture(t),a=f.run('a'),b=f.run('b'),cancel=new AbortController();
 const c=f.run('c','chatgpt-web',cancel.signal),rejected=assert.rejects(c,{name:'AbortError'});
 const item=f.bridge.scheduler.queue[0],resolve=item.resolve;item.resolve=release=>{cancel.abort();resolve(release);};
 const jobs=await f.next();await f.api('/event',{id:jobs[0].id,type:'done',text:'a'});await a;await rejected;
 assert.equal(f.bridge.sessions.get('c').phase,'cancelled');assert.equal(f.bridge.journal.list('c').some(e=>e.type==='request'),false);
 await f.api('/event',{id:jobs[1].id,type:'done',text:'b'});await b;assert.equal((await f.api('/status')).pending,0);
});
test('failed inference frees a slot without cancelling the other provider or replaying its request',async t=>{
  const f=await fixture(t),a=f.run('fail'),failed=assert.rejects(a,/quota/),b=f.run('keep','gemini-web'),c=f.run('queued');
  const jobs=await f.next();await f.api('/event',{id:jobs[0].id,type:'error',message:'quota'});await failed;
  const [jc]=await f.next();await f.api('/event',{id:jc.id,type:'done',text:'new'});await c;
  await f.api('/event',{id:jobs[1].id,type:'done',text:'kept'});await b;
  assert.equal(f.bridge.journal.list('keep').filter(e=>e.type==='request').length,1);
});
test('failed durable setup never exposes an orphaned dispatchable job and releases its slot',async t=>{
 const f=await fixture(t),update=f.bridge.sessions.update.bind(f.bridge.sessions);
 f.bridge.sessions.update=(id,changes)=>{const result=update(id,changes);if(changes.jobId)throw Error('Simulated durable state failure');return result;};
 await assert.rejects(f.run('storage-fault'),/durable state failure/);
 assert.equal(f.bridge.jobs.size,0);assert.equal(f.bridge.scheduler.active.size,0);assert.deepEqual((await f.poll()).commands,[]);
 f.bridge.sessions.update=update;const next=f.run('healthy');const [job]=await f.next();await f.api('/event',{id:job.id,type:'done',text:'OK'});assert.equal((await next).at(-1).text,'OK');
});
test('admission skips a locked conversation, preserves eligible FIFO order, and shutdown rejects queued work',async()=>{
  const gate=new RequestScheduler(2),releaseA=gate.acquire('a'),releaseB=gate.acquire('b');
  const a2=gate.acquire('a');let cStarted=false;const c=gate.acquire('c').then(release=>{cStarted=true;return release;});
  releaseB();const releaseC=await c;assert.equal(cStarted,true);assert.equal(gate.active.has('a'),true);
  releaseA();const releaseA2=await a2;assert.equal(gate.active.size,2);
  const queued=gate.acquire('d');const rejected=assert.rejects(queued,/No request was submitted/);gate.close();await rejected;
  releaseC();releaseA2();assert.equal(gate.active.size,0);
});
