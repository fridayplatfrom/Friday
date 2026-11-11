// Read-only mixed native image/document acceptance. Never submits a task.
import fs from 'node:fs';import {join} from 'node:path';import {homedir} from 'node:os';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {consumeSSE} from '../ag-ui-client.mjs';
const spec=JSON.parse(fs.readFileSync('tasks/mixed-transfer-current.json','utf8'));
const output='../../output/friday-mixed-transfer-audit.json',recheck=process.argv.includes('--recheck');
const before=recheck?JSON.parse(fs.readFileSync(output,'utf8')):null;
const logs=join(homedir(),'.dsh/logs'),latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];assert.ok(login);
const admission=await fetch(login,{redirect:'manual'}),cookie=admission.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');assert.ok(cookie);
const headers={Cookie:cookie,'X-Harness-Models':'1'},base='http://127.0.0.1:3030/browser-models';
const get=async path=>{const r=await fetch(base+path,{headers,signal:AbortSignal.timeout(15000)});assert.ok(r.ok);return r;};
const session=await(await get('/session/'+spec.threadId)).json();assert.equal(session.nativeSession.status,'idle');
const run=before?session.aguiRuns.find(r=>r.runId===before.runId):session.aguiRuns.findLast(r=>r.startedAt>=Date.parse(spec.startedAt));assert.equal(run?.status,'finished');
const events=[];await consumeSSE(await get(`/ag-ui/runs/${run.runId}?threadId=${spec.threadId}`),{onEvent:event=>events.push(event)});
assert.equal(events.filter(e=>e.type==='TOOL_CALL_START').length,0);assert.equal(events.at(-1).outcome?.type,'success');
const report=events.findLast(e=>e.type==='MESSAGES_SNAPSHOT').messages.filter(m=>m.role==='assistant').at(-1).content;
assert.ok(report.trim().startsWith('FRIDAY_MIXED_START')&&report.trim().endsWith('FRIDAY_MIXED_END'));
assert.ok(report.includes(spec.id)&&report.includes(spec.nonce));assert.match(report,/17\s*[×x*]\s*3\s*=\s*51/);
assert.match(report,/Left:[^\n]*red circle/i);assert.match(report,/Right:[^\n]*blue square/i);
const uploads=[];
for(const expected of spec.files){const records=session.files.filter(f=>f.direction==='to-website'&&f.sha256===expected.sha256);assert.equal(records.length,1);const file=records[0];assert.equal(file.status,'delivered');const bytes=Buffer.from(await(await get('/files/'+file.id)).arrayBuffer());assert.deepEqual(bytes,fs.readFileSync(expected.path));uploads.push(file);}
const current={status:'passed',testId:spec.id,threadId:spec.threadId,runId:run.runId,report,uploads,pair:session.pairs[spec.site],historyDigest:createHash('sha256').update(JSON.stringify(events)).digest('hex'),verifiedAt:new Date().toISOString()};
if(before){for(const key of ['runId','report','uploads','pair','historyDigest'])assert.deepEqual(current[key],before[key]);current.recheckedAfterCancellation=true;}
fs.writeFileSync(output,JSON.stringify(current,null,2));console.log(JSON.stringify({status:'passed',runId:run.runId,uploads:uploads.length,exactBytes:true,visualAndDocumentAnswer:true,rechecked:recheck}));
