import {existsSync,mkdirSync,readFileSync,writeFileSync,renameSync,openSync,closeSync,symlinkSync,readdirSync,realpathSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {homedir} from 'node:os';
import {randomBytes} from 'node:crypto';
import {spawn} from 'node:child_process';
import {createConnection} from 'node:net';

const atomic=(file,value)=>{mkdirSync(dirname(file),{recursive:true});writeFileSync(file+'.tmp',value,{mode:0o600});renameSync(file+'.tmp',file);};
function initializeProfile(profile,{provider,resources}){
 const marker=join(profile,'.friday-bootstrap.json');
 if(existsSync(profile)&&readdirSync(profile).length){
  if(!existsSync(marker)||JSON.parse(readFileSync(marker,'utf8')).complete)throw Error('Existing incomplete Harness profile needs review; no profile data was replaced.');
 }
 mkdirSync(profile,{recursive:true});atomic(marker,JSON.stringify({version:1,complete:false}));
 const bundles=['@deepseek-ai/dsh-base','@deepseek-ai/dsh-web-app'],composer=join(provider,'plugins','social-post-composer');
 if(existsSync(join(composer,'package.json'))){
  const local=join(profile,'node_modules','@local'),target=join(local,'social-post-composer');mkdirSync(local,{recursive:true});
  if(existsSync(target)){if(realpathSync(target)!==realpathSync(composer))throw Error('Existing local plugin link needs review.');}
  else symlinkSync(composer,target,process.platform==='win32'?'junction':'dir');
  bundles.push('@local/social-post-composer');
 }
 atomic(join(profile,'cordis.yml'),'[]\n');atomic(join(profile,'cordis.patch.yml'),readFileSync(join(resources,'harness','friday-default-patch.yml'),'utf8'));
 // Commit package.json last: a crash before this point can resume only an
 // explicitly marked, incomplete installation, never an existing user profile.
 atomic(join(profile,'package.json'),JSON.stringify({name:'dsh-profile-web',private:true,dsh:{profile:{bundles}}},null,2));
 atomic(marker,JSON.stringify({version:1,complete:true}));
}
export function prepareInstalledProfile({home=homedir(),provider,executable,resources}){
 const dsh=join(home,'.dsh'),connector=join(dsh,'browser-connector'),profile=join(dsh,'profiles','web');
 mkdirSync(connector,{recursive:true});const connectionFile=join(connector,'connection.json');
 if(!existsSync(connectionFile))atomic(connectionFile,JSON.stringify({port:8766,token:randomBytes(32).toString('base64')}));
 const connection=JSON.parse(readFileSync(connectionFile,'utf8'));
 if(connection.port!==8766||typeof connection.token!=='string'||connection.token.length<20)throw Error('Existing Friday connection needs review; it was not replaced.');
 const fresh=!existsSync(join(profile,'package.json'));
 if(fresh)initializeProfile(profile,{provider,resources});
 const patchFile=join(profile,'cordis.patch.yml'),prior=existsSync(patchFile)?readFileSync(patchFile,'utf8'):'';
 const nodes=[{id:'harness-browser-provider',name:join(provider,'index.mjs'),config:{browserMode:'extension',workspaceBrowser:true,demoForm:true}},
  {id:'harness-playwright',name:'@deepseek-ai/dsh-mcp-client',config:{serverName:'browser',transport:'stdio',command:executable,args:['--expose-internals',join(provider,'workspace-browser-mcp.mjs'),'--executable-path',executable,'--image-responses','allow','--allowed-origins','http://127.0.0.1:8767;http://127.0.0.1:8010','--public-web','true'],failOnStartupError:true}}];
 const overlay=[];for(const node of nodes){if(new RegExp('(?:^|\\n)\\s*- id: '+node.id+'(?:\\r?\\n|$)').test(prior))overlay.push(node);else overlay.push({insert:[node]});}
 // Existing presets, custom plugins, selected models and permission controls are
 // left in the user's profile. Only our executable/source paths are redirected.
 const defaults=null; // Fresh defaults were persisted once; later user edits win.
 const overlayFile=join(connector,'installed-runtime.patch.yml');atomic(overlayFile,JSON.stringify(overlay,null,2));
 return {dsh,connector,connection,overlayFile,fresh,defaults};
}
async function listening(port){return new Promise(resolve=>{const socket=createConnection({host:'127.0.0.1',port});socket.setTimeout(700);socket.once('connect',()=>{socket.destroy();resolve(true);});for(const event of ['error','timeout'])socket.once(event,()=>{socket.destroy();resolve(false);});});}
export async function ensureBundledBackend({resources,executable,home=homedir(),timeout=90000}){
 const provider=join(resources,'provider'),node=join(resources,'harness','runtime','primary-runtime','dependencies','node','bin','node.exe'),prepared=prepareInstalledProfile({resources,provider,executable:node,home});
 const status=async()=>{const response=await fetch('http://127.0.0.1:8766/status',{headers:{Authorization:'Bearer '+prepared.connection.token},signal:AbortSignal.timeout(2000)});if(!response.ok)throw Error('Another process owns Friday’s local connection. Close the other app first.');return response.json();};
 if(await listening(3030)){await status();return {...prepared,reused:true};}
 // Never stop an unknown process or an active request merely to claim a port.
 if(await listening(8766))throw Error('Friday’s bridge is running without its interface. Close the other Friday process before starting this copy.');
 const support=join(resources,'harness','runtime'),logDir=join(prepared.dsh,'logs');mkdirSync(logDir,{recursive:true});
 const stamp=new Date().toISOString().replace(/[:.]/g,'-'),out=join(logDir,'browser-'+stamp+'.out.log'),err=join(logDir,'browser-'+stamp+'.err.log');
 const env={...process.env,FRIDAY_BUNDLED_RESOURCES:resources,DSH_HOME:prepared.dsh,DSH_DESKTOP_NODE_EXECUTABLE:node,
  PATH:[join(support,'bin'),join(support,'primary-runtime','dependencies','node','bin'),join(support,'primary-runtime','dependencies','python'),join(support,'git','cmd'),process.env.PATH||''].join(';')};
 const stdout=openSync(out,'a'),stderr=openSync(err,'a');let child;
 try{child=spawn(node,['--expose-internals',join(provider,'desktop','backend-entry.mjs'),'--profile','web',...(prepared.defaults?['--patch',prepared.defaults]:[]),'--patch',prepared.overlayFile,'--port','3030','--host','127.0.0.1','--no-open'],{env,cwd:home,windowsHide:true,detached:false,stdio:['ignore',stdout,stderr,'ipc']});}finally{closeSync(stdout);closeSync(stderr);}
 let spawnError;child.once('error',error=>{spawnError=error;});child.unref();
 const close=async()=>{if(child.exitCode!==null)return;child.send({type:'friday-stop'});await Promise.race([new Promise(resolve=>child.once('exit',resolve)),new Promise((_,reject)=>{const timer=setTimeout(()=>reject(Error('Friday backend is still closing; wait before updating.')),15000);timer.unref();})]);};
 const until=Date.now()+timeout;while(Date.now()<until){if(spawnError)throw spawnError;if(child.exitCode!==null)throw Error('Friday backend stopped during startup. See '+err);try{if(await listening(3030)){await status();atomic(join(prepared.connector,'installed-runtime.json'),JSON.stringify({pid:child.pid,executable,resources,startedAt:new Date().toISOString()}));return {...prepared,reused:false,pid:child.pid,close};}}catch(error){if(!/fetch failed|aborted|timed out/.test(error.message))throw error;}await new Promise(r=>setTimeout(r,350));}
 throw Error('Friday backend did not become ready. See '+err);
}
