// Read-only telemetry for explicitly requested local concurrency acceptance.
import fs from 'node:fs';import {homedir} from 'node:os';import {join} from 'node:path';import {setTimeout as delay} from 'node:timers/promises';
const seconds=Number(process.argv[2]||180);if(!Number.isInteger(seconds)||seconds<1||seconds>900)throw Error('Supply 1–900 seconds');
const root=join(homedir(),'.dsh/browser-connector'),connection=JSON.parse(fs.readFileSync(join(root,'connection.json'),'utf8'));
const records=[],started=Date.now(),file=new URL('../../../output/friday-parallel-status-live.json',import.meta.url);
const save=()=>fs.writeFileSync(file,JSON.stringify({startedAt:new Date(started).toISOString(),maxActive:Math.max(0,...records.map(r=>r.activeRequests||0)),maxQueued:Math.max(0,...records.map(r=>r.queuedRequests||0)),records},null,2));
while(Date.now()-started<seconds*1000){
 try{const response=await fetch(`http://127.0.0.1:${connection.port}/status`,{headers:{Authorization:`Bearer ${connection.token}`},signal:AbortSignal.timeout(3000)});if(!response.ok)throw Error('Status unavailable');const {activeRequests,queuedRequests,pending,maxConcurrentRequests,backendVersion,extensionVersion}=await response.json();records.push({at:new Date().toISOString(),activeRequests,queuedRequests,pending,maxConcurrentRequests,backendVersion,extensionVersion});save();}catch{records.push({at:new Date().toISOString(),offline:true});save();}
 await delay(500);
}
save();console.log(JSON.stringify({samples:records.length,maxActive:Math.max(...records.map(r=>r.activeRequests||0)),maxQueued:Math.max(...records.map(r=>r.queuedRequests||0))}));
