import test from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import {readFileSync} from 'node:fs';
import {DevelopmentUpdater} from '../extension/development-update.js';import {BrowserDownloadWatch} from '../extension/download-watch.js';import {browserRead} from '../extension/tab-manager.js';
const script=readFileSync(new URL('../extension/provider-catalog.js',import.meta.url),'utf8')+'\n'+readFileSync(new URL('../extension/background.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'');
const settle=async()=>{for(let i=0;i<10;i++)await new Promise(resolve=>setImmediate(resolve));};
test('worker resumes a lost submitted ChatGPT listener once, without repeating normal dispatch',async()=>{
 for(const scenario of ['verified','other-url','busy','no-receipt','image-purpose']){
  let tick,receive,delivered=false,lost=false;const messages=[],noop={addListener(){}},job={id:'job',site:'chatgpt-web',sessionId:'session',purpose:scenario==='image-purpose'?'image':'task',prompt:'Exact original prompt',conversationUrl:'https://chatgpt.com/c/test'};
  const chrome={runtime:{getURL:()=> 'config',getManifest:()=>({version:'0.10.3'}),onMessage:{addListener(fn){receive=fn;}}},storage:{local:{async get(key){return typeof key==='string'?{}:{...key,enabled:true,sites:['chatgpt-web']};},async set(){}},onChanged:noop},tabs:{async sendMessage(id,message){if(message.type==='harness-pulse')return lost?{ok:false,busy:scenario==='busy',resumeAvailable:scenario!=='no-receipt',url:scenario==='other-url'?'https://chatgpt.com/c/other':job.conversationUrl}:{ok:true};messages.push({id,...message});if(message.resume)lost=false;return {ok:true,started:true};},onUpdated:noop,onRemoved:noop},alarms:{create(){},onAlarm:noop},action:{async setBadgeText(){}}};
  vm.runInNewContext(script,{chrome,URL,AbortSignal,DevelopmentUpdater,BrowserDownloadWatch,browserRead,setInterval:fn=>{tick=fn;},waitForWebsiteTab:async()=>true,WebsiteTabManager:class{async bindings(){return [];}async acquire(){return {tab:{id:7},binding:{url:job.conversationUrl}};}async complete(){}async failed(){}},fetch:async(path)=>{if(path==='config')return {json:async()=>({token:'synthetic'})};if(path.endsWith('/poll')){const commands=delivered?[]:[job];delivered=true;return {ok:true,json:async()=>({commands,activeIds:['job'],listeners:[],actions:[]})};}return {ok:true,json:async()=>({ok:true})};}});
  await settle();assert.equal(messages.length,1);lost=true;tick();await settle();tick();await settle();
  assert.equal(messages.filter(m=>!m.resume).length,1);
  assert.equal(messages.filter(m=>m.resume).length,scenario==='verified'?1:0);
  if(scenario==='verified'){assert.equal(messages[1].prompt,job.prompt);assert.equal(messages[1].id,job.id);assert.equal(messages[1].streamEvents,true);}
  await new Promise(resolve=>receive({type:'harness-event',event:{id:'job',type:'done',text:'Verified reply'}},{tab:{id:7}},resolve));await settle();
 }
});
