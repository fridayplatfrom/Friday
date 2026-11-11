// Operator acceptance only: existing native sessions, native tools and permissions.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {homedir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const spec=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
if(!Array.isArray(spec.runs)||spec.runs.length<2||spec.runs.length>3||new Set(spec.runs.map(r=>r.threadId)).size!==spec.runs.length)throw Error('Supply two or three distinct native test sessions.');
const connection=JSON.parse(fs.readFileSync(join(homedir(),'.dsh/browser-connector/connection.json'),'utf8'));
const records=[],startedAt=new Date().toISOString();let finished=false;
const sample=async()=>{const response=await fetch(`http://127.0.0.1:${connection.port}/status`,{headers:{Authorization:`Bearer ${connection.token}`},signal:AbortSignal.timeout(3000)});if(!response.ok)throw Error('Status unavailable');const {activeRequests,queuedRequests,pending,maxConcurrentRequests,backendVersion,extensionVersion,connected}=await response.json();return {at:new Date().toISOString(),activeRequests,queuedRequests,pending,maxConcurrentRequests,backendVersion,extensionVersion,connected};};
const initial=await sample();
if(!initial.connected||initial.pending||initial.backendVersion!=='0.10.2'||initial.extensionVersion!=='0.10.2')throw Error('Idle matching v0.10.2 backend and extension required. Nothing submitted.');
const trace=new URL('../../../output/friday-parallel-status-cohort-live.json',import.meta.url);
const save=()=>fs.writeFileSync(trace,JSON.stringify({startedAt,maxActive:Math.max(0,...records.map(r=>r.activeRequests||0)),maxQueued:Math.max(0,...records.map(r=>r.queuedRequests||0)),records},null,2));
const watcher=(async()=>{while(!finished){try{records.push(await sample());}catch{records.push({at:new Date().toISOString(),offline:true});}save();await delay(200);}})();
const runner=fileURLToPath(new URL('../run-native-task.mjs',import.meta.url));
const results=await Promise.allSettled(spec.runs.map(run=>new Promise((resolve,reject)=>{
 const child=spawn(process.execPath,[runner,run.threadId,run.brief,run.site,'--require-version=0.10.2'],{windowsHide:true,stdio:['ignore','pipe','pipe']});
 let stdout='',stderr='';child.stdout.on('data',data=>{stdout+=data;});child.stderr.on('data',data=>{stderr+=data;});
 child.on('error',reject);child.on('close',code=>{const result={site:run.site,threadId:run.threadId,code,stdout,stderr};console.log(JSON.stringify(result));resolve(result);});
})));
finished=true;await watcher;save();
console.log(JSON.stringify({runs:results.length,maxActive:Math.max(...records.map(r=>r.activeRequests||0)),maxQueued:Math.max(...records.map(r=>r.queuedRequests||0))}));
if(results.some(r=>r.status==='rejected'||r.value.code!==0))process.exitCode=1;
