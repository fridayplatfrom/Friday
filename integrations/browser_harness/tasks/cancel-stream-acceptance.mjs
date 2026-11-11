// Explicit synthetic live acceptance: stop only this newly admitted native run.
import fs from 'node:fs';import {join} from 'node:path';import {homedir} from 'node:os';import {randomUUID} from 'node:crypto';import assert from 'node:assert/strict';import {setTimeout as delay} from 'node:timers/promises';
import {HttpAgent} from '@ag-ui/client';
const threadId='session-b9227320-2827-4e26-9337-c3c3b6f6adc9',runId=randomUUID(),started=Date.now();
const logs=join(homedir(),'.dsh/logs'),latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];assert.ok(login);
const admission=await fetch(login,{redirect:'manual'}),cookie=admission.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');assert.ok(cookie);
const headers={Cookie:cookie,'X-Harness-Models':'1','Content-Type':'application/json'},base='http://127.0.0.1:3030/browser-models';
async function request(path,input){const response=await fetch(base+path,{headers,...(input?{method:'POST',body:JSON.stringify(input)}:{}),signal:AbortSignal.timeout(15000)});assert.ok(response.ok);return response.json();}
const initial=await request('/status');assert.equal(initial.pending,0);assert.equal(initial.connected,true);assert.equal(initial.extensionVersion,'0.10.2');
const before=await request('/session/'+threadId);assert.equal(before.nativeSession.status,'idle');assert.equal(before.nativeSession.model,'chatgpt-web');
const record={status:'running',threadId,runId,startedAt:new Date(started).toISOString(),events:[],pair:before.pairs['chatgpt-web'],files:before.files};
const file='../../output/friday-cancel-stream-audit.json',save=()=>fs.writeFileSync(file,JSON.stringify(record,null,2));save();
let firstText;const streaming=new Promise(resolve=>{firstText=resolve;});
const agent=new HttpAgent({url:base+'/ag-ui',threadId,headers,initialMessages:[{id:randomUUID(),role:'user',content:`NEW synthetic streaming-cancellation test ${runId}. Only this task is active. Start your visible answer with FRIDAY_CANCEL_STREAM_BEGIN, then write 300 numbered short fictional test observations, one per line, to produce a long stream. Do not call any Harness tools, create files or images, browse, change permissions, or resume prior tasks. This response will deliberately be stopped by the operator.`}]});
const running=agent.runAgent({runId},{onEvent:({event})=>{record.events.push(event);save();if(event.type==='TEXT_MESSAGE_CONTENT'&&event.delta.trim())firstText(true);if(['RUN_ERROR','RUN_FINISHED'].includes(event.type))firstText(false);}});
// Attach immediately so a rejected observer promise cannot be unhandled.
let runError;const settled=running.catch(error=>{runError=error;firstText(false);});
try{
 const ready=await Promise.race([streaming,delay(90000,undefined,{ref:false}).then(()=>false)]);
 if(!ready)throw Error('No cancellable live text stream observed; this attempt is not a pass.');
 record.cancelRequestedAt=new Date().toISOString();record.cancelResult=await request('/ag-ui/cancel',{threadId,runId});save();assert.equal(record.cancelResult.alreadyFinished,false);
 await Promise.race([settled,delay(20000,undefined,{ref:false}).then(()=>{throw Error('Native cancellation did not settle in time.');})]);if(runError)throw runError;
 for(let i=0;i<30;i++){const status=await request('/status');if(!status.pending)break;await delay(300);}
 const final=await request('/session/'+threadId),status=await request('/status');assert.equal(status.pending,0);assert.equal(final.nativeSession.status,'idle');
 assert.deepEqual(final.pairs['chatgpt-web'],record.pair);assert.deepEqual(final.files,record.files);
 assert.equal(record.events.filter(e=>e.type==='TOOL_CALL_START').length,0);
 const terminal=record.events.at(-1);assert.equal(terminal.type,'RUN_FINISHED');assert.equal(terminal.outcome.type,'cancelled');
 const journal=await request('/journal/'+threadId);const requests=journal.filter(e=>e.type==='request'&&e.at>=started&&e.data.purpose==='task');assert.equal(requests.length,1,'Cancellation must not resubmit the website prompt.');
 const jobId=requests[0].data.id;const submitted=journal.filter(e=>e.type==='submitted'&&e.data.id===jobId);assert.equal(submitted.length,1);
 record.status='passed';record.finishedAt=new Date().toISOString();record.websiteJobId=jobId;record.websiteRequests=1;record.websiteSubmissions=1;record.finalPending=0;save();
 console.log(JSON.stringify({status:record.status,runId,streamedCharacters:record.events.filter(e=>e.type==='TEXT_MESSAGE_CONTENT').reduce((sum,e)=>sum+e.delta.length,0),nativeOutcome:terminal.outcome.type,websiteSubmissions:1,unchangedAttachments:true,pending:0}));
}catch(error){
 const current=await request('/session/'+threadId).catch(()=>null);if(current?.aguiRuns?.find(r=>r.runId===runId)?.status==='running')await request('/ag-ui/cancel',{threadId,runId}).catch(()=>{});
 record.status='failed';record.error=error.message;save();throw error;
}
