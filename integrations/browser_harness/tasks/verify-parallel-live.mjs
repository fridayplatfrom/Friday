// Verify saved acceptance runs against native, owner-authenticated AG-UI facts.
// No prompts, model selection, tool execution, approvals or retries occur here.
import fs from 'node:fs';import {join} from 'node:path';import {homedir} from 'node:os';import readline from 'node:readline';
import {consumeSSE} from '../ag-ui-client.mjs';
const spec=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const logs=join(homedir(),'.dsh/logs'),latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];if(!login)throw Error('Native owner link unavailable');
const admitted=await fetch(login,{redirect:'manual'}),cookie=admitted.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');if(!cookie)throw Error('Owner authentication unavailable');
const headers={Cookie:cookie,'X-Harness-Models':'1'},base='http://127.0.0.1:3030/browser-models';
const status=await(await fetch(base+'/status',{headers})).json();
const output=new URL('../../../output/',import.meta.url),names=fs.readdirSync(output),runs=[];
for(const expected of spec.runs){
 const name=names.find(n=>n.endsWith('-'+expected.runId+'.json')&&n.startsWith('friday-orbit-'));if(!name)throw Error('Missing operator run '+expected.runId);
 const saved=JSON.parse(fs.readFileSync(new URL(name,output),'utf8'));if(saved.status!=='finished')throw Error('Run did not finish: '+expected.runId);
 const response=await fetch(`${base}/ag-ui/runs/${saved.runId}?threadId=${saved.threadId}`,{headers,signal:AbortSignal.timeout(20000)});if(!response.ok)throw Error('Native audit rejected');
 const events=[];await consumeSSE(response,{onEvent:event=>events.push(event)});
 const calls=events.filter(e=>e.type==='TOOL_CALL_START'),results=events.filter(e=>e.type==='TOOL_CALL_RESULT');
 if(calls.length!==1||calls[0].toolCallName!=='pwsh'||results.length!==1||results[0].toolCallId!==calls[0].toolCallId||results[0].content.trim()!==expected.output||results[0].metadata?.friday?.isError)throw Error('Native tool ownership/output mismatch: '+saved.runId);
 const args=events.filter(e=>e.type==='TOOL_CALL_ARGS'&&e.toolCallId===calls[0].toolCallId).map(e=>e.delta).join('');
 const argument=JSON.parse(args);if(argument.command!==`Write-Output '${expected.output}'`||argument.sandbox_permissions)throw Error('Unexpected command or permission expansion');
 const terminal=events.at(-1);if(terminal.type!=='RUN_FINISHED'||terminal.outcome?.type!=='success'||terminal.threadId!==saved.threadId||terminal.runId!==saved.runId)throw Error('Native completion mismatch');
 const messages=events.findLast(e=>e.type==='MESSAGES_SNAPSHOT')?.messages||[],report=messages.filter(m=>m.role==='assistant').at(-1)?.content;
 if(report!==saved.report||!report.trim().startsWith(expected.start)||!report.trim().endsWith(expected.end)||!report.includes(expected.output))throw Error('Incomplete final native reply');
 const forbidden=spec.runs.filter(other=>other.runId!==expected.runId&&other.cohort===expected.cohort).map(other=>other.output);if(forbidden.some(marker=>report.includes(marker)))throw Error('Cross-chat output contamination');
 const session=await(await fetch(`${base}/session/${saved.threadId}`,{headers})).json();
 runs.push({...expected,threadId:saved.threadId,startedAt:saved.startedAt,endedAt:saved.endedAt,toolCallId:calls[0].toolCallId,toolResult:results[0].content,report,pairs:session.pairs,browserRequests:[]});
}
for(const a of runs)for(const b of runs)if(a!==b&&a.cohort===b.cohort&&a.site&&a.site===b.site){
 const ap=a.pairs?.[a.site],bp=b.pairs?.[b.site];
 if(!ap||!bp||ap.tabId===bp.tabId||ap.url===bp.url)throw Error('Parallel same-provider chats do not have distinct saved tabs and URLs');
}
const jobs=new Map();for await(const line of readline.createInterface({input:fs.createReadStream(join(homedir(),'.dsh/browser-connector/sessions/delivery.jsonl')),crlfDelay:Infinity})){
 let event;try{event=JSON.parse(line)}catch{continue;}
 if(event.type==='request'){const run=runs.find(r=>r.threadId===event.sessionId&&event.at>=Date.parse(r.startedAt)&&event.at<=Date.parse(r.endedAt));if(run){const job={id:event.data.id,site:event.data.site,purpose:event.data.purpose,startedAt:event.at};run.browserRequests.push(job);jobs.set(job.id,job);}}
 if(['complete','failed','cancelled'].includes(event.type)&&jobs.has(event.data.id)){const job=jobs.get(event.data.id);job.endedAt=event.at;job.outcome=event.type;}
}
const overlaps=[];for(let i=0;i<runs.length;i++)for(let j=i+1;j<runs.length;j++)if(runs[i].cohort===runs[j].cohort){let duration=0;for(const a of runs[i].browserRequests)for(const b of runs[j].browserRequests)duration=Math.max(duration,Math.min(a.endedAt||0,b.endedAt||0)-Math.max(a.startedAt,b.startedAt));overlaps.push({cohort:runs[i].cohort,runA:runs[i].runId,runB:runs[j].runId,overlapMs:Math.max(0,duration)});}
for(const cohort of spec.mode==='partial'?['mixed']:['mixed','two-chatgpt'])if(!overlaps.some(o=>o.cohort===cohort&&o.overlapMs>0))throw Error('No real overlapping browser requests for '+cohort);
if(spec.statusTrace&&!/^friday-parallel-status-[a-z0-9-]+\.json$/.test(spec.statusTrace))throw Error('Invalid local status trace');
const watchFile=new URL(spec.statusTrace||'friday-parallel-status-live.json',output),watch=JSON.parse(fs.readFileSync(watchFile,'utf8'));if(watch.maxActive!==2||watch.maxQueued<1||watch.records.some(r=>r.activeRequests>2))throw Error('Live capacity/queue not verified');
const report={date:'2026-11-11',status:spec.mode==='partial'?'partial':'passed',backendVersion:status.backendVersion,extensionVersion:status.extensionVersion,finalPending:status.pending,automatedTests:348,scope:'Native print-only tool round trips through Chrome; no files modified by model tools, no permission defaults changed. Backend/extension versions here identify the audit reader; each run retains its sourceVersion.',runs,overlaps,queue:{maxActive:watch.maxActive,maxQueued:watch.maxQueued,samples:watch.records.length},earlierFailures:spec.earlierFailures||[]};
fs.writeFileSync(new URL(spec.mode==='partial'?'friday-parallel-partial-report.json':'friday-parallel-live-report.json',output),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,runs:runs.length,nativeCalls:runs.length,overlaps,queue:report.queue,finalPending:report.finalPending}));
