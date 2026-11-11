import {createServer} from 'node:http';
import {timingSafeEqual} from 'node:crypto';

/** Private native-dispatch channel. Never accepts browser origins or public hosts. */
export function workspaceControlServer(manager,token){
 if(typeof token!=='string'||token.length<32)throw new Error('A private control token is required.');
 const expected=Buffer.from('Bearer '+token);
 const routes=new Set(['/select','/release','/checkpoint','/status','/acknowledge','/open','/review','/preview','/focus']);
 const server=createServer(async(req,res)=>{
  const reply=(status,value)=>{if(res.destroyed)return;res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(value));};
  const actual=Buffer.from(req.headers.authorization||'');
  if(req.headers.host!==`127.0.0.1:${server.address().port}`||req.method!=='POST'||req.headers.origin||actual.length!==expected.length||!timingSafeEqual(actual,expected))return reply(403,{error:'Local authenticated control required.'});
  if(!routes.has(req.url))return reply(404,{error:'Unknown browser control.'});
  if(!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type']||''))return reply(415,{error:'JSON control request required.'});
  if(Number(req.headers['content-length'])>16384)return reply(413,{error:'Control request too large.'});
  try{
   let size=0;const chunks=[];for await(const chunk of req.iterator({destroyOnReturn:false})){size+=chunk.length;if(size>16384){req.resume();return reply(413,{error:'Control request too large.'});}chunks.push(chunk);}
   const input=JSON.parse(Buffer.concat(chunks).toString('utf8'));
   if(!input||typeof input!=='object'||Array.isArray(input))throw new Error('Control arguments must be an object.');
   if(req.url==='/select')return reply(200,manager.select(input));
   if(req.url==='/release'){manager.release(input.id);return reply(200,{ok:true});}
   if(req.url==='/checkpoint'){if(manager.running||manager.lease)throw new Error('A native browser action is active.');manager.running=true;try{await manager.close();return reply(200,{ok:true});}finally{manager.running=false;}}
   const workspace=manager.workspace(input.directory);
   if(req.url==='/status')return reply(200,workspace.state.summary());
   if(req.url==='/preview')return reply(200,await manager.inspect(workspace,{tabId:input.tabId}));
   if(req.url==='/focus')return reply(200,await manager.inspect(workspace,{tabId:input.tabId,focus:true}));
   if(req.url==='/acknowledge'){workspace.state.acknowledge(input.id,input.sessionId,input.success!==false);return reply(200,{ok:true});}
   if(manager.running||manager.lease)throw new Error('A native browser action is active.');
   if(req.url==='/open'){manager.running=true;try{await manager.context(workspace);return reply(200,workspace.state.summary());}finally{manager.running=false;}}
   workspace.state.review(input.id,input.decision,input.revision);return reply(200,workspace.state.summary());
  }catch(error){reply(409,{error:error.message});}
 });
 server.requestTimeout=10000;server.headersTimeout=10000;server.keepAliveTimeout=5000;server.maxHeadersCount=30;
 return server;
}
