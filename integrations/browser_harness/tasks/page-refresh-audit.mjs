// Verify a live reload after text streaming began. This never submits a prompt.
import fs from 'node:fs';import {join} from 'node:path';import {homedir} from 'node:os';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
import {consumeSSE} from '../ag-ui-client.mjs';
const proof=JSON.parse(fs.readFileSync('../../output/friday-page-refresh-103-before.json','utf8'));
const refresh=JSON.parse(fs.readFileSync('../../output/friday-page-refresh-103-executed.json','utf8'));
assert.ok(proof.firstTextAt&&proof.streamedCharacters>0&&!proof.terminal);
assert.ok(Date.parse(refresh.startedAt)>Date.parse(proof.firstTextAt));
const logs=join(homedir(),'.dsh/logs'),latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];assert.ok(login);
const admission=await fetch(login,{redirect:'manual'}),cookie=admission.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');assert.ok(cookie);
const base='http://127.0.0.1:3030/browser-models',headers={Cookie:cookie,'X-Harness-Models':'1'};
const get=async path=>{const r=await fetch(base+path,{headers,signal:AbortSignal.timeout(20000)});assert.ok(r.ok);return r;};
const state=await(await get('/session/'+proof.threadId)).json(),status=await(await get('/status')).json();
const run=state.aguiRuns.find(r=>r.runId===proof.runId);assert.equal(run?.status,'finished','The live task must finish before this audit.');
const events=[],cursors=[];await consumeSSE(await get(`/ag-ui/runs/${proof.runId}?threadId=${proof.threadId}`),{onEvent:(event,cursor)=>{events.push(event);cursors.push(cursor);}});
assert.equal(events.filter(e=>e.type==='TOOL_CALL_START').length,0);assert.equal(events.at(-1).outcome?.type,'success');
const reconnections=events.filter(e=>e.type==='STATE_SNAPSHOT'&&e.snapshot?.friday?.phase==='reconnecting'&&e.timestamp>=Date.parse(refresh.startedAt));
assert.ok(reconnections.length,'A real listener reattachment after live text must be recorded.');
const report=events.findLast(e=>e.type==='MESSAGES_SNAPSHOT').messages.filter(m=>m.role==='assistant').at(-1).content;
assert.ok(report.trim().startsWith('FRIDAY_REFRESH103_START')&&report.trim().endsWith('FRIDAY_REFRESH103_END'),'Require the full bounded reply, not an interrupted fragment.');
assert.ok(proof.acceptanceId&&report.includes(proof.acceptanceId),'The reply must belong to this unique acceptance task.');
const journal=await(await get('/journal/'+proof.threadId)).json(),allRequests=journal.filter(e=>e.type==='request'&&e.at>=run.startedAt&&e.at<=run.endedAt&&e.data.purpose==='task');
// Harness may compact history before answering. Those separate model requests
// are not resubmissions of the uniquely identified current human task.
const requests=allRequests.filter(e=>e.data.prompt.includes(proof.acceptanceId));assert.equal(requests.length,1);
const jobId=requests[0].data.id,submitted=journal.filter(e=>e.type==='submitted'&&e.data.id===jobId),completed=journal.filter(e=>e.type==='complete'&&e.data.id===jobId);
assert.equal(submitted.length,1);assert.equal(completed.length,1);assert.equal(completed[0].data.text,report);
assert.ok(submitted[0].at<Date.parse(proof.at)&&completed[0].at>reconnections[0].timestamp);
assert.equal(status.pending,0);assert.equal(state.nativeSession.status,'idle');assert.equal(status.backendVersion,'0.10.3');assert.equal(status.extensionVersion,'0.10.3');
const after=cursors[Math.floor(cursors.length/2)],tail=[];await consumeSSE(await get(`/ag-ui/runs/${proof.runId}?threadId=${proof.threadId}&after=${after}`),{onEvent:event=>tail.push(event)});assert.deepEqual(tail,events.filter((_,i)=>cursors[i]>after));
const result={status:'passed',runId:proof.runId,threadId:proof.threadId,acceptanceId:proof.acceptanceId,firstTextAt:proof.firstTextAt,refresh,reconnectedAt:new Date(reconnections[0].timestamp).toISOString(),websiteRequests:1,websiteSubmissions:1,auxiliaryRequests:allRequests.length-1,websiteJobId:jobId,report,reportCharacters:report.length,pair:state.pairs['chatgpt-web'],historyDigest:createHash('sha256').update(JSON.stringify(events)).digest('hex'),cursorRecovery:true,pending:0,verifiedAt:new Date().toISOString(),scope:'Existing ChatGPT text task, live tab reload, verified saved turn, no tools or file transfers.'};
fs.writeFileSync('../../output/friday-page-refresh-103-audit.json',JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,runId:proof.runId,websiteSubmissions:1,reportCharacters:report.length,cursorRecovery:true,pending:0}));
