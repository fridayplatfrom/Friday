// Operator-only: use Friday's existing owner-authenticated Show paired chat action.
import fs from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {SITES} from '../protocol.mjs';
const [site,sessionId]=process.argv.slice(2);
if(!Object.hasOwn(SITES,site)||!/^session-[a-f0-9-]{36}$/i.test(sessionId||''))throw Error('Supply a provider ID and existing native session ID.');
const directory=join(homedir(),'.dsh/logs'),latest=fs.readdirSync(directory).filter(name=>/^browser-.*\.out\.log$/.test(name)).sort((a,b)=>fs.statSync(join(directory,b)).mtimeMs-fs.statSync(join(directory,a)).mtimeMs)[0];
const login=latest&&fs.readFileSync(join(directory,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];
if(!login)throw Error('Native owner link is not ready.');
const admission=await fetch(login,{redirect:'manual',signal:AbortSignal.timeout(5000)}),cookie=admission.headers.getSetCookie().map(value=>value.split(';')[0]).join('; ');
if(!cookie)throw Error('Native owner authentication failed.');
const response=await fetch('http://127.0.0.1:3030/browser-models/focus',{method:'POST',headers:{Cookie:cookie,'X-Harness-Models':'1','Content-Type':'application/json'},body:JSON.stringify({site,sessionId}),signal:AbortSignal.timeout(5000)});
if(!response.ok)throw Error('Saved chat focus action rejected: '+response.status);
console.log(JSON.stringify({queued:true,site,sessionId}));
