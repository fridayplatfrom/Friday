// Explicit operator runner: submit a supplied brief to an existing native Friday
// session. Native Harness owns execution, permissions, files and tool results.
import fs from 'node:fs';
import {join,resolve} from 'node:path';
import {homedir} from 'node:os';
import {randomUUID} from 'node:crypto';
import {HttpAgent} from '@ag-ui/client';

const [threadId,briefPath,expectedSite='kimi-web']=process.argv.slice(2);
if(!['kimi-web','gemini-web','deepseek-web','chatgpt-web'].includes(expectedSite))throw new Error('Unknown expected website provider. Select it in the native Friday model selector first.');
if(!threadId||!briefPath)throw new Error('Supply a native Friday session ID and a task brief file.');
const prompt=fs.readFileSync(resolve(briefPath),'utf8');
if(!prompt.trim()||prompt.length>20000)throw new Error('Expected a nonempty task brief under 20,000 characters.');
const logs=join(homedir(),'.dsh/logs');
const latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
if(!latest)throw new Error('Friday server log is unavailable.');
const login=fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];
if(!login)throw new Error('Current owner login URL is unavailable.');
const admitted=await fetch(login,{redirect:'manual'});
const cookie=admitted.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');
if(!cookie)throw new Error('Friday owner authentication is unavailable.');
const headers={Cookie:cookie,'X-Harness-Models':'1','Content-Type':'application/json'};
const root='http://127.0.0.1:3030/browser-models';
const stateResponse=await fetch(root+'/status',{headers});
if(!stateResponse.ok)throw new Error('Friday status is unavailable.');
const state=await stateResponse.json();
if(!state.connected)throw new Error('Connect Friday before submitting. Native sessions remain individually ordered; excess browser requests are queued.');
const requiredVersion=process.argv.find(value=>value.startsWith('--require-version='))?.slice('--require-version='.length);
if(requiredVersion&&(!/^\d+\.\d+\.\d+$/.test(requiredVersion)||state.backendVersion!==requiredVersion||state.extensionVersion!==requiredVersion))throw new Error(`Activate matching backend and Chrome extension ${requiredVersion} before this acceptance test. No prompt was submitted.`);
if(!state.enabledSites.includes(expectedSite))throw new Error('Enable the selected website connection before submitting this task.');
const recovery=await fetch(root+'/recover-session',{method:'POST',headers,body:JSON.stringify({sessionId:threadId})});
if(!recovery.ok)throw new Error((await recovery.json()).error||'Native conversation recovery failed. No prompt was submitted.');
const restored=await recovery.json();
const sessionResponse=await fetch(root+'/session/'+encodeURIComponent(threadId),{headers});
const session=await sessionResponse.json();
if(!sessionResponse.ok||!session.sessionId)throw new Error('Use an initialized native Friday session for this build.');
if(!session.nativeSession?.loaded)throw new Error('Open this existing conversation in Friday before the live test. No prompt was submitted.');
if(restored.provider!=='browser-web'||restored.model!==expectedSite)throw new Error('The native model selector does not match the requested test provider. No prompt was submitted.');
if(session.nativeSession.status==='running')throw new Error('The native conversation is busy. No prompt was submitted.');
const runId=randomUUID(),record={threadId,runId,startedAt:new Date().toISOString(),status:'running',toolCalls:[],toolResults:0};
const evidence=new URL('../../output/friday-orbit-'+expectedSite+'-'+runId+'.json',import.meta.url);
const save=()=>fs.writeFileSync(evidence,JSON.stringify(record,null,2));
save();
const agent=new HttpAgent({url:root+'/ag-ui',threadId,headers,initialMessages:[{id:randomUUID(),role:'user',content:prompt}]});
try{
 await agent.runAgent({runId},{onEvent:({event})=>{
  if(event.type==='TEXT_MESSAGE_CONTENT'){
   record.streamedCharacters=(record.streamedCharacters||0)+event.delta.length;
   if(!record.firstTextAt){record.firstTextAt=new Date().toISOString();save();console.log(JSON.stringify({event:'first-text'}));}
  }
  if(event.type==='TOOL_CALL_START'){record.toolCalls.push({id:event.toolCallId,name:event.toolCallName});console.log(JSON.stringify({event:'tool-start',name:event.toolCallName,count:record.toolCalls.length}));save();}
  if(event.type==='TOOL_CALL_RESULT'){record.toolResults++;save();}
  if(event.type==='RUN_ERROR'){record.status='error';record.error=event.message;save();}
  if(event.type==='RUN_FINISHED'){record.status='finished';save();}
 }});
 record.report=agent.messages.filter(m=>m.role==='assistant').at(-1)?.content||'';
 record.endedAt=new Date().toISOString();save();
 console.log(JSON.stringify({status:record.status,runId,toolCalls:record.toolCalls.length,toolResults:record.toolResults,report:record.report}));
 if(record.status!=='finished')process.exitCode=1;
}catch(error){record.status='error';record.error=String(error.message);record.endedAt=new Date().toISOString();save();throw error;}
