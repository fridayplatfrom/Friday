import test from 'node:test';
import assert from 'node:assert/strict';
import { WebsiteTabManager, waitForWebsiteTab } from '../extension/tab-manager.js';

function fixture(options = {}) {
  const store = {}; const tabs = new Map(); let created = 0; const navigations = []; let probe = { ok: true }; let now = 0;
  const chrome = { storage: { local: {
    async get(key) { return structuredClone({ [key]: store[key] }); },
    async set(values) { Object.assign(store, structuredClone(values)); }, async remove(key) { delete store[key]; },
  } }, tabs: {
    async query(){return [...tabs.values()];},
    async create(props) { const tab = { id: ++created, ...props }; tabs.set(tab.id, tab); return tab; },
    async get(id) { if (!tabs.has(id)) throw new Error('closed'); return tabs.get(id); },
    async update(id, props) { if (props.url) navigations.push(props.url); Object.assign(tabs.get(id), props); return tabs.get(id); },
    async sendMessage() { now += options.probeTime || 0; return probe; },
  } };
  return { chrome, manager: new WebsiteTabManager(chrome, { ...options, now: () => now }), tabs, store, navigations,
    created: () => created, setProbe(value) { probe = value; } };
}
const command = { site: 'chatgpt-web', sessionId: 'session-a' };
test('ChatGPT local draft routes never become pinned history and promote to the final chat in the same tab',async()=>{
 const f=fixture(),initial=await f.manager.acquire(command);
 f.tabs.get(initial.tab.id).url='https://chatgpt.com/c/local-chatgpt%3Adraft-id';await f.manager.complete(initial.tab.id);
 assert.equal((await f.manager.bindings())[0].url,'https://chatgpt.com/');
 f.tabs.get(initial.tab.id).url='https://chatgpt.com/c/real-saved-chat';await f.manager.complete(initial.tab.id);
 assert.equal((await f.manager.bindings())[0].url,'https://chatgpt.com/c/real-saved-chat');assert.equal((await f.manager.acquire(command)).tab.id,initial.tab.id);assert.equal(f.created(),1);
});
test('a closed provisional ChatGPT draft opens the homepage rather than a non-restorable local URL',async()=>{
 const f=fixture(),initial=await f.manager.acquire(command);
 const pairs=Object.values(f.store.harnessWebsitePairs);pairs[0].url='https://chatgpt.com/c/local-chatgpt%3Aold-draft';f.tabs.delete(initial.tab.id);
 const reopened=await f.manager.acquire(command);assert.equal(reopened.tab.url,'https://chatgpt.com/');
});

test('Kimi provisional URLs promote to the saved chat without spawning duplicate tabs',async()=>{
 const f=fixture(),task={site:'kimi-web',sessionId:'kimi-save'},initial=await f.manager.acquire(task);
 const temporary='https://www.kimi.ai/chat/p06dd1b8-09b4-47ff-bc90-253bcd78b31a';
 const saved='https://www.kimi.ai/chat/1a1c5e92-b482-8f7a-8000-099eba60381a';
 f.tabs.get(initial.tab.id).url=temporary;await f.manager.complete(initial.tab.id);
 f.tabs.get(initial.tab.id).url=saved;await f.manager.complete(initial.tab.id);
 assert.equal((await f.manager.bindings())[0].url,saved);
 assert.equal((await f.manager.acquire(task)).tab.id,initial.tab.id);assert.equal(f.created(),1);
 await f.manager.updateURL(initial.tab.id,'https://www.kimi.ai/chat/unrelated');
 assert.equal((await f.manager.bindings())[0].url,saved);
});

test('prototype provider names cannot create or adopt a browser tab',async()=>{
 const f=fixture();for(const site of ['__proto__','constructor','toString'])await assert.rejects(f.manager.acquire({...command,site}),/Unknown website/);
 assert.equal(f.created(),0);
});

test('consecutive requests and worker restart reuse exactly one managed tab', async () => {
  const f = fixture(); const first = await f.manager.acquire(command); await f.manager.complete(first.tab.id, 100);
  const second = await f.manager.acquire(command); assert.equal(second.tab.id, first.tab.id);
  const restarted = new WebsiteTabManager(f.chrome); assert.equal((await restarted.acquire(command)).tab.id, first.tab.id);
  assert.equal(f.created(), 1); assert.equal(f.navigations.length, 0);
});
test('a failed or timed-out saved-tab lookup never creates a duplicate tab and releases the local queue',async()=>{
 for(const mode of ['rejected','timeout']){
  const f=fixture({readTimeoutMs:15}),first=await f.manager.acquire(command),get=f.chrome.tabs.get;
  f.chrome.tabs.get=()=>mode==='timeout'?new Promise(()=>{}):Promise.reject(new Error('Chrome API unavailable'));
  await assert.rejects(f.manager.acquire(command),mode==='timeout'?/lookup timed out/:/API unavailable/);assert.equal(f.created(),1);
  f.chrome.tabs.get=get;assert.equal((await f.manager.acquire(command)).tab.id,first.tab.id);assert.equal(f.created(),1);
 }
});
test('a failed saved-chat search does not open a replacement with an uncertain existing tab',async()=>{
 const f=fixture({readTimeoutMs:15});f.chrome.tabs.query=()=>new Promise(()=>{});
 await assert.rejects(f.manager.acquire({...command,conversationUrl:'https://chatgpt.com/c/saved'}),/lookup timed out/);assert.equal(f.created(),0);
});

test('exact saved URLs recover despite stalled stale-ID lookups without opening another tab',async()=>{
 for(const [site,url]of [['deepseek-web','https://chat.deepseek.com/a/chat/s/saved'],['gemini-web','https://gemini.google.com/app/saved'],['kimi-web','https://www.kimi.ai/chat/saved']]){
  const f=fixture({readTimeoutMs:5}),task={site,sessionId:'restored'};
  f.store.harnessWebsitePairs={[JSON.stringify(['restored',site])]:{...task,tabId:12,url}};f.tabs.set(42,{id:42,url});
  f.chrome.tabs.get=()=>new Promise(()=>{});
  assert.equal((await f.manager.acquire(task)).tab.id,42);assert.equal(f.created(),0);
  assert.equal((await f.manager.lookup({...task,tabId:12,url})).id,42);assert.equal(f.created(),0);
 }
});

test('failed URL discovery can fall back to a confirmed saved ID but cannot infer absence',async()=>{
 const f=fixture({readTimeoutMs:5}),task={...command,conversationUrl:'https://chatgpt.com/c/saved'};
 const initial=await f.manager.acquire(task);f.chrome.tabs.query=()=>new Promise(()=>{});
 assert.equal((await f.manager.acquire(task)).tab.id,initial.tab.id);assert.equal(f.created(),1);
 f.tabs.delete(initial.tab.id);await assert.rejects(f.manager.acquire(task),/lookup timed out/);assert.equal(f.created(),1);
});

test('a responding exact-document listener proves readiness even if Chrome metadata stalls',async()=>{
 const chrome={tabs:{get:()=>new Promise(()=>{}),sendMessage:async()=>({ok:true,url:'https://gemini.google.com/app/saved',readyState:'complete',hasEditor:true})}};
 assert.equal(await waitForWebsiteTab(chrome,42,{navigationUrl:'https://gemini.google.com/app/saved',probeTimeoutMs:5,attempts:1,sleep:async()=>{}}),true);
 assert.equal(await waitForWebsiteTab(chrome,42,{navigationUrl:'https://gemini.google.com/app/other',probeTimeoutMs:5,attempts:1,sleep:async()=>{}}),false);
});

test('an unresponsive paired page gets one bounded wake-up and no prompt or reload',async()=>{
 let awake=false,wakes=0;
 const chrome={tabs:{async sendMessage(){if(!awake)throw Error('Page suspended');return {ok:true,readyState:'complete',url:'https://www.kimi.ai/chat/saved'};}}};
 assert.equal(await waitForWebsiteTab(chrome,7,{navigationUrl:'https://www.kimi.ai/chat/saved',sleep:async()=>{},onUnresponsive:async()=>{wakes++;awake=true;}}),true);
 assert.equal(wakes,1);
 let active=true;
 assert.equal(await waitForWebsiteTab({tabs:{async sendMessage(){throw Error('Unavailable');}}},7,{isActive:()=>active,sleep:async()=>{},onUnresponsive:async()=>{active=false;},attempts:5}),false);
});
test('long conversations, slow probes and failures never recycle a paired chat', async () => {
  const f = fixture({ maxRequests: 1, maxCharacters: 5, probeTime: 10000 });
  const first = await f.manager.acquire(command);
  await f.manager.complete(first.tab.id, 999999); await f.manager.failed(first.tab.id);
  f.setProbe({ hasDraft: true, responseCharacters: 999999 });
  for (let i=0;i<10;i++) assert.equal((await f.manager.acquire(command)).tab.id, first.tab.id);
  assert.equal(f.created(),1); assert.equal(f.navigations.length,0);
});

test('each session and provider has its own persistent tab; returning reuses the original', async () => {
  const f=fixture(); const a=await f.manager.acquire(command);
  const b=await f.manager.acquire({...command,sessionId:'session-b'});
  const gemini=await f.manager.acquire({site:'gemini-web',sessionId:'session-b'});
  assert.notEqual(a.tab.id,b.tab.id); assert.notEqual(gemini.tab.id,b.tab.id);
  assert.equal((await new WebsiteTabManager(f.chrome).acquire(command)).tab.id,a.tab.id);
  assert.equal(f.created(),3); assert.equal(f.navigations.length,0);
});

test('closed paired tab reopens its saved conversation URL', async () => {
  const f=fixture();const first=await f.manager.acquire(command);
  f.tabs.get(first.tab.id).url='https://chatgpt.com/c/abc?secret=ignored';
  await f.manager.updateURL(first.tab.id,f.tabs.get(first.tab.id).url);
  await f.manager.forget(first.tab.id);f.tabs.delete(first.tab.id);
  const next=await f.manager.acquire(command);
  assert.equal(next.navigationUrl,'https://chatgpt.com/c/abc');assert.equal(f.created(),2);
});

test('navigating the owned tab away gives a useful error without spawning or overwriting tabs', async () => {
  const f=fixture();const first=await f.manager.acquire(command);
  f.tabs.get(first.tab.id).url='https://example.com/';
  await assert.rejects(f.manager.acquire(command),/Return it to/);
  assert.equal(f.created(),1);assert.equal(f.navigations.length,0);
});

test('concurrent acquisition of one session cannot open duplicate tabs', async () => {
  const f=fixture();const results=await Promise.all([f.manager.acquire(command),f.manager.acquire(command)]);
  assert.equal(results[0].tab.id,results[1].tab.id);assert.equal(f.created(),1);
});

test('rollover waits for the new document, ignoring an old script during navigation', async () => {
  let tick = 0; let probes = 0;
  const chrome = { tabs: {
    async get() { return { status: tick === 0 ? 'loading' : 'complete' }; },
    async sendMessage() { probes++; return { ok: true, readyState: 'complete',
      url: tick < 3 ? 'https://chatgpt.com/c/old' : 'https://chatgpt.com/' }; },
  } };
  assert.equal(await waitForWebsiteTab(chrome, 1, { navigationUrl: 'https://chatgpt.com/', sleep: async () => { tick++; } }), true);
  assert.equal(tick, 3); assert.equal(probes, 4);
});
test('unready, missing, or cancelled document never receives a run request', async () => {
  const chrome = { tabs: { async get() { return { status: 'complete' }; },
    async sendMessage() { return { ok: true, readyState: 'loading', url: 'https://chatgpt.com/' }; } } };
  assert.equal(await waitForWebsiteTab(chrome, 1, { attempts: 3, sleep: async () => {} }), false);
  assert.equal(await waitForWebsiteTab(chrome, 1, { isActive: () => false }), false);
});

test('a usable interactive editor is ready even while a website asset keeps Chrome loading',async()=>{
  const chrome={tabs:{async get(){return {status:'loading'};},async sendMessage(){return {ok:true,readyState:'interactive',hasEditor:true,url:'https://chatgpt.com/c/one'};}}};
  assert.equal(await waitForWebsiteTab(chrome,7,{navigationUrl:'https://chatgpt.com/c/one'}),true);
  assert.equal(await waitForWebsiteTab(chrome,7,{navigationUrl:'https://chatgpt.com/c/other',attempts:1,sleep:async()=>{}}),false);
});

test('a hung Chrome readiness probe is bounded and cannot block cancellation indefinitely',async()=>{
  for(const hangGet of [true,false]){
    const chrome={tabs:{get:()=>hangGet?new Promise(()=>{}):Promise.resolve({status:'complete'}),sendMessage:()=>new Promise(()=>{})}};
    assert.equal(await waitForWebsiteTab(chrome,7,{attempts:1,probeTimeoutMs:5,sleep:async()=>{}}),false);
  }
  let active=true;
  const chrome={tabs:{get:async()=>({status:'complete'}),sendMessage:async()=>{active=false;return {ok:true,readyState:'complete'};}}};
  assert.equal(await waitForWebsiteTab(chrome,7,{isActive:()=>active,sleep:async()=>{}}),false);
});

test('explicit active-tab pairing repairs only the chosen session and protects unrelated owned tabs',async()=>{
 const f=fixture(),backup={sessionId:'backup',site:'deepseek-web'},tab={id:99,url:'https://chat.deepseek.com/a/chat/s/synthetic?private=discard'};f.tabs.set(99,tab);
 f.store.harnessWebsitePairs={stale:{...backup,tabId:12,url:'https://chat.deepseek.com/'},duplicate:{...backup,tabId:13,url:'https://chat.deepseek.com/'}};
 await f.manager.pairExisting(backup,tab);assert.equal((await f.manager.bindings()).length,1);assert.equal((await f.manager.acquire(backup)).tab.id,99);assert.equal(f.created(),0);assert.equal((await f.manager.bindings())[0].url,'https://chat.deepseek.com/a/chat/s/synthetic');
 await assert.rejects(f.manager.pairExisting({...backup,sessionId:'other'},tab),/another Friday/);
 await assert.rejects(f.manager.pairExisting(backup,{id:100,url:'https://unrelated.test/'}),/intended provider/);
 assert.equal((await f.manager.bindings())[0].tabId,99);
});

test('restored saved chat URLs recover changed tab IDs without creating another provider tab',async()=>{
 for(const [site,url] of [['chatgpt-web','https://chatgpt.com/c/saved'],['deepseek-web','https://chat.deepseek.com/a/chat/s/saved'],['gemini-web','https://gemini.google.com/app/saved'],['kimi-web','https://www.kimi.ai/chat/saved'],['kimi-web','https://www.kimi.com/chat/saved']]){
  const f=fixture(),task={sessionId:'restored',site};f.store.harnessWebsitePairs={[JSON.stringify(['restored',site])]:{...task,tabId:12,url}};f.tabs.set(42,{id:42,url,active:true});
  const pair=await f.manager.acquire(task);assert.equal(pair.tab.id,42);assert.equal(pair.navigationUrl,url);assert.equal(f.created(),0);
  assert.equal((await f.manager.acquire(task)).tab.id,42);assert.equal(f.created(),0);
 }
});
test('server-saved conversation URL survives cleared extension pairing storage; new tasks get fresh chats',async()=>{
 const f=fixture(),url='https://chatgpt.com/c/from-harness';f.tabs.set(77,{id:77,url});
 const restored=await f.manager.acquire({...command,conversationUrl:url});assert.equal(restored.tab.id,77);assert.equal(f.created(),0);
 const next=await f.manager.acquire({...command,sessionId:'new-session'});assert.notEqual(next.tab.id,77);assert.equal(next.navigationUrl,'https://chatgpt.com/');assert.equal(f.created(),1);
});
test('a same-site different chat is preserved while Friday recovers its pinned conversation',async()=>{
 const f=fixture();const first=await f.manager.acquire(command);f.tabs.get(first.tab.id).url='https://chatgpt.com/c/pinned';await f.manager.complete(first.tab.id);
 f.tabs.get(first.tab.id).url='https://chatgpt.com/c/unrelated';await f.manager.updateURL(first.tab.id,f.tabs.get(first.tab.id).url);const recovered=await f.manager.acquire(command);
 assert.equal(recovered.navigationUrl,'https://chatgpt.com/c/pinned');assert.equal(f.tabs.get(first.tab.id).url,'https://chatgpt.com/c/unrelated');
});
test('a closed last Chrome window can reopen the saved chat without debugging flags',async()=>{
 const f=fixture();f.chrome.tabs.create=async()=>{throw new Error('No current window');};let opened;
 f.chrome.windows={create:async options=>{opened=options;return {tabs:[{id:500,url:options.url}]};}};
 const result=await f.manager.acquire({...command,conversationUrl:'https://chatgpt.com/c/reopen'});assert.equal(result.tab.id,500);assert.equal(opened.url,'https://chatgpt.com/c/reopen');assert.equal(opened.type,'normal');
});
