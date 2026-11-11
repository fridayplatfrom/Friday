// Read-only native acceptance audit. This script never submits or retries a task.
import fs from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {consumeSSE} from '../ag-ui-client.mjs';
const mode=process.argv[2];
if(!['checkpoint','final'].includes(mode))throw Error('Select checkpoint or final.');
const spec=JSON.parse(fs.readFileSync('tasks/file-recovery-current.json','utf8'));
const evidence=join(spec.directory,'recovery-audit.json');
const digest=value=>createHash('sha256').update(value).digest('hex');
const logs=join(homedir(),'.dsh/logs');
const latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];
if(!login)throw Error('Owner link unavailable.');
const admitted=await fetch(login,{redirect:'manual'}),cookie=admitted.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');
if(!cookie)throw Error('Owner authentication unavailable.');
const headers={Cookie:cookie,'X-Harness-Models':'1'},base='http://127.0.0.1:3030/browser-models';
async function state(route){const response=await fetch(base+route,{headers,signal:AbortSignal.timeout(15000)});assert.ok(response.ok);return response.json();}
const status=await state('/status');
assert.equal(status.pending,0,'Finish all native tasks before auditing.');
assert.equal(status.connected,true);assert.equal(status.backendVersion,'0.10.2');assert.equal(status.extensionVersion,'0.10.2');
const session=await state('/session/'+spec.threadId),pair=session.pairs?.[spec.site];
assert.ok(pair?.url&&Number.isInteger(pair.tabId));
const raw=fs.readFileSync(spec.stateFile),file=JSON.parse(raw.toString('utf8')),sha256=digest(raw).toUpperCase();
assert.equal(file.testId,spec.id);assert.equal(file.creationCount,1);assert.match(file.nonce,/^[a-f0-9-]{36}$/);
function operatorRun(log){
 const result=fs.readFileSync(log,'utf8').trim().split(/\r?\n/).map(line=>JSON.parse(line)).findLast(value=>value.runId);
 assert.equal(result.status,'finished');return result;
}
async function audit(run,commands,start,end){
 const response=await fetch(`${base}/ag-ui/runs/${run.runId}?threadId=${spec.threadId}`,{headers,signal:AbortSignal.timeout(15000)});
 const events=[],cursors=[];await consumeSSE(response,{onEvent:(event,cursor)=>{events.push(event);cursors.push(cursor);}});
 const calls=events.filter(e=>e.type==='TOOL_CALL_START'),results=events.filter(e=>e.type==='TOOL_CALL_RESULT');
 assert.equal(calls.length,commands.length);assert.equal(results.length,commands.length);
 for(let i=0;i<calls.length;i++){
  const call=calls[i],result=results[i];assert.equal(call.toolCallName,'pwsh');assert.equal(call.toolCallId,result.toolCallId);assert.ok(!result.metadata?.friday?.isError);
  const argument=JSON.parse(events.filter(e=>e.type==='TOOL_CALL_ARGS'&&e.toolCallId===call.toolCallId).map(e=>e.delta).join(''));
  assert.equal(argument.command,commands[i]);assert.ok(!argument.sandbox_permissions);
  if(i)assert.ok(events.indexOf(results[i-1])<events.indexOf(call),'Dependent tools must wait for real results.');
 }
 assert.equal(events.at(-1).type,'RUN_FINISHED');assert.equal(events.at(-1).outcome?.type,'success');
 const messages=events.findLast(e=>e.type==='MESSAGES_SNAPSHOT')?.messages||[],report=messages.filter(m=>m.role==='assistant').at(-1)?.content;
 assert.equal(report,run.report);assert.ok(report.trim().startsWith(start)&&report.trim().endsWith(end));
 assert.ok(report.includes(file.nonce)&&report.toUpperCase().includes(sha256),'Final report must include actual nonce and file hash.');
 const after=cursors[events.indexOf(results[0])];
 const resumed=await fetch(`${base}/ag-ui/runs/${run.runId}?threadId=${spec.threadId}&after=${after}`,{headers,signal:AbortSignal.timeout(15000)});
 const tail=[];await consumeSSE(resumed,{onEvent:event=>tail.push(event)});
 assert.deepEqual(tail,events.filter((_,i)=>cursors[i]>after),'Cursor reconnect must return exactly the remaining events.');
 assert.equal(digest(fs.readFileSync(spec.stateFile)).toUpperCase(),sha256,'Observing saved events cannot modify the file.');
 return {runId:run.runId,toolCalls:calls.map(c=>({id:c.toolCallId,name:c.toolCallName})),results:results.map(r=>r.content),report,historyDigest:digest(JSON.stringify(events)),cursorResume:{after,tailEvents:tail.length,exactMatch:true}};
}
const creation=await audit(operatorRun('file-recovery-create-live.log'),spec.commands,spec.start,spec.end);
assert.deepEqual(JSON.parse(creation.results[0].trim()),file);assert.ok(creation.results[1].includes(file.nonce)&&creation.results[1].includes('SHA256='+sha256));
if(mode==='checkpoint'){
 assert.ok(!fs.existsSync(evidence),'Never overwrite an existing checkpoint.');
 fs.writeFileSync(evidence,JSON.stringify({status:'awaiting-restart',testId:spec.id,threadId:spec.threadId,pair,file,sha256,creation,checkpointAt:new Date().toISOString()},null,2));
 console.log(JSON.stringify({status:'checkpoint-verified',tools:creation.toolCalls.length,testId:spec.id}));
}else{
 const before=JSON.parse(fs.readFileSync(evidence,'utf8'));
 assert.ok(['awaiting-restart','passed'].includes(before.status));assert.equal(before.testId,spec.id);assert.deepEqual(pair,before.pair);assert.deepEqual(file,before.file);assert.equal(sha256,before.sha256);assert.equal(creation.historyDigest,before.creation.historyDigest,'Completed native history must survive restart unchanged.');
 const continuation=await audit(operatorRun('file-recovery-continue-live.log'),[spec.commands[1]],'FRIDAY_FILE_RECONNECTED_START','FRIDAY_FILE_RECONNECTED_END');
 assert.ok(continuation.results[0].includes(file.nonce)&&continuation.results[0].includes('SHA256='+sha256));
 const report={...before,status:'passed',continuation,verifiedAt:new Date().toISOString(),finalPending:status.pending,scope:'Isolated file creation followed by dependent read, completed-task restart, then explicit read-only continuation. No mid-action crash or arbitrary exactly-once guarantee.'};
 fs.writeFileSync(evidence,JSON.stringify(report,null,2));
 console.log(JSON.stringify({status:report.status,tools:3,sameSavedChat:true,unchangedFile:true,unchangedCompletedHistory:true,finalPending:0,evidence}));
}
