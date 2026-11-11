// Explicit synthetic acceptance runner, never loaded by production or npm test.
import fs from 'node:fs';import {join} from 'node:path';import {homedir} from 'node:os';import {randomUUID} from 'node:crypto';import {setTimeout as delay} from 'node:timers/promises';
import {HttpAgent} from '@ag-ui/client';
const site=process.argv.find(a=>a.startsWith('--site='))?.slice(7)||'chatgpt-web';if(!['chatgpt-web','deepseek-web','gemini-web','kimi-web'].includes(site))throw new Error('Unsupported acceptance provider.');
const threadId=process.argv[2];if(!threadId)throw new Error('Supply the open synthetic Friday session.');
const logs=join(homedir(),'.dsh/logs'),log=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,log),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];if(!login)throw new Error('Current owner login URL unavailable.');
const admitted=await fetch(login,{redirect:'manual'}),cookie=admitted.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');if(!cookie)throw new Error('Owner authentication unavailable.');
const root='http://127.0.0.1:3030',headers={Cookie:cookie,'X-Harness-Models':'1','Content-Type':'application/json'};
const api=async(action,body)=>{const r=await fetch(root+'/browser-models/'+action,{headers,method:body?'POST':'GET',...(body?{body:JSON.stringify(body)}:{})});if(!r.ok)throw new Error('Friday owner route failed '+r.status);return r.json();};
const wait=async(predicate)=>{for(let i=0;i<100;i++){const value=await predicate();if(value)return value;await delay(1000);}throw new Error('Acceptance condition did not settle.');};
async function run(text){const runId=randomUUID(),events=[],client=new HttpAgent({url:root+'/browser-models/ag-ui',threadId,headers,initialMessages:[{id:randomUUID(),role:'user',content:text}]});await client.runAgent({runId},{onEvent:({event})=>events.push(event)});return {runId,events,report:client.messages.filter(m=>m.role==='assistant').at(-1)?.content||''};}
let failed;
if(process.argv.includes('--enable-all')){for(const site of ['chatgpt-web','deepseek-web','gemini-web','kimi-web'])await api('connect',{site});await wait(async()=>(await api('status')).enabledSites.length===4);const status=await api('status');console.log(JSON.stringify({backendVersion:status.backendVersion,extensionVersion:status.extensionVersion,enabledSites:status.enabledSites}));process.exit(0);}
if(process.argv.includes('--health-only')){await api('health',{site,sessionId:threadId});await delay(2000);console.log(JSON.stringify((await api('status')).providers.find(p=>p.id===site).health));process.exit(0);}
console.log('Checking controlled disconnected-provider failure');
if(process.argv.includes('--resume')){const saved=await api('session/'+encodeURIComponent(threadId));failed={runId:saved.aguiRuns.findLast(r=>r.status==='error')?.runId,diagnostic:saved.recovery.at(-1)};}else try{
 await api('disconnect',{site});await wait(async()=>!(await api('status')).enabledSites.includes(site));
 failed=await run('Synthetic Friday disconnected-provider test. Reply exactly FRIDAY_SHOULD_NOT_SUBMIT. Do not use tools.');
 if(failed.events.at(-1)?.type!=='RUN_ERROR')throw new Error('Disconnected request did not fail explicitly.');
 const diagnostic=(await api('session/'+encodeURIComponent(threadId))).recovery?.at(-1);
 if(diagnostic?.submission!=='not-submitted'||diagnostic.automaticResubmit!==false)throw new Error('Failure receipt lost submission safety.');
 console.log('Verified not-submitted diagnostic; no automatic resend');
 failed.diagnostic=diagnostic;
}finally{await api('connect',{site});await wait(async()=>(await api('status')).enabledSites.includes(site));}
if(process.argv.includes('--resume'))await api('focus',{site,sessionId:threadId});
console.log('Waiting for paired '+site+' readiness');
await wait(async()=>{await api('health',{site,sessionId:threadId});await delay(1300);return (await api('status')).providers.find(p=>p.id===site).health.state==='ready';});
console.log('Running real '+site+' native tool round trip');
const success=await run('Friday provider-framework acceptance. Use native pwsh exactly once to print FRIDAY_PROVIDER_TOOL_OK. Do not modify files or run other tools. After its actual result, return a complete English report beginning FRIDAY_PROVIDER_REPORT_START and ending FRIDAY_PROVIDER_REPORT_END, including the actual output.');
const tools=success.events.filter(e=>e.type==='TOOL_CALL_RESULT');
const calls=success.events.filter(e=>e.type==='TOOL_CALL_START');
if(success.events.at(-1)?.type!=='RUN_FINISHED'||calls.length!==1||calls[0].toolCallName!=='pwsh'||tools.length!==1||!tools[0].content.includes('FRIDAY_PROVIDER_TOOL_OK')||!success.report.includes('FRIDAY_PROVIDER_REPORT_START')||!success.report.includes('FRIDAY_PROVIDER_REPORT_END'))throw new Error(site+' acceptance incomplete; inspect native history before retrying.');
const status=await api('status');
const evidence={checkedAt:new Date().toISOString(),version:status.backendVersion,extensionVersion:status.extensionVersion,provider:site,failedRunId:failed.runId,diagnostic:failed.diagnostic,successRunId:success.runId,toolCalls:calls.map(c=>({id:c.toolCallId,name:c.toolCallName})),toolResults:tools.length,reportCharacters:success.report.length,providerHealth:status.providers.map(p=>({id:p.id,capabilities:p.capabilities,health:p.health}))};
fs.writeFileSync(new URL('../../output/friday-provider-'+site+'-live-2026-11-10.json',import.meta.url),JSON.stringify(evidence,null,2));console.log(JSON.stringify({failedRunId:failed.runId,successRunId:success.runId,toolResults:tools.length,reportCharacters:success.report.length}));
