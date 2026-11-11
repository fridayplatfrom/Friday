import {WorkspaceBrowserState,workspaceIdentity,argumentDigest,readOnlyBrowserCall,restorableTab} from './workspace-browser-state.mjs';
import {randomUUID} from 'node:crypto';

export class WorkspaceBrowserManager{
 constructor({root,origins,launch,upstream,maxOpen=2}){Object.assign(this,{root,origins,launch,upstream,maxOpen});this.workspaces=new Map();this.lease=null;this.running=false;this.closing=false;}
 workspace(directory){const identity=workspaceIdentity(directory);if(!this.workspaces.has(identity.key))this.workspaces.set(identity.key,{state:new WorkspaceBrowserState(this.root,identity),context:null,lastUsed:0});return this.workspaces.get(identity.key);}
 async context(workspace){
  workspace.lastUsed=Date.now();if(workspace.context)return workspace.proxy;
  const open=[...this.workspaces.values()].filter(w=>w.context&&w!==workspace).sort((a,b)=>a.lastUsed-b.lastUsed);
  while(open.length>=this.maxOpen)await this.closeWorkspace(open.shift());
  const context=await this.launch(workspace.state.profile);workspace.context=context;
  const save=()=>{if(workspace.closing||workspace.restoring||workspace.context!==context)return;const tabs=context.pages().map(page=>restorableTab(page.url(),this.origins)).filter(Boolean);if(tabs.length)workspace.state.tabs(tabs,workspace.state.state.activeIndex);};
  const watch=page=>{page.on('framenavigated',()=>{clearTimeout(workspace.timer);workspace.timer=setTimeout(save,150);});page.on('close',()=>{clearTimeout(workspace.timer);workspace.timer=setTimeout(save,150);});};
  context.on('page',watch);context.on('close',()=>{clearTimeout(workspace.timer);workspace.context=null;const client=workspace.client;workspace.client=null;void client?.close().catch(()=>{});});context.pages().forEach(watch);
  workspace.restoring=true;
  try{
   const saved=workspace.state.state.tabs.filter(url=>restorableTab(url,this.origins)===url);
   const available=context.pages().slice();for(const url of saved){let page=available.find(p=>p.url()===url);if(page){available.splice(available.indexOf(page),1);continue;}page=await context.newPage();try{await page.goto(url,{waitUntil:'domcontentloaded',timeout:15000});}catch{/* keep saved URL; never resubmit a form */}}
   if(saved.length){for(const page of context.pages())if(page.url()==='about:blank')await page.close();await context.pages()[workspace.state.state.activeIndex]?.bringToFront();}
  }finally{workspace.restoring=false;}
  workspace.proxy=new Proxy(context,{get:(target,key)=>key==='close'?()=>this.closeWorkspace(workspace):typeof target[key]==='function'?target[key].bind(target):target[key]});return workspace.proxy;
 }
 saveTabs(workspace){if(!workspace.context)return;const urls=workspace.context.pages().map(p=>restorableTab(p.url(),this.origins)).filter(Boolean);workspace.state.tabs(urls,workspace.state.state.activeIndex);}
 async inspect(workspace,{tabId,focus=false}={}){
  if(this.running||this.lease||this.inspectFocus){if(focus)throw new Error('A workspace browser action is active.');return {...workspace.state.summary(),busy:true,live:false,tabDetails:[]};}
  if(!workspace.context)return {...workspace.state.summary(),live:false,tabDetails:[]};
  if(focus)this.inspectFocus=true;
  try{
  this.pageIds||=new WeakMap();
  const pages=workspace.context.pages().filter(page=>restorableTab(page.url(),this.origins));
  const tabDetails=await Promise.all(pages.map(async page=>{if(!this.pageIds.has(page))this.pageIds.set(page,randomUUID());let title;try{title=await Promise.race([page.title(),new Promise(resolve=>{const timer=setTimeout(()=>resolve('Browser tab'),800);timer.unref?.();})]);}catch{title='Browser tab';}return {id:this.pageIds.get(page),url:restorableTab(page.url(),this.origins),title};}));
  const index=tabId?tabDetails.findIndex(tab=>tab.id===tabId):Math.min(workspace.state.state.activeIndex,Math.max(0,pages.length-1));
  if(tabId&&index<0)throw new Error('That browser tab has changed. Refresh the tab list; no navigation was performed.');
  if(focus&&pages[index]){await pages[index].bringToFront();workspace.state.state.activeIndex=index;this.saveTabs(workspace);}
  let image=null;if(!focus&&pages[index])try{image='data:image/jpeg;base64,'+(await pages[index].screenshot({type:'jpeg',quality:55,timeout:2500})).toString('base64');}catch{}
  return {...workspace.state.summary(),live:true,tabDetails,selectedTab:tabDetails[index]?.id||null,image};
  }finally{if(focus)this.inspectFocus=false;}
 }
 async closeWorkspace(workspace){if(!workspace.context)return;this.saveTabs(workspace);workspace.closing=true;clearTimeout(workspace.timer);try{await workspace.context.close();}finally{workspace.context=null;workspace.closing=false;}}
 select(input){
  if(this.lease||this.running||this.inspectFocus)throw new Error('A workspace browser action is active.');
  if(typeof input.id!=='string'||!input.id||input.id.length>200||typeof input.sessionId!=='string'||typeof input.tool!=='string'||!/^browser_/.test(input.tool)||!/^([a-f0-9]{64})$/.test(input.digest))throw new Error('Invalid native browser execution scope.');
  const workspace=this.workspace(input.directory);this.lease={...input,workspace};return workspace.state.summary();
 }
 release(id){if(this.lease?.id===id){if(this.running)this.lease.releaseRequested=true;else this.lease=null;}}
 async call(name,args,signal){
  const lease=this.lease;if(!lease||lease.tool!==name||lease.digest!==argumentDigest(args))throw new Error('Browser tool requires its exact native workspace execution scope.');
  if(this.running)throw new Error('Browser execution is already active.');
  const workspace=lease.workspace,write=!readOnlyBrowserCall(name,args);let begun=false;this.running=true;
  try{
   signal?.throwIfAborted();if(write){workspace.state.begin(lease);begun=true;}
   if(!workspace.client)workspace.client=await this.upstream(()=>this.context(workspace),workspace.state.state.directory);
   const result=await workspace.client.callTool({name,arguments:args},undefined,{signal,timeout:300000});
   if(name==='browser_close'&&!result.isError)await this.closeWorkspace(workspace);
   if(write)workspace.state.settle(lease.id,!result.isError&&!signal?.aborted);
   if(name==='browser_tabs'&&args.action==='select'&&Number.isInteger(args.index))workspace.state.state.activeIndex=args.index;
   if(name!=='browser_close')this.saveTabs(workspace);
   const status=write?workspace.state.state.actions.find(action=>action.id===lease.id)?.status:'read-only';
   return {...result,...(signal?.aborted?{isError:true}:{}),content:[...(result.content||[]),{type:'text',text:'Friday workspace browser receipt: '+JSON.stringify({workspace:workspace.state.state.key,actionId:lease.id,status,pending:workspace.state.pending().length})}]};
  }catch(error){if(begun)workspace.state.settle(lease.id,false);throw error;}
  finally{this.running=false;if(lease.releaseRequested&&this.lease===lease)this.lease=null;}
 }
 async close(){this.closing=true;for(const w of this.workspaces.values()){await this.closeWorkspace(w);await w.client?.close().catch(()=>{});}}
}
