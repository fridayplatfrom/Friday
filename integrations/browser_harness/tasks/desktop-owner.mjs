// Local owner-authenticated diagnostics. Never print the owner URL or cookies.
import fs from 'node:fs';import {join} from 'node:path';import {homedir} from 'node:os';
const directory=join(homedir(),'.dsh/logs');
const latest=fs.readdirSync(directory).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(directory,b)).mtimeMs-fs.statSync(join(directory,a)).mtimeMs)[0];
const login=latest&&fs.readFileSync(join(directory,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];
if(!login)throw Error('Native owner link unavailable');
const admission=await fetch(login,{redirect:'manual',signal:AbortSignal.timeout(10000)});
const cookie=admission.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');if(!cookie)throw Error('Native owner authentication failed');
export async function ownerResponse(path,body){const response=await fetch('http://127.0.0.1:3030/browser-models/'+path,{method:body===undefined?'GET':'POST',headers:{Cookie:cookie,'X-Harness-Models':'1','Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)}),signal:AbortSignal.timeout(20000)});if(!response.ok)throw Error('Native diagnostic rejected: '+response.status);return response;}
export async function owner(path,body){return (await ownerResponse(path,body)).json();}
