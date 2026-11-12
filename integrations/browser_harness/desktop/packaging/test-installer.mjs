// Executes only this build's checksum-verified installer in a disposable path.
// Actual provider sign-in/streaming remains a separate live acceptance gate.
import {existsSync,mkdirSync,readFileSync,writeFileSync,mkdtempSync,readdirSync,realpathSync,rmSync,statfsSync,statSync} from 'node:fs';
import {resolve,join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const desktop=resolve(dirname(fileURLToPath(import.meta.url)),'..'),release=resolve(process.env.FRIDAY_RELEASE_DIR||join(desktop,'release'));
const version=JSON.parse(readFileSync(join(desktop,'package.json'),'utf8')).version,installer=join(release,`Friday-Setup-${version}-x64.exe`);
const actual=createHash('sha256').update(readFileSync(installer)).digest('hex');if(actual!==readFileSync(installer+'.sha256','utf8').trim())throw Error('Installer checksum does not match this build.');
// Keep the test install close to the normal per-user path length.
const testRoot=mkdtempSync(join(process.env.LOCALAPPDATA,'Fry-')),installed=join(testRoot,'app'),home=join(testRoot,'home');mkdirSync(home);
const report={installer,sha256:actual,testRoot,checks:{},scope:'Silent install, bundled CLI, in-place reinstall, and uninstall preservation; no claim about live provider authentication'};
const temporary=join(testRoot,'t');
const env={...process.env,USERPROFILE:home,DSH_HOME:join(home,'.dsh'),TEMP:temporary,TMP:temporary};
function run(exe,args,extra={}){const result=spawnSync(exe,args,{windowsHide:true,encoding:'utf8',env,timeout:600000,maxBuffer:4e6,...extra});if(result.error||result.status!==0)throw Error((result.error?.message||`Exit ${result.status}`)+' '+String(result.stderr).slice(-1000));return result;}
try{
 const registry=run('reg.exe',['query','HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall','/s','/f','Friday','/d'],{timeout:15000});
 if(registry.stdout.includes('DisplayName'))throw Error('A registered Friday installation exists. Run installer tests in a separate Windows user or VM.');
}catch(error){if(!error.message.startsWith('Exit 1'))throw error;}
try{
 const unpacked=join(release,'win-unpacked');if(existsSync(unpacked)){const target=realpathSync(unpacked);if(!target.startsWith(realpathSync(release)+'\\'))throw Error('Unpacked build target escaped its release folder');rmSync(target,{recursive:true,force:true});}
 if(process.env.FRIDAY_COMPRESS_INSTALL_TEST==='1'){run('compact.exe',['/C','/I','/Q',testRoot,home]);report.testStorage='NTFS-compressed disposable test folders; normal installer unchanged';}
 mkdirSync(temporary,{recursive:true});
 const free=statfsSync(testRoot);if(free.bavail*free.bsize<1500*1024**2)throw Error('At least 1.5 GB free is required for the installed test copy. The installer is retained.');
 run(installer,['/S','/D='+installed],{windowsVerbatimArguments:true});const executable=join(installed,'Friday.exe'),resources=join(installed,'resources');if(!existsSync(executable))throw Error('Installer did not create Friday.exe');report.checks.install=true;console.log('Silent installation: PASS');
 for(const name of ['snapshot_blob.bin','v8_context_snapshot.bin','resources.pak','vulkan-1.dll'])if(!existsSync(join(installed,name)))throw Error('Installer payload is incomplete: '+name);
 const stageResources=join(desktop,'.packaging','resources');let payloadFiles=0;
 function verifyPayload(from,to){for(const entry of readdirSync(from,{withFileTypes:true})){const source=join(from,entry.name),target=join(to,entry.name);if(entry.isDirectory())verifyPayload(source,target);else{if(!existsSync(target)||statSync(source).size!==statSync(target).size)throw Error('Installed payload is missing or truncated: '+target);payloadFiles++;}}}
 if(existsSync(stageResources)){verifyPayload(stageResources,resources);report.checks.payloadFilesVerified=payloadFiles;console.log('Complete payload file sizes: PASS ('+payloadFiles+')');}
 const cli=join(resources,'harness','dsh','node_modules','@deepseek-ai','dsh-desktop-host','lib','cli.js'),node=join(resources,'harness','runtime','primary-runtime','dependencies','node','bin','node.exe');
 const dumped=run(node,['--expose-internals',cli,'--profile','web','--dump-default-config']);if(!dumped.stdout.includes('ui-sidebar-browser')||!dumped.stdout.includes('tool-pwsh'))throw Error('Installed native feature catalog is incomplete');report.checks.bundledCli=true;console.log('Installed Harness CLI: PASS');
 const provider=join(resources,'provider');if(!existsSync(join(provider,'desktop','backend-runtime.mjs'))||!existsSync(join(provider,'node_modules','playwright-core','package.json')))throw Error('Installed connector dependencies missing');report.checks.bundledConnector=true;
 run(join(resources,'harness','runtime','primary-runtime','dependencies','node','bin','node.exe'),['--version']);run(join(resources,'harness','runtime','primary-runtime','dependencies','python','python.exe'),['-I','-c','import docx,pptx,openpyxl,PIL; print("OK")']);run(join(resources,'harness','runtime','git','cmd','git.exe'),['--version']);report.checks.runtimes=true;console.log('Installed Node, Python, documents and Git: PASS');
 const sentinel=join(home,'.dsh','installer-preservation.json');mkdirSync(dirname(sentinel),{recursive:true});const state=JSON.stringify({synthetic:true,tabs:['https://example.com/'],receipts:{form:{status:'completed',delivered:true}},savedLoginMarker:'synthetic'});writeFileSync(sentinel,state);
 run(installer,['/S','/D='+installed],{windowsVerbatimArguments:true});if(readFileSync(sentinel,'utf8')!==state)throw Error('Reinstall changed saved profile data');report.checks.reinstallPreservesData=true;console.log('In-place reinstall preservation: PASS');
 const uninstall=readdirSync(installed).find(name=>/^Uninstall.*\.exe$/i.test(name));if(!uninstall)throw Error('Uninstaller missing');
 if(process.env.FRIDAY_KEEP_TEST_INSTALL==='1')report.uninstallDeferredForGuiTest=true;
 else{run(join(installed,uninstall),['/S',`_?=${installed}`],{windowsVerbatimArguments:true});if(readFileSync(sentinel,'utf8')!==state)throw Error('Uninstall changed saved profile data');if(existsSync(executable))throw Error('Uninstall did not remove Friday.exe');report.checks.uninstallPreservesData=true;}
 report.passed=true;
}catch(error){report.passed=false;report.error=error.stack;process.exitCode=1;}
writeFileSync(join(testRoot,'report.json'),JSON.stringify(report,null,2));writeFileSync(join(release,'installer-test-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
