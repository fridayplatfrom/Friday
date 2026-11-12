import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {join,resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
const here=dirname(fileURLToPath(import.meta.url));
if(!process.argv.includes('--probe')){
 const carrier=process.env.FRIDAY_CARRIER_BINARY||resolve(here,'../node_modules/electron/dist/electron.exe');
 const result=spawnSync(carrier,['--expose-internals',fileURLToPath(import.meta.url),'--probe'],{env:{...process.env,ELECTRON_RUN_AS_NODE:'1'},encoding:'utf8',windowsHide:true,timeout:45000});
 console.log(result.stdout);console.error(result.stderr);if(result.error)console.error(result.error.message);process.exitCode=result.status===0?0:1;
}else{
 const require=createRequire(import.meta.url),archive=process.env.FRIDAY_COMPAT_ARCHIVE||join(process.env.FRIDAY_HARNESS_DIST||join(process.env.LOCALAPPDATA,'Programs','DeepSeek Harness'),'resources','app.asar'),modules=process.env.FRIDAY_COMPAT_MODULES||join(archive,'dsh','node_modules');
 console.log('Node '+process.versions.node+'; Electron '+(process.versions.electron||'none'));let failed=false;
 for(const name of ['koffi','sharp'])try{require(join(modules,name));console.log(name+': load OK');}catch(error){console.error(name+': '+error.message);failed=true;}
 try{
  const pty=require(join(modules,'node-pty')),child=pty.spawn(join(process.env.SystemRoot,'System32','WindowsPowerShell','v1.0','powershell.exe'),['-NoProfile','-NonInteractive','-Command',"Write-Output 'FRIDAY_PTY_OK'"],{cols:80,rows:24,cwd:tmpdir(),env:process.env});
  let output='';child.onData(data=>output+=data);child.onExit(result=>{const passed=result.exitCode===0&&output.includes('FRIDAY_PTY_OK');console.log('Native terminal: '+(passed?'PASS':'FAIL'));process.exit(failed||!passed?1:0);});
 }catch(error){console.error('Native terminal: '+error.message);process.exitCode=1;}
}
