import {createServer} from 'node:http';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {createRequire} from 'node:module';
import {mkdirSync,writeFileSync,renameSync,readFileSync,unlinkSync} from 'node:fs';
import {dirname} from 'node:path';
import {acceptDownloadBehavior,taskDownload} from '../native-task-downloads.mjs';
const {wsServer:WebSocketServer}=createRequire(import.meta.url)('playwright-core/lib/utilsBundle');

// A scoped CDP adapter, not an Electron remote-debugging port. Only task guests
// owned by the authenticated Harness renderer can enter this connection.
export class TaskBrowserConnection {
 constructor({guests,workspace,directory,sessionId,open,send,validate=()=>{}}){Object.assign(this,{guests,workspace,directory,sessionId,open,send,validate});this.sessions=new Map();this.children=new Map();this.attaching=new Map();this.unsubscribe=guests.subscribe?.(()=>{if(this.autoAttach&&!this.disposed)for(const lease of this.eligible())void this.attach(lease).catch(()=>{});});}
 eligible(){return [...this.guests.leases.values()].filter(l=>l.workspace===this.workspace&&l.sessionId===this.sessionId&&l.guest&&!l.guest.isDestroyed());}
 async attach(lease){
  if(this.disposed)throw Error('The task browser connection has closed.');
  const guest=lease.guest;if(this.sessions.has(String(guest.id)))return this.sessions.get(String(guest.id));
  if(this.attaching.has(guest.id))return this.attaching.get(guest.id);
  const pending=(async()=>{
   if(guest.debugger.isAttached())throw Error('The task tab debugger is already in use. Close its developer tools and retry.');
   guest.debugger.attach('1.3');
   let raw;try{raw=await guest.debugger.sendCommand('Target.getTargetInfo');}catch(error){guest.debugger.detach();throw error;}
   if(this.disposed){guest.debugger.detach();throw Error('The task browser connection has closed.');}
   const session={guest,id:String(guest.id),target:{...raw.targetInfo,type:'page',browserContextId:'friday-task-context'}};
   const downloadHandler=item=>{this.validate();if(!this.downloadsEnabled)throw Error('Task downloads are not enabled.');return taskDownload(item,{guest,directory:this.directory,send:this.send,validate:this.validate});};
   lease.downloadHandler=downloadHandler;
   const onMessage=(_e,method,params,child)=>{
    if(method==='Target.attachedToTarget'&&params.sessionId)this.children.set(params.sessionId,session);
    if(method==='Target.detachedFromTarget')this.children.delete(params.sessionId);
    this.send({method,params,sessionId:child||session.id});
   };
   const onDetach=()=>{this.sessions.delete(session.id);this.send({method:'Target.detachedFromTarget',params:{sessionId:session.id,targetId:session.target.targetId}});};
   session.dispose=()=>{if(lease.downloadHandler===downloadHandler)delete lease.downloadHandler;guest.debugger.removeListener('message',onMessage);guest.debugger.removeListener('detach',onDetach);if(!guest.isDestroyed()&&guest.debugger.isAttached())guest.debugger.detach();};
   this.sessions.set(session.id,session);guest.debugger.on('message',onMessage);guest.debugger.on('detach',onDetach);
   this.send({method:'Target.attachedToTarget',params:{sessionId:session.id,targetInfo:session.target,waitingForDebugger:false}});return session;
  })();this.attaching.set(guest.id,pending);try{return await pending;}finally{this.attaching.delete(guest.id);}
 }
 async command(method,params={},sessionId){
  this.validate();
  if(sessionId){
   const session=this.sessions.get(sessionId)||this.children.get(sessionId);
   if(!session||!this.eligible().some(l=>l.guest===session.guest))throw Error('Task tab is no longer owned by this workspace and conversation.');
   if(/^(Browser|Storage)\./.test(method))throw Error('Browser-wide commands are unavailable on a task tab.');
   if(method.startsWith('Target.')&&!['Target.setAutoAttach','Target.getTargetInfo','Target.detachFromTarget'].includes(method))throw Error('Cross-target browser commands are unavailable.');
   if(method==='Target.detachFromTarget'&&!this.children.has(params.sessionId))throw Error('Unknown child task target.');
   if(method==='Page.navigate'&&!this.guests.allowedNavigation(params.url))throw Error('This address is not permitted in the task Browser.');
   if(method==='Page.handleJavaScriptDialog'&&params.accept)throw Error('Native Browser dialogs retain their existing policy.');
   if(method==='Target.getTargetInfo'&&!this.children.has(sessionId))return {targetInfo:session.target};
   // Electron's Page.bringToFront does not select the owner's retained tab.
   // Also focus the guest before input: Chromium can otherwise send insertText
   // to the embedder's focused composer while the target guest is hidden.
   if(method==='Page.bringToFront'||method.startsWith('Input.')||method==='DOM.focus'){
    if(method==='Page.bringToFront'||!session.guest.isFocused?.())await this.open({focusGuestId:session.guest.id});
    session.guest.focus?.();
    if(method==='Page.bringToFront')return {};
   }
   return session.guest.debugger.sendCommand(method,params,this.children.has(sessionId)?sessionId:undefined);
  }
  if(method==='Browser.getVersion')return {protocolVersion:'1.3',product:'Chrome/'+process.versions.chrome,userAgent:'Friday Native Browser',revision:''};
  if(method==='Browser.setDownloadBehavior'){this.downloadsEnabled=acceptDownloadBehavior(params,this.directory);return {};}
  if(method==='Target.setAutoAttach'){this.autoAttach=params.autoAttach!==false;for(const lease of this.eligible())await this.attach(lease);return {};}
  if(method==='Target.getTargetInfo')return {targetInfo:{targetId:'friday-task-browser',type:'browser',title:'Friday task Browser',url:''}};
  if(method==='Target.getTargets')return {targetInfos:[...this.sessions.values()].map(s=>s.target)};
  if(method==='Target.createTarget'){
   if(params.url!=='about:blank'&&!this.guests.allowedNavigation(params.url))throw Error('Unsupported task Browser address.');
   const lease=await this.open({fresh:true,url:params.url==='about:blank'?'https://example.com/':params.url});
   return {targetId:(await this.attach(lease)).target.targetId};
  }
  if(method==='Target.closeTarget'){
   const session=[...this.sessions.values()].find(s=>s.target.targetId===params.targetId);
   if(!session)throw Error('Unknown task Browser target.');
   await this.open({closeGuestId:session.guest.id});return {success:true};
  }
  if(method==='Target.activateTarget'){
   const session=[...this.sessions.values()].find(s=>s.target.targetId===params.targetId);
   if(!session)throw Error('Unknown task Browser target.');await this.open({focusGuestId:session.guest.id});return {};
  }
  if(method==='Browser.close'){this.dispose();return {};}
  throw Error('Unsupported browser-level command: '+method);
 }
 dispose(){this.disposed=true;this.unsubscribe?.();for(const session of this.sessions.values())session.dispose();this.sessions.clear();this.children.clear();}
}

export async function startTaskBrowserRelay({guests,connect,file}){
 const token=randomBytes(32).toString('hex'),tickets=new Map(),connections=new Set();
 const authorized=req=>{const actual=Buffer.from(req.headers.authorization||''),expected=Buffer.from('Bearer '+token);return !req.headers.origin&&actual.length===expected.length&&timingSafeEqual(actual,expected)&&req.headers.host===`127.0.0.1:${server.address().port}`;};
 const server=createServer(async(req,res)=>{
  const reply=(status,data)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(data));};
  if(!authorized(req))return reply(403,{error:'Private desktop connection required.'});
  if(req.method!=='POST'||req.url!=='/connect')return reply(404,{error:'Unknown desktop control.'});
  try{let body='';for await(const chunk of req){body+=chunk;if(body.length>16384)throw Error('Request too large.');}const input=JSON.parse(body);const scope=await connect(input);const ticket=randomBytes(32).toString('hex');tickets.set(ticket,{scope,until:Date.now()+15000});for(const [key,value]of tickets)if(value.until<Date.now())tickets.delete(key);reply(200,{endpoint:`ws://127.0.0.1:${server.address().port}/${ticket}`});}
  catch(error){reply(409,{error:error.message});}
 });
 const sockets=new WebSocketServer({noServer:true,maxPayload:16*1024*1024});
 server.on('upgrade',(req,socket,head)=>{
  const ticket=req.url?.slice(1),entry=tickets.get(ticket);tickets.delete(ticket);
  if(!authorized(req)||!entry||entry.until<Date.now()){socket.destroy();return;}
  sockets.handleUpgrade(req,socket,head,ws=>{
   const connection=new TaskBrowserConnection({guests,...entry.scope,send:value=>{if(ws.readyState===1)ws.send(JSON.stringify(value));}});connections.add(connection);
   ws.on('message',async raw=>{let message;try{message=JSON.parse(raw.toString());const result=await connection.command(message.method,message.params,message.sessionId);if(ws.readyState===1)ws.send(JSON.stringify({id:message.id,sessionId:message.sessionId,result}));}catch(error){if(ws.readyState===1)ws.send(JSON.stringify({id:message?.id,sessionId:message?.sessionId,error:{message:error.message}}));}});
   ws.on('close',()=>{connection.dispose();connections.delete(connection);});ws.on('error',()=>{});
  });
 });
 server.requestTimeout=35000;server.headersTimeout=10000;
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 mkdirSync(dirname(file),{recursive:true});writeFileSync(file+'.tmp',JSON.stringify({port:server.address().port,token,pid:process.pid}));renameSync(file+'.tmp',file);
 return {close(){for(const connection of connections)connection.dispose();for(const client of sockets.clients)client.terminate();sockets.close();server.close();try{if(JSON.parse(readFileSync(file,'utf8')).token===token)unlinkSync(file);}catch{}}};
}
