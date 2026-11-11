import test from 'node:test';
import assert from 'node:assert/strict';
import {DevelopmentUpdater} from '../extension/development-update.js';

function fixture(){
 let version='0.4.8',target='0.4.9',enabled=true,now=0;const saved={},selfReloads=[],pageReloads=[];
 const pairs=[7,8].map(tabId=>({tabId,url:'https://chatgpt.com/c/'+tabId}));
 const tabs=new Map(pairs.map(pair=>[pair.tabId,{id:pair.tabId,url:pair.url}]));
 const states=new Map([[7,{ok:true,hasDraft:false,isGenerating:false}],[8,{ok:true,hasDraft:false,isGenerating:false}]]);
 const chrome={runtime:{getManifest:()=>({version}),reload:()=>selfReloads.push(version)},
   storage:{local:{async get(key){return {[key]:saved[key]};},async set(value){Object.assign(saved,structuredClone(value));}}},
   tabs:{async get(id){return tabs.get(id);},async query(){return [...tabs.values()];},async sendMessage(id){return states.get(id);},async reload(id){pageReloads.push(id);}}};
 const options={enabled:async()=>enabled,readManifest:async()=>({version:target}),bindings:async()=>pairs,now:()=>now};
 return {chrome,options,saved,pairs,tabs,states,selfReloads,pageReloads,newUpdater:()=>new DevelopmentUpdater(chrome,options),
 setEnabled:value=>enabled=value,setTarget:value=>target=value,setVersion:value=>version=value,tick:()=>now+=4000};
}

test('development update reloads once and restores the same idle tabs',async()=>{
 const f=fixture(),updater=f.newUpdater();assert.equal(await updater.check(()=>false),true);
 assert.equal(f.selfReloads.length,1);assert.deepEqual(f.saved.harnessDevelopmentUpdate.refresh.map(pair=>pair.tabId),[7,8]);
 assert.equal(await updater.check(()=>false),false);assert.equal(f.selfReloads.length,1);
 f.setVersion('0.4.9');await f.newUpdater().restore();assert.deepEqual(f.pageReloads,[7,8]);assert.equal(f.saved.harnessDevelopmentUpdate,null);
});

test('development update discovers exact live URLs even if stale tab-ID reads never return',async()=>{
 const f=fixture();f.chrome.tabs.get=()=>new Promise(()=>{});
 assert.equal(await f.newUpdater().check(()=>false),true);assert.equal(f.selfReloads.length,1);
 f.setVersion('0.4.9');await f.newUpdater().restore();assert.deepEqual(f.pageReloads,[7,8]);
});

test('disabled, busy, unchanged, malformed and actively generating installations never auto reload',async()=>{
 for(const mode of ['disabled','busy','unchanged','malformed','generating']){
   const f=fixture();if(mode==='disabled')f.setEnabled(false);if(mode==='unchanged')f.setTarget('0.4.8');
   if(mode==='malformed')f.setTarget('bad-version');if(mode==='generating')f.states.set(7,{ok:true,hasDraft:false,isGenerating:true});
   assert.equal(await f.newUpdater().check(()=>mode==='busy'),false,mode);assert.equal(f.selfReloads.length,0,mode);
 }
});

test('a task starting during update inspection cancels reload; a navigated tab is not refreshed after restart',async()=>{
 const f=fixture();let busy=false;
 f.options.readManifest=async()=>{busy=true;return {version:'0.4.9'};};
 assert.equal(await f.newUpdater().check(()=>busy),false);assert.equal(f.selfReloads.length,0);
 f.options.readManifest=async()=>({version:'0.4.9'});await f.newUpdater().check(()=>false);
 f.tabs.set(7,{url:'https://example.test/other'});f.setVersion('0.4.9');await f.newUpdater().restore();
 assert.deepEqual(f.pageReloads,[8]);
});

test('draft or unresponsive paired tabs defer the entire update until idle',async()=>{
 for(const state of [{ok:true,hasDraft:true,isGenerating:false},undefined]){
  const f=fixture();f.states.set(8,state);const updater=f.newUpdater();
  assert.equal(await updater.check(()=>false),false);assert.equal(f.selfReloads.length,0);
  f.states.set(8,{ok:true,hasDraft:false,isGenerating:false});f.tick();
  assert.equal(await updater.check(()=>false),true);
 }
});

test('restored IDs resolve by saved URL during both inspection and activation; closed tabs stay closed',async()=>{
 const f=fixture();f.tabs.delete(7);f.tabs.delete(8);
 f.tabs.set(17,{id:17,url:f.pairs[0].url});f.states.set(17,{ok:true,hasDraft:false,isGenerating:false});
 assert.equal(await f.newUpdater().check(()=>false),true);
 assert.deepEqual(f.saved.harnessDevelopmentUpdate.refresh.map(p=>p.tabId),[17]);
 f.tabs.delete(17);f.tabs.set(27,{id:27,url:f.pairs[0].url});f.setVersion('0.4.9');
 await f.newUpdater().restore();assert.deepEqual(f.pageReloads,[27]);
});

test('incognito and unrelated provider conversations are never refreshed',async()=>{
 const f=fixture();f.tabs.clear();f.tabs.set(17,{id:17,url:f.pairs[0].url,incognito:true});
 f.tabs.set(18,{id:18,url:'https://chatgpt.com/c/unrelated'});
 assert.equal(await f.newUpdater().check(()=>false),true);assert.deepEqual(f.saved.harnessDevelopmentUpdate.refresh,[]);
});
