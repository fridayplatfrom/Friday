// Verify the fresh native tool run after cancellation, without rerunning it.
import fs from 'node:fs';import {join} from 'node:path';import {homedir} from 'node:os';import assert from 'node:assert/strict';
import {consumeSSE} from '../ag-ui-client.mjs';
const before=JSON.parse(fs.readFileSync('../../output/friday-cancel-stream-audit.json','utf8'));assert.equal(before.status,'passed');assert.equal(before.repeatedCancelResult.alreadyFinished,true);
const run=fs.readFileSync('after-cancel-tool-live.log','utf8').trim().split(/\r?\n/).map(line=>JSON.parse(line)).findLast(r=>r.runId);assert.equal(run.status,'finished');
const logs=join(homedir(),'.dsh/logs'),latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];assert.ok(login);
const admitted=await fetch(login,{redirect:'manual'}),cookie=admitted.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');assert.ok(cookie);
const base='http://127.0.0.1:3030/browser-models',headers={Cookie:cookie,'X-Harness-Models':'1'};
const get=async path=>{const response=await fetch(base+path,{headers,signal:AbortSignal.timeout(15000)});assert.ok(response.ok);return response;};
const events=[];await consumeSSE(await get(`/ag-ui/runs/${run.runId}?threadId=${before.threadId}`),{onEvent:event=>events.push(event)});
const calls=events.filter(e=>e.type==='TOOL_CALL_START'),results=events.filter(e=>e.type==='TOOL_CALL_RESULT');assert.equal(calls.length,1);assert.equal(results.length,1);assert.equal(calls[0].toolCallName,'pwsh');assert.equal(calls[0].toolCallId,results[0].toolCallId);assert.ok(!results[0].metadata?.friday?.isError);
const args=JSON.parse(events.filter(e=>e.type==='TOOL_CALL_ARGS').map(e=>e.delta).join(''));assert.equal(args.command,"Write-Output 'FRIDAY_AFTER_CANCEL_READY'");assert.ok(!args.sandbox_permissions);assert.equal(results[0].content.trim(),'FRIDAY_AFTER_CANCEL_READY');
assert.equal(events.at(-1).outcome.type,'success');const report=events.findLast(e=>e.type==='MESSAGES_SNAPSHOT').messages.filter(m=>m.role==='assistant').at(-1).content;assert.equal(report,run.report);assert.ok(report.trim().startsWith('FRIDAY_AFTER_CANCEL_START')&&report.trim().endsWith('FRIDAY_AFTER_CANCEL_END'));
const cancelled=[];await consumeSSE(await get(`/ag-ui/runs/${before.runId}?threadId=${before.threadId}`),{onEvent:event=>cancelled.push(event)});assert.deepEqual(cancelled,before.events);
const session=await(await get('/session/'+before.threadId)).json(),status=await(await get('/status')).json();assert.equal(status.pending,0);assert.equal(session.nativeSession.status,'idle');assert.deepEqual(session.pairs['chatgpt-web'],before.pair);assert.deepEqual(session.files,before.files);
const evidence={status:'passed',cancelledRunId:before.runId,recoveryRunId:run.runId,threadId:before.threadId,toolCallId:calls[0].toolCallId,toolResult:results[0].content,report,sameChat:true,unchangedAttachments:true,unchangedCancelledTranscript:true,repeatedCancelNoop:true,pending:0,verifiedAt:new Date().toISOString()};
fs.writeFileSync('../../output/friday-after-cancel-audit.json',JSON.stringify(evidence,null,2));console.log(JSON.stringify({status:'passed',sameChat:true,toolCalls:1,unchangedAttachments:true,repeatedCancelNoop:true,pending:0}));
