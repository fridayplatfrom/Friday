import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';
import {join} from 'node:path';
import {SITES} from './protocol.mjs';
import {websiteURL} from './session-store.mjs';
import {BACKEND_VERSION} from './diagnostics.mjs';
import {createOwnedPage} from './protected-browser.mjs';

/** Uses the native MCP owner's ONE context; never launches a browser. */
export class SharedBrowserWorker {
 constructor(context,{directory,connection,protectedPages,fetchImpl=fetch}){
  Object.assign(this,{context,directory,connection,protectedPages,fetchImpl});this.running=new Map();this.pages=new Map();this.bindings=new Map();this.nextTabId=1000000;this.enabledSites=['chatgpt-web'];this.listeners=[];this.online=false;this.polling=false;this.stopped=false;
 }
 async request(path,input){
  const response=await this.fetchImpl(`http://127.0.0.1:${this.connection.port||8766}${path}`,{method:input===undefined?'GET':'POST',headers:{Authorization:`Bearer ${this.connection.token}`,'Content-Type':'application/json'},...(input===undefined?{}:{body:JSON.stringify(input)}),signal:AbortSignal.timeout(10000)});
  const result=await response.json();if(!response.ok)throw new Error(result.error||'Friday bridge unavailable');return result;
 }
 save(){const snapshot=JSON.stringify({enabledSites:this.enabledSites,bindings:[...this.bindings.values()]});return this.saving=(this.saving||Promise.resolve()).then(async()=>{await mkdir(this.directory,{recursive:true});const file=join(this.directory,'shared-browser.json');await writeFile(file+'.tmp',snapshot);await rename(file+'.tmp',file);});}
 async start(){
  try{const saved=JSON.parse(await readFile(join(this.directory,'shared-browser.json'),'utf8'));this.enabledSites=(saved.enabledSites||[]).filter(site=>Object.hasOwn(SITES,site));for(const pair of saved.bindings||[])if(websiteURL(pair.site,pair.url)&&Number.isInteger(pair.tabId)){this.bindings.set(pair.sessionId+':'+pair.site,pair);this.nextTabId=Math.max(this.nextTabId,pair.tabId+1);}}
  catch(error){if(error.code!=='ENOENT')throw new Error('Shared browser preferences are damaged; preserved for recovery.');}
  this.source=(await Promise.all(['shared-page-agent.js','extension/transfers.js','extension/two-way.js','extension/content.js'].map(path=>readFile(new URL(path,import.meta.url),'utf8')))).join('\n');
  // Protect restored provider pages before exposing any page to native MCP.
  for(const page of this.context.pages())if(Object.values(SITES).some(site=>websiteURL(Object.keys(SITES).find(key=>SITES[key]===site),page.url())))await this.prepare(page);
  await this.providerPage('chatgpt-web');
  this.timer=setInterval(()=>void this.poll(),1200);this.timer.unref?.();await this.poll();return this;
 }
 async prepare(page){
  if(this.prepared?.has(page))return;(this.prepared||=new WeakSet()).add(page);this.protectedPages.add(page);
  await page.exposeBinding('__fridaySharedMessage',({frame},message)=>{
   if(frame!==page.mainFrame())return {ok:false,error:'Top-level model page required'};
   return this.message(page,message).catch(error=>({ok:false,error:error.message}));
  });
  await page.addInitScript({content:`if(window===window.top){const start=()=>{${this.source}\n};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();}`});
  if(page.url()!=='about:blank')await page.evaluate(this.source).catch(()=>{});
  page.on('framenavigated',frame=>{if(frame===page.mainFrame())void this.updateBinding(page).catch(()=>{});});
  page.on('close',()=>{for(const [key,value]of this.pages)if(value===page)this.pages.delete(key);for(const [id,job]of this.running)if(job.page===page){void this.request('/event',{id,type:'error',message:'Protected model tab was closed by the user. Review its last request before resuming.'}).catch(()=>{});this.running.delete(id);}});
 }
 async providerPage(site,pair){
  const key=pair?pair.sessionId+':'+site:'home:'+site;
  let page=this.pages.get(key);if(page&&!page.isClosed())return page;
  const wanted=pair?.url||SITES[site].url;
  // Reuse a restored exact conversation or unbound home tab, never another session's tab.
  const occupied=new Set(this.pages.values());
  page=this.context.pages().find(candidate=>this.protectedPages.has(candidate)&&!occupied.has(candidate)&&websiteURL(site,candidate.url())===websiteURL(site,wanted));
  if(!page&&pair){const home=this.pages.get('home:'+site);if(home&&!home.isClosed()){page=home;this.pages.delete('home:'+site);}}
  if(!page){page=await createOwnedPage(this.context,this.protectedPages,true);await this.prepare(page);}
  this.pages.set(key,page);
  if(websiteURL(site,page.url())!==websiteURL(site,wanted))await page.goto(wanted,{waitUntil:'domcontentloaded',timeout:60000});
  return page;
 }
 async updateBinding(page){
  for(const [key,pair]of this.bindings)if(this.pages.get(key)===page){const safe=websiteURL(pair.site,page.url());if(safe&&safe!==pair.url){pair.url=safe;await this.save();const job=[...this.running.values()].find(job=>job.page===page);if(job)await this.request('/event',{id:job.id,type:'binding',...pair});}}
 }
 dispatch(page,message){return page.evaluate(message=>globalThis.__fridaySharedDispatch?.(message),message);}
 async message(page,message){
  if(!this.protectedPages.has(page)||!Object.keys(SITES).some(site=>websiteURL(site,page.url())))throw new Error('Model page origin not allowed');
  const job=message?.type==='harness-event'?this.running.get(message.event?.id):this.running.get(message?.jobId);
  const pair=[...this.bindings.entries()].find(([key])=>this.pages.get(key)===page)?.[1];
  const owned=()=>{if(!job||job.page!==page)throw new Error('Unowned browser job');return job;};
  if(message?.type==='harness-event'){owned();await this.request('/event',message.event);return {ok:true};}
  if(message?.type==='harness-job-file'){owned();return {ok:true,result:await this.request('/job-file',{jobId:job.id,id:message.id,index:message.index})};}
  if(message?.type==='harness-listener-refresh'){const listener=this.listeners.find(item=>item.tabId===pair?.tabId);return listener?{ok:true,config:{...listener,online:this.online,enabled:listener.enabled&&this.enabledSites.includes(listener.site)}}:{ok:false};}
  if(message?.type==='harness-file-transfer'){
   if(!pair||!this.enabledSites.includes(pair.site)||!['begin','chunk','finish'].includes(message.action))throw new Error('No enabled paired file destination');if(message.jobId)owned();
   return {ok:true,result:await this.request('/files/'+message.action,{...message.input,...pair,url:page.url(),jobId:message.jobId})};
  }
  if(['harness-web-message','harness-web-stop'].includes(message?.type)){
   if(!pair||!this.enabledSites.includes(pair.site))throw new Error('No enabled paired conversation');
   return this.request(message.type==='harness-web-stop'?'/inbound/stop':'/inbound',{...pair,url:page.url(),id:message.id,text:message.text,jobId:message.jobId,fileIds:message.fileIds});
  }
  // Native Playwright download events are scoped to the active model page.
  if(message?.type==='harness-download-watch'){owned();job.download=page.waitForEvent('download',{timeout:30000});job.download.catch(()=>{});return {ok:true,available:true,watchId:job.id};}
  if(message?.type==='harness-download-result'){
   owned();if(message.watchId!==job.id||!job.download)throw new Error('Unowned download');const item=await job.download;delete job.download;
   const path=await item.path();if(!path||await item.failure())throw new Error('Website download failed');
   const bytes=await readFile(path);if(bytes.length>32*1024*1024)throw new Error('Download exceeds 32 MB');
   const {createHash,randomUUID}=await import('node:crypto');const id=randomUUID();
   await this.request('/files/begin',{...pair,jobId:job.id,id,name:item.suggestedFilename(),size:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});
   for(let offset=0,index=0;offset<bytes.length;offset+=384*1024,index++)await this.request('/files/chunk',{...pair,jobId:job.id,id,index,data:bytes.subarray(offset,offset+384*1024).toString('base64')});
   return {ok:true,file:await this.request('/files/finish',{...pair,jobId:job.id,id})};
  }
  return {ok:false,error:'Unsupported model-page operation'};
 }
 async run(command){
  const job={...command,page:null};this.running.set(job.id,job);
  try{
   const key=job.sessionId+':'+job.site;let pair=this.bindings.get(key);
   if(!pair){pair={sessionId:job.sessionId,site:job.site,url:SITES[job.site].url,tabId:this.nextTabId++};this.bindings.set(key,pair);await this.save();}
   job.page=await this.providerPage(job.site,pair);await this.updateBinding(job.page);await this.request('/event',{id:job.id,type:'binding',...pair});
   let ready=false;
   // Login/load waiting is visible and cancellable; no uncertain prompt replay.
   while(this.running.has(job.id)&&!this.stopped){
    try{const state=await this.dispatch(job.page,{type:'harness-ping'});if(state?.hasEditor){ready=true;break;}}catch{}
    await this.request('/event',{id:job.id,type:'status',state:'reconnecting'});await new Promise(resolve=>setTimeout(resolve,1000));
   }
   if(!ready||!this.running.has(job.id))return;
   const result=await this.dispatch(job.page,{...job,page:undefined,type:'harness-run'});
   if(!result?.ok&&this.running.has(job.id))throw new Error(result?.error||'Model page agent unavailable');
   await this.updateBinding(job.page);
  }catch(error){if(this.running.has(job.id))await this.request('/event',{id:job.id,type:'error',message:error.message}).catch(()=>{});}
  finally{this.running.delete(job.id);}
 }
 async poll(){
  if(this.polling||this.stopped)return;this.polling=true;
  try{
   const result=await this.request('/poll',{transport:'shared-browser',version:BACKEND_VERSION,sites:this.enabledSites,bindings:[...this.bindings.values()],runningIds:[...this.running.keys()]});this.online=true;this.listeners=result.listeners||[];
   for(const [id,job]of this.running)if(!result.activeIds.includes(id)){this.running.delete(id);if(job.page)void this.dispatch(job.page,{type:'harness-cancel',id}).catch(()=>{});}
   for(const action of result.actions||[]){
    if(action.type==='open-site'&&Object.hasOwn(SITES,action.site)){const active=[...this.running.values()].find(job=>job.site===action.site);const page=active?.page||[...this.pages.entries()].find(([key,page])=>key.endsWith(':'+action.site)&&!page.isClosed())?.[1]||await this.providerPage(action.site);await page.bringToFront();}
    if(action.type==='configure-site'&&Object.hasOwn(SITES,action.site)&&typeof action.enabled==='boolean'){this.enabledSites=action.enabled?[...new Set([...this.enabledSites,action.site])]:this.enabledSites.filter(site=>site!==action.site);await this.save();if(action.enabled)void this.providerPage(action.site).catch(()=>{});}
    if(action.type==='focus'){const pair=this.bindings.get(action.sessionId+':'+action.site);if(pair)await(await this.providerPage(action.site,pair)).bringToFront();}
   }
   for(const command of result.commands||[])if(!this.running.has(command.id)){if(!this.running.size)void this.run(command);else await this.request('/event',{id:command.id,type:'error',message:'Friday model connection is busy'});}
   for(const listener of this.listeners){const page=this.pages.get(listener.sessionId+':'+listener.site);if(page&&!page.isClosed())void this.dispatch(page,{type:'harness-listen',config:{...listener,online:true,enabled:listener.enabled&&this.enabledSites.includes(listener.site)}}).catch(()=>{});}
  }catch{this.online=false;for(const listener of this.listeners){const page=this.pages.get(listener.sessionId+':'+listener.site);if(page&&!page.isClosed())void this.dispatch(page,{type:'harness-listen',config:{...listener,online:false,status:'Harness is offline — waiting to reconnect. Local tools cannot run.'}}).catch(()=>{});}}
  finally{this.polling=false;}
 }
 stop(){this.stopped=true;clearInterval(this.timer);}
}
