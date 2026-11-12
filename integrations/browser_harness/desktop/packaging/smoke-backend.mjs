// Real offline-capable boot of the staged runtime under a new, isolated home.
import {mkdtempSync,writeFileSync,readFileSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,join,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createServer} from 'node:net';
import {spawn} from 'node:child_process';
const desktop=resolve(dirname(fileURLToPath(import.meta.url)),'..'),stage=resolve(process.env.FRIDAY_BUILD_STAGE||join(desktop,'.packaging'));
const root=mkdtempSync(join(process.env.FRIDAY_SMOKE_PARENT||stage,'backend-smoke-')),home=join(root,'home');mkdirSync(home);
const resources=resolve(process.env.FRIDAY_SMOKE_RESOURCES||join(stage,'resources')),executable=resolve(process.env.FRIDAY_SMOKE_EXECUTABLE||join(resources,'harness','runtime','primary-runtime','dependencies','node','bin','node.exe')),provider=join(resources,'provider');
const {prepareInstalledProfile}=await import(pathToFileURL(join(provider,'desktop','backend-runtime.mjs')).href);
const prepared=prepareInstalledProfile({home,resources,executable,provider});
async function freePort(){const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;await new Promise(r=>server.close(r));return port;}
const port=await freePort(),bridgePort=await freePort(),connectionFile=join(prepared.connector,'connection.json');prepared.connection.port=bridgePort;writeFileSync(connectionFile,JSON.stringify(prepared.connection));
const overlay=JSON.parse(readFileSync(prepared.overlayFile,'utf8')),providerConfig=overlay.flatMap(p=>p.insert||[p]).find(p=>p.id==='harness-browser-provider').config;providerConfig.connectionFile=connectionFile;providerConfig.demoForm=false;writeFileSync(prepared.overlayFile,JSON.stringify(overlay));
const support=join(resources,'harness','runtime'),env={...process.env,USERPROFILE:home,DSH_HOME:prepared.dsh,ELECTRON_RUN_AS_NODE:'1',FRIDAY_BUNDLED_RESOURCES:resources,DSH_DESKTOP_NODE_EXECUTABLE:executable,
 PATH:[join(support,'bin'),join(support,'primary-runtime','dependencies','node','bin'),join(support,'primary-runtime','dependencies','python'),join(support,'git','cmd'),join(process.env.SystemRoot,'System32')].join(';')};
const child=spawn(executable,['--expose-internals',join(provider,'desktop','backend-entry.mjs'),'--profile','web','--patch',prepared.overlayFile,'--host','127.0.0.1','--port',String(port),'--no-open'],{env,cwd:home,windowsHide:true,stdio:['ignore','pipe','pipe','ipc']});
let stdout='',stderr='';child.stdout.on('data',chunk=>stdout+=chunk);child.stderr.on('data',chunk=>stderr+=chunk);let startupError;child.on('error',error=>startupError=error);
const report={scope:'Staged standalone backend with empty user home and PATH restricted to bundled tools plus Windows System32',checks:{},passed:false};
try{
 const until=Date.now()+90000;let login;
 while(Date.now()<until){if(startupError)throw startupError;if(child.exitCode!==null)throw Error('Backend exited: '+child.exitCode);login=stdout.match(new RegExp('http://127\\.0\\.0\\.1:'+port+'/\\?token=[^\\s]+'))?.[0];if(login)break;await new Promise(r=>setTimeout(r,250));}
 if(!login)throw Error('Backend did not print its local authentication link');
 const initial=await fetch(login,{redirect:'manual'}),cookie=initial.headers.get('set-cookie')?.split(';')[0];
 const response=initial.status>=300&&initial.status<400?await fetch(new URL(initial.headers.get('location'),login),{headers:cookie?{Cookie:cookie}:{}}):initial;
 const html=await response.text();writeFileSync(join(root,'owner-page.html'),html);if(!response.ok||!html.includes('<html'))throw Error('Bundled interface did not serve HTML (HTTP '+response.status+')');report.checks.ownerPage=true;
 const headers={Authorization:'Bearer '+prepared.connection.token},status=await fetch(`http://127.0.0.1:${bridgePort}/status`,{headers});if(!status.ok)throw Error('Bundled bridge did not start');report.checks.bridge=true;
 const scripts=[...html.matchAll(/<script[^>]+src=["']([^"']+)["']/g)].map(m=>new URL(m[1].replaceAll('&amp;','&'),login)).filter(url=>url.origin===new URL(login).origin);if(!scripts.length)throw Error('Native client entry asset was not found');
 for(const script of scripts){const asset=await fetch(script,{headers:cookie?{Cookie:cookie}:{}});if(!asset.ok)throw Error('Native client asset failed to load: '+script.pathname+' (HTTP '+asset.status+'): '+(await asset.text()).slice(0,350));}report.checks.clientAssets=true;
}catch(error){report.error=error.stack;}
finally{
 if(child.exitCode===null&&child.connected)child.send({type:'friday-stop'});
 const until=Date.now()+15000;while(child.exitCode===null&&Date.now()<until)await new Promise(r=>setTimeout(r,100));report.exitCode=child.exitCode;report.checks.gracefulShutdown=[0,130].includes(child.exitCode);
 if(child.exitCode===null){child.kill();report.error||='Private backend did not stop gracefully';}
 report.passed=!report.error&&report.checks.gracefulShutdown;
 // Logs can contain the private local sign-in link; keep them out of reports.
 writeFileSync(join(root,'backend-private.log'),stdout+'\n'+stderr,{mode:0o600});writeFileSync(join(root,'report.json'),JSON.stringify(report,null,2));
 console.log('Report: '+join(root,'report.json'));console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;
}
