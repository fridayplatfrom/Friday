// Explicit local acceptance runner. Uses only the current dsh web login URL;
// keeps its token/cookie in memory and never writes or prints them.
import fs from 'node:fs';
import {homedir} from 'node:os';
import {join} from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import {HttpAgent} from '@ag-ui/client';
import {EventSchema} from '@ag-ui/core/schemas';

const sessionId=process.argv[2];if(!sessionId)throw new Error('Supply the existing Friday session id.');
const logs=join(homedir(),'.dsh','logs');
const newest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,newest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];
if(!login)throw new Error('Current local web login URL is unavailable.');
const admitted=await fetch(login,{redirect:'manual'});
const cookie=admitted.headers.getSetCookie().map(value=>value.split(';')[0]).join('; ');
if(!cookie)throw new Error('Local owner authentication did not return a cookie.');
const headers={Cookie:cookie,'X-Harness-Models':'1'};
const root='http://127.0.0.1:3030';
const message={id:randomUUID(),role:'user',content:'Friday AG-UI live acceptance. Use the native pwsh tool exactly once to print FRIDAY_AGUI_TOOL_OK_42. Do not change files, install anything, or run other tools. After receiving the real tool result, give an ordinary English report beginning FRIDAY_AGUI_REPORT_START and ending FRIDAY_AGUI_REPORT_END. Include the actual output and explain that the command ran once. Do not include a tool request in the final report.'};
const runId=randomUUID(),client=new HttpAgent({url:root+'/browser-models/ag-ui',threadId:sessionId,initialMessages:[message],headers});
const events=[];
await client.runAgent({runId},{onEvent:({event})=>{EventSchema.parse(event);events.push(event);if(['TOOL_CALL_START','TOOL_CALL_RESULT','RUN_FINISHED','RUN_ERROR'].includes(event.type))console.log(event.type);}});
const report=client.messages.filter(m=>m.role==='assistant').at(-1)?.content||'';
const results=events.filter(e=>e.type==='TOOL_CALL_RESULT');
const last=events.at(-1);
if(last?.type!=='RUN_FINISHED'||last.outcome?.type!=='success'||!report.includes('FRIDAY_AGUI_REPORT_START')||!report.includes('FRIDAY_AGUI_REPORT_END')||results.length!==1||!results[0].content.includes('FRIDAY_AGUI_TOOL_OK_42'))throw new Error('AG-UI live acceptance did not meet its success criteria. Inspect Harness.');
const screenshots=client.state.friday?.screenshots||[];
if(screenshots.length){const res=await fetch(root+screenshots.at(-1).url,{headers});if(!res.ok||res.headers.get('content-type')!=='image/png')throw new Error('Saved preview unavailable through owner-authenticated route.');}
const replay=new HttpAgent({url:root+'/browser-models/ag-ui',threadId:sessionId,initialMessages:[message],headers});
await replay.runAgent({runId});if(replay.messages.at(-1)?.content!==report)throw new Error('Replayed report differs.');
const evidence={checkedAt:new Date().toISOString(),backend:'0.7.0',threadId:sessionId,runId,eventCount:events.length,eventTypes:[...new Set(events.map(e=>e.type))],toolResults:results.length,reportCharacters:report.length,reportSha256:createHash('sha256').update(report).digest('hex'),replayMatches:true,retainedScreenshotPreviews:screenshots.length};
fs.writeFileSync(new URL('../../output/friday-agui-live-2026-11-10.json',import.meta.url),JSON.stringify(evidence,null,2));
fs.writeFileSync(new URL('../../output/friday-agui-live-events-2026-11-10.json',import.meta.url),JSON.stringify(events,null,2));
console.log(JSON.stringify(evidence));
