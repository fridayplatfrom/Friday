import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {argumentDigest} from './workspace-browser-state.mjs';
export const controlFile=join(homedir(),'.dsh','browser-connector','workspace-browser-control.json');
export async function browserControl(action,input,file=controlFile){
 const config=JSON.parse(readFileSync(file,'utf8'));
 if(!Number.isInteger(config.port)||config.port<1||config.port>65535||typeof config.token!=='string')throw new Error('Workspace browser is not ready.');
 const response=await fetch(`http://127.0.0.1:${config.port}/${action}`,{method:'POST',headers:{Authorization:'Bearer '+config.token,'Content-Type':'application/json'},body:JSON.stringify(input),signal:AbortSignal.timeout(action==='open'?60000:10000)});
 const result=await response.json();if(!response.ok)throw new Error(result.error||'Workspace browser control failed.');return result;
}
/** Scope native tool dispatch; preserve the original Harness tool and its permissions. */
export function installWorkspaceBrowser(ctx,control=browserControl){
 let tail=Promise.resolve();
 ctx.on('tools/execute',async(exec,next)=>{
  if(!exec.name.startsWith('mcp__browser__'))return next();
  const directory=exec.agent?.session?.header?.cwd;
  if(!directory)throw new Error('Native workspace identity is missing; browser action was not dispatched.');
  const previous=tail;let unlock;tail=new Promise(resolve=>{unlock=resolve;});
  await previous;
  let attempted=false;
  try{
   exec.signal?.throwIfAborted();
   attempted=true;await control('select',{directory,sessionId:exec.agent.session.id,id:exec.callId,tool:exec.name.slice('mcp__browser__'.length),digest:argumentDigest(exec.arguments)});
   return await next();
  }finally{try{if(attempted)await control('release',{id:exec.callId});}finally{unlock();}}
 });
}
