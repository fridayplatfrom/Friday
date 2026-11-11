import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { DevelopmentUpdater } from '../extension/development-update.js';
import { BrowserDownloadWatch } from '../extension/download-watch.js';
import {browserRead} from '../extension/tab-manager.js';

const recovery = readFileSync(new URL('../recovery-client.js', import.meta.url), 'utf8');
const background = readFileSync(new URL('../extension/provider-catalog.js', import.meta.url), 'utf8')+'\n'+readFileSync(new URL('../extension/background.js', import.meta.url), 'utf8').replace(/^import .*\r?\n/gm, '');
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };

test('the Chrome worker keeps two owned tabs active, rejects cross-tab events and replaces only the finished slot',async()=>{
 let receive,tick,round=0;const completed=[],events=[],polls=[],pulses=[],noop={addListener(){}},ids=new Map([['a',11],['b',22],['c',33]]);
 const jobs=['a','b','c'].map(id=>({id,sessionId:id,site:'chatgpt-web',prompt:id}));
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.10.0'}),onMessage:{addListener(fn){receive=fn;}}},storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['chatgpt-web']};},async set(){}},onChanged:noop},tabs:{async sendMessage(tabId,message){if(message.type==='harness-pulse')pulses.push([tabId,message.id]);return {ok:true,started:true};},onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},waitForWebsiteTab:async()=>true,WebsiteTabManager:class{async bindings(){return [];}async acquire(command){return {tab:{id:ids.get(command.id)},binding:{}};}async complete(id){completed.push(id);}async failed(){}},fetch:async(path,options)=>{
  if(path==='config')return {json:async()=>({token:'synthetic'})};
  if(path.endsWith('/poll')){polls.push(JSON.parse(options.body));const commands=round++===0?jobs.slice(0,2):round===3?[jobs[2]]:[];return {ok:true,json:async()=>({commands,activeIds:['a','b','c'],listeners:[],actions:[],queuedRequests:1})};}
  if(path.endsWith('/event'))events.push(JSON.parse(options.body));return {ok:true,json:async()=>({ok:true})};
 }});
 await settle();tick();await settle();assert.deepEqual([...polls.at(-1).runningIds].sort(),['a','b']);assert.deepEqual(pulses,[[11,'a'],[22,'b']]);
 const send=(id,tabId)=>new Promise(resolve=>receive({type:'harness-event',event:{id,type:'done',text:`reply-${id}`}},{tab:{id:tabId}},resolve));
 assert.equal((await send('a',22)).ok,false);assert.equal(events.some(e=>e.type==='done'),false);
 assert.equal((await send('a',11)).ok,true);await settle();tick();await settle();tick();await settle();
 assert.deepEqual([...polls.at(-1).runningIds].sort(),['b','c']);assert.deepEqual(completed,[11]);
 await send('c',33);await send('b',22);await settle();assert.deepEqual(completed.sort(),[11,22,33]);
 assert.equal(events.filter(e=>e.type==='done').length,3);
});

test('short start ACK reserves the website job until its real terminal event is acknowledged',async()=>{
 let receive,tick,delivered=false,completed=0;const polls=[],events=[],noop={addListener(){}},job={id:'stream-job',site:'kimi-web',sessionId:'saved',prompt:'synthetic'};
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.9.7'}),onMessage:{addListener(fn){receive=fn;}}},storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['kimi-web']};},async set(){}},onChanged:noop},tabs:{async sendMessage(_id,message){assert.equal(message.streamEvents,true);return {ok:true,started:true};},onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},waitForWebsiteTab:async()=>true,WebsiteTabManager:class{async bindings(){return [];}async acquire(){return {tab:{id:7},binding:{}};}async complete(){completed++;}async failed(){}},fetch:async(path,options)=>{
  if(path==='config')return {json:async()=>({token:'synthetic'})};
  if(path.endsWith('/poll')){polls.push(JSON.parse(options.body));const commands=delivered?[]:[job];delivered=true;return {ok:true,json:async()=>({commands,activeIds:[job.id],listeners:[],actions:[]})};}
  if(path.endsWith('/event'))events.push(JSON.parse(options.body));return {ok:true,json:async()=>({ok:true})};
 }});
 await settle();tick();await settle();assert.deepEqual([...polls.at(-1).runningIds],[job.id]);assert.equal(completed,0);
 const answer=await new Promise(resolve=>receive({type:'harness-event',event:{id:job.id,type:'done',text:'Complete reply'}},{tab:{id:7}},resolve));
 assert.equal(answer.ok,true);await settle();tick();await settle();
 assert.equal(completed,1);assert.deepEqual([...polls.at(-1).runningIds],[]);assert.equal(events.filter(event=>event.type==='done').length,1);
});
test('a lost start ACK cannot hold the worker after an acknowledged terminal event',async()=>{
 for(const rejectedStart of [false,true]){
 let receive,tick,delivered=false,completed=0;const polls=[],events=[],noop={addListener(){}},job={id:'stream-job',site:'kimi-web',sessionId:'saved',prompt:'synthetic'};
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.9.7'}),onMessage:{addListener(fn){receive=fn;}}},storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['kimi-web']};},async set(){}},onChanged:noop},tabs:{async sendMessage(_id,message){if(message.type==='harness-pulse')return {ok:true};assert.equal(message.streamEvents,true);return rejectedStart?Promise.reject(new Error('Start message port closed')):new Promise(()=>{});},onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},waitForWebsiteTab:async()=>true,WebsiteTabManager:class{async bindings(){return [];}async acquire(){return {tab:{id:7},binding:{}};}async complete(){completed++;}async failed(){}},fetch:async(path,options)=>{
  if(path==='config')return {json:async()=>({token:'synthetic'})};
  if(path.endsWith('/poll')){polls.push(JSON.parse(options.body));const commands=delivered?[]:[job];delivered=true;return {ok:true,json:async()=>({commands,activeIds:[job.id],listeners:[],actions:[]})};}
  if(path.endsWith('/event'))events.push(JSON.parse(options.body));return {ok:true,json:async()=>({ok:true})};
 }});
 await settle();tick();await settle();assert.deepEqual([...polls.at(-1).runningIds],[job.id]);assert.equal(completed,0);
 const answer=await new Promise(resolve=>receive({type:'harness-event',event:{id:job.id,type:'done',text:'Complete reply'}},{tab:{id:7}},resolve));
 assert.equal(answer.ok,true);await settle();tick();await settle();
 assert.equal(completed,1);assert.deepEqual([...polls.at(-1).runningIds],[]);assert.equal(events.filter(event=>event.type==='done').length,1);
 }
});
test('a hung Chrome metadata lookup produces a fresh unavailable health result instead of silence or a false closed-tab report',async()=>{
 const reports=[],noop={addListener(){}},pair={sessionId:'active',site:'chatgpt-web',tabId:7,url:'https://chatgpt.com/c/active'};let delivered=false;
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.9.6'}),onMessage:noop},storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['chatgpt-web']};},async set(){}},onChanged:noop},tabs:{get:()=>new Promise(()=>{}),sendMessage:async()=>{throw Error('Metadata lookup must finish first');},onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead:action=>browserRead(action,5),setInterval(){},WebsiteTabManager:class{async bindings(){return [pair];}},fetch:async(path,options)=>{
  if(path==='config')return {json:async()=>({token:'synthetic'})};
  if(path.endsWith('/provider-health')){reports.push(JSON.parse(options.body));return {ok:true,json:async()=>({ok:true})};}
  const actions=delivered?[]:[{type:'probe-site',site:'chatgpt-web',sessionId:'active'}];delivered=true;
  return {ok:true,json:async()=>({commands:[],activeIds:[],listeners:[],actions})};
 }});
 await new Promise(resolve=>setTimeout(resolve,40));await settle();
 assert.equal(reports.length,1);assert.equal(reports[0].probeStatus,'probe-timeout');assert.equal(reports[0].notOpen,false);assert.equal(reports[0].scopeSession,'active');
});

test('automatic update uses authenticated loopback version even when Chrome caches its old manifest',async()=>{
 const saved={},requests=[],noop={addListener(){}};let reloads=0;
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.9.1'}),reload(){reloads++;},onMessage:noop},storage:{local:{async get(key){return typeof key==='string'?{[key]:saved[key]}:{...key,...saved};},async set(values){Object.assign(saved,values);}},onChanged:noop},tabs:{onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval(){},WebsiteTabManager:class{async bindings(){return [];}},fetch:async(path,options)=>{if(path==='config')return {json:async()=>({token:'synthetic',developmentAutoReload:true})};requests.push({path,auth:options.headers.Authorization});if(path.endsWith('/status'))return {ok:true,json:async()=>({availableExtensionVersion:'0.9.2'})};return {ok:true,json:async()=>({commands:[],activeIds:[],listeners:[],actions:[]})};}});
 await settle();assert.equal(reloads,1);assert.equal(saved.harnessDevelopmentUpdate.version,'0.9.2');assert.equal(requests.find(r=>r.path.endsWith('/status')).auth,'Bearer synthetic');
});

test('fresh connector enables catalog providers by default and preserves explicit disabled choices',async()=>{
 for(const saved of [{},{enabled:false,sites:['gemini-web']},{enabled:true,sites:['kimi-web']}]){
  const polls=[],noop={addListener(){}};
  const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.9.1'}),onMessage:noop},storage:{local:{async get(key){return typeof key==='string'?{[key]:saved[key]}:{...key,...saved};},async set(){}},onChanged:noop},tabs:{onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
  vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval(){},WebsiteTabManager:class{async bindings(){return [];}},fetch:async(path,options)=>{if(path==='config')return {json:async()=>({token:'synthetic'})};polls.push(JSON.parse(options.body));return {ok:true,json:async()=>({commands:[],activeIds:[],listeners:[],actions:[]})};}});
  await settle();assert.deepEqual([...polls[0].sites],saved.enabled===false?[]:saved.sites||['chatgpt-web','deepseek-web','gemini-web','kimi-web']);
 }
});

test('native recovery guard shows offline, detects restart, and restores a blank UI without clearing storage', async () => {
  let tick; let online = true; let instance = 'first'; let editor = {}; let reloads = 0; const banners = [];
  const node = () => ({ style: {}, setAttribute() {}, replaceChildren(...children) { this.children = children; }, append() {}, remove() {} });
  vm.runInNewContext(recovery, { document: { body: { append: item => banners.push(item) }, createElement: node,
    createTextNode: text => text, querySelector: () => editor }, location: { reload: () => reloads++ },
    AbortSignal, setInterval: callback => { tick = callback; }, fetch: async () => {
      if (!online) throw new Error('Offline'); return { ok: true, json: async () => ({ instanceId: instance }) };
    } });
  await settle(); online = false; tick(); await settle(); assert.match(banners.at(-1).children[0], /offline/);
  online = true; instance = 'second'; tick(); await settle(); assert.equal(reloads, 0, 'an open editor is preserved');
  editor = null; tick(); await settle(); assert.equal(reloads, 1, 'a view that becomes blank after restart reloads');
});

test('extension publishes offline status, sends one notice per transition, and restores status after reconnect', async () => {
  let tick; let online = true; const sent = []; const saved = {};
  const pair = { sessionId: 'one', site: 'chatgpt-web', tabId: 7, url: 'https://chatgpt.com/c/one', enabled: true, status: 'Ready' };
  const noop = { addListener() {} }; let receive;
  const chrome = { runtime: { getURL: () => 'config', getManifest: () => ({ version: '0.3.4' }), onMessage: {addListener(handler) {receive=handler;}} },
    storage: { local: { async get(key) { return typeof key === 'string' ? { [key]: saved[key] } : { ...key, enabled: true, sites: ['chatgpt-web'] }; },
      async set(data) { Object.assign(saved, data); } }, onChanged: noop },
    tabs: { async get() { return { url: pair.url }; }, async sendMessage(id, message) { sent.push(message); return { sent: true }; }, onUpdated: noop, onRemoved: noop },
    action: { async setBadgeText() {} }, alarms: { create() {}, onAlarm: noop } };
  vm.runInNewContext(background, { chrome, URL, AbortSignal, DevelopmentUpdater,BrowserDownloadWatch,browserRead, setInterval: callback => { tick = callback; },
    WebsiteTabManager: class { async bindings() { return [pair]; } },
    fetch: async path => { if (path === 'config') return { json: async () => ({ token: 'fake-local-token' }) };
      if (!online) throw new Error('Offline'); return { ok: true, json: async () => ({ listeners: [pair], commands: [], actions: [], activeIds: [] }) }; } });
  await settle(); online = false; tick(); await settle(); tick(); await settle();
  const pull = tab => new Promise(resolve => receive({type:'harness-listener-refresh'}, {tab}, resolve));
  assert.equal((await pull({id:7,url:pair.url})).config.online,false);
  assert.equal((await pull({id:99,url:pair.url})).ok,false);
  assert.ok(sent.some(message => message.type === 'harness-listen' && message.config.online === false));
  assert.equal(sent.filter(message => message.type === 'harness-connection-notice' && !message.online).length, 1);
  online = true; tick(); await settle();
  assert.equal(sent.filter(message => message.type === 'harness-connection-notice' && message.online).length, 1);
  assert.equal(sent.filter(message => message.type === 'harness-listen').at(-1).config.status, 'Ready');
  assert.equal((await pull({id:7,url:pair.url})).config.online,true);
});

test('frozen status listeners cannot delay dispatch; slow acquisition is reserved and cancellation prevents late submission',async()=>{
  let tick,releaseAcquire;let acquisitions=0,pollCount=0;const polls=[],sent=[];
  const job={id:'test-job',site:'chatgpt-web',sessionId:'one',prompt:'test'};
  const pair={sessionId:'other',tabId:8,url:'https://chatgpt.com/c/other',site:'chatgpt-web',enabled:true};
  const noop={addListener(){}};
  const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.4.2'}),onMessage:noop},
    storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['chatgpt-web']};},async set(){}},onChanged:noop},
    tabs:{get:async()=>({url:pair.url}),async sendMessage(id,message){sent.push(message);if(message.type==='harness-listen')return new Promise(()=>{});return {ok:true};},onUpdated:noop,onRemoved:noop},
    alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
  vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},
    WebsiteTabManager:class{async bindings(){return [pair];}acquire(){acquisitions++;return new Promise(resolve=>{releaseAcquire=()=>resolve({tab:{id:9},binding:{}});});}},
    waitForWebsiteTab:async()=>{throw new Error('Cancelled acquisition must not dispatch');},
    fetch:async(path,options)=>{if(path==='config')return {json:async()=>({token:'test'})};
      if(path.endsWith('/poll')){polls.push(JSON.parse(options.body));pollCount++;return {ok:true,json:async()=>({commands:pollCount<3?[job]:[],activeIds:pollCount<3?[job.id]:[],listeners:[pair],actions:[]})};}
      return {ok:true,json:async()=>({ok:true})};}
  });
  await settle();assert.equal(acquisitions,1,'dispatch does not wait for a frozen listener');
  tick();await settle();assert.deepEqual([...polls[1].runningIds],[job.id]);assert.equal(acquisitions,1,'same job is not reacquired');
  tick();await settle();releaseAcquire();await settle();
  assert.equal(sent.some(message=>message.type==='harness-run'),false,'cancellation prevents a late submission');
});

test('native Models can disable and reenable existing provider polling without new tabs or unknown sites',async()=>{
 let tick;let actions=[{type:'configure-site',site:'chatgpt-web',enabled:false}];
 const saved={enabled:true,sites:['chatgpt-web']},polls=[];const noop={addListener(){}};
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.4.25'}),onMessage:noop},
 storage:{local:{async get(key){return typeof key==='string'?{[key]:saved[key]}:{...key,...saved};},async set(values){Object.assign(saved,values);}},onChanged:noop},
 tabs:{onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},
 WebsiteTabManager:class{async bindings(){return [];}},fetch:async(path,options)=>{
  if(path==='config')return {json:async()=>({token:'synthetic'})};
  polls.push(JSON.parse(options.body));const delivered=actions;actions=[];
  return {ok:true,json:async()=>({commands:[],activeIds:[],listeners:[],actions:delivered})};
 }});
 await settle();assert.equal(saved.enabled,false);assert.equal(saved.sites.length,0);
 actions=[{type:'configure-site',site:'chatgpt-web',enabled:true},{type:'configure-site',site:'arbitrary-site',enabled:true}];
 tick();await settle();assert.deepEqual([...polls.at(-1).sites],[],'disabled extension still checks authenticated configuration');
 assert.equal(saved.enabled,true);assert.deepEqual([...saved.sites],['chatgpt-web']);
 tick();await settle();assert.deepEqual([...polls.at(-1).sites],['chatgpt-web']);
});

test('explicit paired-tab recovery preserves drafts, generating pages and unrelated navigation',async()=>{
 let tick,actions=[{type:'refresh-site',site:'chatgpt-web'}],reloads=0;
 const pair={sessionId:'test',site:'chatgpt-web',tabId:7,url:'https://chatgpt.com/c/synthetic'};let url=pair.url,page={hasDraft:true,isGenerating:false};const noop={addListener(){}};
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.8.2'}),onMessage:noop},storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['chatgpt-web']};},async set(){}},onChanged:noop},tabs:{async get(){return {url};},async sendMessage(){return page;},async reload(){reloads++;},onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},WebsiteTabManager:class{async bindings(){return [pair];}},fetch:async path=>{if(path==='config')return {json:async()=>({token:'synthetic'})};const delivered=actions;actions=[];return {ok:true,json:async()=>({commands:[],activeIds:[],listeners:[],actions:delivered})};}});
 await settle();assert.equal(reloads,0);
 page={hasDraft:false,isGenerating:true};actions=[{type:'refresh-site',site:'chatgpt-web'}];tick();await settle();assert.equal(reloads,0);
 page={hasDraft:false,isGenerating:false};actions=[{type:'refresh-site',site:'chatgpt-web'}];tick();await settle();assert.equal(reloads,1);
 url='https://chatgpt.com/c/unrelated';actions=[{type:'refresh-site',site:'chatgpt-web'}];tick();await settle();assert.equal(reloads,1);
});

test('health probes target the requested session and global checks skip closed tabs from other conversations',async()=>{
 let tick,actions=[{type:'probe-site',site:'chatgpt-web',sessionId:'active'}];const probes=[],reports=[];const pair={sessionId:'active',site:'chatgpt-web',tabId:7,url:'https://chatgpt.com/c/active'},other={sessionId:'closed',site:'chatgpt-web',tabId:8,url:'https://chatgpt.com/c/closed'},noop={addListener(){}};
 const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.8.4'}),onMessage:noop},storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['chatgpt-web']};},async set(){}},onChanged:noop},tabs:{async get(id){if(id===8)throw new Error('No tab');return {url:pair.url};},async sendMessage(id){probes.push(id);return {provider:'chatgpt-web',hasEditor:true,isGenerating:false};},onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
 vm.runInNewContext(background,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},WebsiteTabManager:class{async bindings(){return [pair,other];}},fetch:async(path,options)=>{if(path==='config')return {json:async()=>({token:'synthetic'})};if(path.endsWith('/provider-health')){reports.push(JSON.parse(options.body));return {ok:true,json:async()=>({ok:true})};}const delivered=actions;actions=[];return {ok:true,json:async()=>({commands:[],activeIds:[],listeners:[],actions:delivered})};}});
 await settle();assert.equal(probes[0],7);assert.equal(reports[0].scopeSession,'active');assert.equal(reports[0].page.provider,'chatgpt-web');
 actions=[{type:'probe-site',site:'chatgpt-web'}];tick();await settle();assert.equal(probes.at(-1),7);assert.equal(reports.at(-1).notOpen,false);
});
