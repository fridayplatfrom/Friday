import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {taskArtifacts} from './native-task-downloads.mjs';
export const desktopBrowserFile=join(homedir(),'.dsh/browser-connector/desktop-browser-control.json');

/** Attach to Friday's scoped native guests; never launch or fall back to Chrome. */
export async function nativeTaskContext(chromium,{directory,sessionId},file=desktopBrowserFile){
 let config;try{config=JSON.parse(readFileSync(file,'utf8'));}catch{throw Error('Open Friday Desktop to use its native right-side Browser. No separate browser was launched.');}
 if(!Number.isInteger(config.port)||config.port<1||config.port>65535||!/^[a-f0-9]{64}$/.test(config.token||''))throw Error('Invalid Friday Desktop browser connection.');
 let response;try{response=await fetch(`http://127.0.0.1:${config.port}/connect`,{method:'POST',headers:{Authorization:'Bearer '+config.token,'Content-Type':'application/json'},body:JSON.stringify({directory,sessionId}),signal:AbortSignal.timeout(35000)});}catch{throw Error('Friday Desktop is not responding. Reopen it; no separate browser was launched and no tool action was replayed.');}
 const result=await response.json();if(!response.ok)throw Error(result.error||'Friday native Browser is unavailable.');
 const endpoint=new URL(result.endpoint);
 if(endpoint.protocol!=='ws:'||endpoint.hostname!=='127.0.0.1'||endpoint.port!==String(config.port)||!/^\/[a-f0-9]{64}$/.test(endpoint.pathname))throw Error('Invalid native task Browser endpoint.');
 const browser=await chromium.connectOverCDP(endpoint.href,{headers:{Authorization:'Bearer '+config.token},artifactsDir:taskArtifacts(directory),isLocal:true,timeout:20000});
 const context=browser.contexts()[0];if(!context){await browser.close();throw Error('Native Browser did not expose its task context.');}
 // Disconnecting an MCP client must not close the retained UI tabs or clear login.
 return new Proxy(context,{get:(target,key)=>key==='close'?()=>browser.close():typeof target[key]==='function'?target[key].bind(target):target[key]});
}
