import {createHash,randomUUID} from 'node:crypto';
import {mkdirSync,readFileSync,writeFileSync,renameSync,existsSync,realpathSync,openSync,fsyncSync,closeSync} from 'node:fs';
import {join,resolve,isAbsolute} from 'node:path';

export function workspaceIdentity(directory){
 if(typeof directory!=='string'||!isAbsolute(directory))throw new Error('A native absolute workspace directory is required.');
 let canonical=realpathSync(directory);if(process.platform==='win32')canonical=canonical.toLowerCase();
 return {key:createHash('sha256').update(canonical).digest('hex'),directory:canonical};
}
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
export const argumentDigest=value=>createHash('sha256').update(JSON.stringify(canonical(value??{}))).digest('hex');
export const readOnlyBrowserCall=(name,args={})=>['browser_snapshot','browser_take_screenshot','browser_console_messages','browser_network_requests','browser_network_request','browser_find','browser_wait_for'].includes(name)||(name==='browser_tabs'&&args.action==='list');
export function restorableTab(value,origins){
 try{
  const url=new URL(value);if(!['http:','https:'].includes(url.protocol)||url.username||url.password||!origins.includes('*')&&!origins.includes(url.origin))return null;
  let route=url.pathname;for(let i=0;i<3;i++){const decoded=decodeURIComponent(route);if(decoded===route)break;route=decoded;}
  route=route.replaceAll('\\','/');
  if(/[\x00-\x1f\x7f]/.test(route)||/(?:^|\/)(?:logout|logoff|signout|sign-out|callback|authorize|oauth2?|login|signin|sign-in|intent)(?:[\/.;]|$)/i.test(route))return null;
  // Persist common search queries only; credentials, OAuth codes, prefilled posts and fragments are excluded.
  const search=new URLSearchParams();for(const [key,value]of url.searchParams)if(['k','q','query','search','page'].includes(key)&&value.length<=2000)search.append(key,value);
  return url.origin+url.pathname+(search.size?'?'+search:'');
 }catch{return null;}
}

export class WorkspaceBrowserState{
 constructor(root,identity){
  if(!/^[a-f0-9]{64}$/.test(identity.key))throw new Error('Invalid workspace identity.');
  this.directory=join(root,identity.key);this.profile=join(this.directory,'profile');this.file=join(this.directory,'state.json');
  mkdirSync(this.directory,{recursive:true});
  this.state={version:1,key:identity.key,directory:identity.directory,tabs:[],activeIndex:0,actions:[],revision:0};
  if(existsSync(this.file)){
   let saved;try{saved=JSON.parse(readFileSync(this.file,'utf8'));}catch{throw new Error('Browser workspace state is damaged; preserve it for recovery.');}
   if(!saved||typeof saved!=='object'||Array.isArray(saved))throw new Error('Browser workspace state is invalid. Preserve it for recovery.');
   const statuses=new Set(['started','completed','uncertain','confirmed-applied','confirmed-not-applied']);
   const actionsValid=Array.isArray(saved.actions)&&saved.actions.every(action=>action&&typeof action.id==='string'&&action.id.length>0&&typeof action.sessionId==='string'&&typeof action.tool==='string'&&action.tool.startsWith('browser_')&&/^[a-f0-9]{64}$/.test(action.digest)&&statuses.has(action.status)&&Number.isFinite(action.startedAt)&&(action.delivered===undefined||typeof action.delivered==='boolean'));
   if(saved.version!==1||saved.key!==identity.key||saved.directory!==identity.directory||!Array.isArray(saved.tabs)||saved.tabs.length>40||saved.tabs.some(tab=>typeof tab!=='string')||!Number.isSafeInteger(saved.revision)||saved.revision<0||!Number.isInteger(saved.activeIndex)||saved.activeIndex<0||!actionsValid||new Set(saved.actions.map(a=>a.id)).size!==saved.actions.length)throw new Error('Browser workspace state is invalid or does not match this workspace. Preserve it for recovery.');
   this.state=saved;
  }
  let changed=false;for(const action of this.state.actions)if(action.status==='started'||action.status==='completed'&&!action.delivered){action.status='uncertain';changed=true;}
  if(changed)this.save();
 }
 save(){this.state.revision++;const fd=openSync(this.file+'.tmp','w');try{writeFileSync(fd,JSON.stringify(this.state));fsyncSync(fd);}finally{closeSync(fd);}renameSync(this.file+'.tmp',this.file);}
 tabs(values,activeIndex=0){this.state.tabs=values.slice(0,40);this.state.activeIndex=Math.max(0,Math.min(activeIndex,values.length-1));this.save();}
 pending(){return this.state.actions.filter(a=>a.status==='uncertain'||a.status==='started'||a.status==='completed'&&!a.delivered);}
 checkBegin(call){
  if(this.state.actions.some(a=>a.id===call.id))throw new Error('This browser action already has a receipt. It was not replayed. Inspect its saved native result.');
  if(this.pending().length)throw new Error('An interrupted browser action may already have applied. Inspect the page and review its receipt in Friday before another browser write. Nothing was replayed.');
 }
 begin(call){
  this.checkBegin(call);
  const record={id:call.id,sessionId:call.sessionId,tool:call.tool,digest:call.digest,status:'started',startedAt:Date.now()};
  this.state.actions.push(record);this.save();return record;
 }
 settle(id,success){const action=this.state.actions.find(a=>a.id===id);if(!action)return;action.status=success?'completed':'uncertain';action.endedAt=Date.now();this.save();}
 rejectBeforeInput(id,reason='native-reference-not-found'){if(!['native-reference-not-found','native-tab-not-found'].includes(reason))throw Error('Unsupported pre-input rejection.');const action=this.state.actions.find(a=>a.id===id&&a.status==='started');if(!action)throw Error('Only an admitted action can be rejected before input.');action.status='confirmed-not-applied';action.endedAt=Date.now();action.rejection=reason;this.save();}
 acknowledge(id,sessionId,success=true){const action=this.state.actions.find(a=>a.id===id&&a.sessionId===sessionId);if(action?.status==='completed'&&!action.delivered){if(success)action.delivered=true;else action.status='uncertain';this.save();}}
 review(id,decision,revision){
  if(!['confirmed-applied','confirmed-not-applied'].includes(decision))throw new Error('Inspect the actual website outcome first.');
  if(revision!==this.state.revision)throw new Error('Browser recovery state changed. Refresh before reviewing.');
  const action=this.state.actions.find(a=>a.id===id);if(!action||!this.pending().includes(action)||action.status==='started')throw new Error('Only an interrupted or unacknowledged action can be reviewed.');
  action.status=decision;action.reviewedAt=Date.now();action.reviewId=randomUUID();this.save();
 }
 summary(){return {key:this.state.key,directory:this.state.directory,tabs:this.state.tabs,activeIndex:this.state.activeIndex,revision:this.state.revision,pending:this.pending(),recent:this.state.actions.slice(-8),persistent:true};}
}
