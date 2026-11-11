import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {SessionStore} from '../session-store.mjs';
import {BrowserAdapter} from '../index.mjs';
import {providerHandoff,providerCheckpoint} from '../handoff.mjs';

const human=text=>({role:'user',content:[{type:'text',text}]}),collect=async stream=>{const out=[];for await(const chunk of stream)out.push(chunk);return out;};
function setup(store=new SessionStore()){
 const calls=[];let fail=false;
 const bridge={sessions:store,jobs:new Map(),journal:{append(){}},activity:{status(){}},
  async *request(site,prompt,_signal,{sessionId}){calls.push({site,prompt});if(fail)throw new Error('Provider unavailable');yield {type:'done',text:'Acknowledged current native history.'};}};
 return {store,calls,adapter:new BrowserAdapter(bridge,{introduction:false}),fail:()=>{fail=true;}};
}
const options=(model,messages)=>({sessionId:'task',model,system:'Workspace Write; native approvals required.',tools:[{name:'pwsh',parameters:{type:'object'}}],messages});

test('Kimi to Gemini and back uses provider-specific acknowledged context and native tool receipts',async()=>{
 const f=setup(),initial=[human('Build ORBIT in the same workspace')];
 await collect(f.adapter.stream(options('kimi-web',initial)));
 const messages=[...initial,{role:'assistant',content:[{type:'tool-call',id:'created',name:'pwsh',arguments:'{}'}]},{role:'tool',toolCallId:'created',content:[{type:'text',text:'Created server.mjs; tests not run'}]},human('Continue with the frontend')];
 await collect(f.adapter.stream(options('gemini-web',messages)));
 assert.match(f.calls[1].prompt,/FRIDAY MODEL HANDOFF: Kimi -> Gemini/);
 assert.match(f.calls[1].prompt,/Build ORBIT/);assert.match(f.calls[1].prompt,/Created server.mjs; tests not run/);assert.match(f.calls[1].prompt,/native approvals required/);
 await collect(f.adapter.stream(options('kimi-web',[...messages,human('Review Gemini changes; do not overwrite them')])));
 assert.match(f.calls[2].prompt,/Gemini -> Kimi/);assert.match(f.calls[2].prompt,/returning/);assert.match(f.calls[2].prompt,/ONLY newly appended/);assert.match(f.calls[2].prompt,/Created server.mjs/);
 assert.equal(f.store.get('task').activeProvider,'kimi-web');assert.equal(f.store.get('task').handoffs.length,2);
 assert.deepEqual(Object.keys(f.store.get('task').providerContexts).sort(),['gemini-web','kimi-web']);
});

test('failed handoff does not acknowledge target delivery and remains safe to retry',async()=>{
 const f=setup();await collect(f.adapter.stream(options('kimi-web',[human('Build it')])));const before=structuredClone(f.store.get('task').providerContexts);
 f.fail();await assert.rejects(collect(f.adapter.stream(options('gemini-web',[human('Build it'),human('Continue')]))),/unavailable/);
 assert.equal(f.store.get('task').activeProvider,'kimi-web');assert.equal(f.store.get('task').pendingHandoff.status,'failed');assert.deepEqual(f.store.get('task').providerContexts,before);
 assert.equal(f.store.get('task').handoffs,undefined);
});

test('saved URLs and provider checkpoints survive restart; rebinding invalidates only that provider',async t=>{
 const dir=mkdtempSync(join(tmpdir(),'friday-handoff-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 const f=setup(new SessionStore(dir));
 for(const [site,url,id]of [['kimi-web','https://www.kimi.ai/chat/saved',1],['gemini-web','https://gemini.google.com/app/saved',2]]){
  f.store.bind({sessionId:'task',site,url,tabId:id});await collect(f.adapter.stream(options(site,[human('Build it')])));
 }
 const restored=new SessionStore(dir);assert.equal(restored.get('task').pairs['kimi-web'].url,'https://www.kimi.ai/chat/saved');
 assert.ok(providerCheckpoint(restored.get('task'),'kimi-web'));assert.ok(providerCheckpoint(restored.get('task'),'gemini-web'));
 restored.bind({sessionId:'task',site:'kimi-web',url:'https://www.kimi.ai/chat/explicit-repair',tabId:3});
 assert.equal(providerCheckpoint(restored.get('task'),'kimi-web'),null);assert.ok(providerCheckpoint(restored.get('task'),'gemini-web'));
});

test('pending tools block a switch, compaction does not trigger a handoff, and compacted history sends a fresh snapshot',async()=>{
 const f=setup();await collect(f.adapter.stream(options('kimi-web',[human('Original task')])));
 const pending=[{role:'assistant',content:[{type:'tool-call',id:'pending',name:'pwsh',arguments:'{}'}]}];
 assert.throws(()=>providerHandoff(f.store.get('task'),options('gemini-web',pending)),/pending native tool/);assert.equal(f.calls.length,1);
 assert.equal(providerHandoff(f.store.get('task'),{...options('gemini-web',pending),purpose:'compaction'}),null);
 await collect(f.adapter.stream(options('gemini-web',[human('Native compacted summary: backend complete; test frontend')])));
 await collect(f.adapter.stream(options('kimi-web',[human('Native compacted summary: backend complete; test frontend')])));
 assert.doesNotMatch(f.calls.at(-1).prompt,/ONLY newly appended/);assert.match(f.calls.at(-1).prompt,/backend complete/);
});

test('handoff retains actual execution receipts independently of an inaccurate compacted summary',()=>{
 const state={activeProvider:'kimi-web',pairs:{'gemini-web':{url:'https://gemini.google.com/app/saved'}},activity:{tools:[{id:'real',name:'pwsh',status:'completed',result:'CREATED empty project folder'}]}};
 const handoff=providerHandoff(state,options('gemini-web',[human('Compacted summary claims server written')]));
 assert.match(handoff.prompt,/CREATED empty project folder/);assert.match(handoff.prompt,/Compaction summaries can be mistaken/);
 assert.equal(handoff.returning,true);
 assert.equal(state.activity.tools.length,1);
});
