// Operator-only read-only probes through Friday's existing authenticated owner route.
// This does not log in, send a website prompt, reload tabs or change model selection.
import fs from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {setTimeout as delay} from 'node:timers/promises';
const logs=join(homedir(),'.dsh/logs');
const latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
const login=latest&&fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];
if(!login)throw new Error('Current native owner sign-in is unavailable.');
const admission=await fetch(login,{redirect:'manual',signal:AbortSignal.timeout(5000)});
const cookie=admission.headers.getSetCookie().map(value=>value.split(';')[0]).join('; ');
if(!cookie)throw new Error('Owner authentication failed.');
const base='http://127.0.0.1:3030/browser-models/';
async function request(route,body){const response=await fetch(base+route,{method:body?'POST':'GET',headers:{Cookie:cookie,'X-Harness-Models':'1','Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(5000)});if(!response.ok)throw new Error('Native diagnostic route rejected the request: '+response.status);return response.json();}
const startedAt=Date.now(),initial=await request('status');
if(!initial.connected)throw new Error('Friday extension is offline.');
if(initial.pending)throw new Error('Finish the active request before the provider audit.');
const sessions=JSON.parse(fs.readFileSync(join(homedir(),'.dsh/browser-connector/sessions/sessions.json'),'utf8'));
const nativeSessions=[];
for(const provider of initial.providers){const candidates=Object.values(sessions).filter(s=>s.pairs?.[provider.id]).sort((a,b)=>b.updatedAt-a.updatedAt),saved=candidates.find(s=>s.site===provider.id)||candidates[0];if(saved){const state=await request('session/'+encodeURIComponent(saved.sessionId));nativeSessions.push({site:provider.id,sessionId:saved.sessionId,native:state.nativeSession});}await request('health',{site:provider.id,...(saved?{sessionId:saved.sessionId}:{})});}
let status;
for(let i=0;i<40;i++){status=await request('status');if(status.providers.every(p=>p.health?.checkedAt>=startedAt))break;await delay(500);}
const report={date:new Date().toISOString(),backendVersion:status.backendVersion,extensionVersion:status.extensionVersion,connected:status.connected,nativeSessions,providers:status.providers.map(p=>({id:p.id,probeFresh:p.health?.checkedAt>=startedAt,health:p.health})),scope:'Visible-page listener/readiness probes only; not a successful model/tool round trip.'};
fs.writeFileSync(new URL('../../../output/friday-provider-health-audit.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
