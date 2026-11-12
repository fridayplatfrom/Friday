import {readFileSync,statfsSync,mkdirSync,existsSync,writeFileSync,readdirSync,linkSync,copyFileSync,unlinkSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {build,Platform,Arch} from 'electron-builder';
import {NtExecutable,NtExecutableResource} from 'resedit';
const desktop=resolve(dirname(fileURLToPath(import.meta.url)),'..'),stage=resolve(process.env.FRIDAY_BUILD_STAGE||join(desktop,'.packaging'));
process.env.ELECTRON_BUILDER_COMPRESSION_LEVEL??='1';
const context=JSON.parse(readFileSync(join(stage,'build-context.json'),'utf8'));
if(!existsSync(join(context.resources,'harness','runtime','git','cmd','git.exe')))throw Error('Run packaging/vendor-git.ps1 to prepare the verified Git runtime.');
const free=statfsSync(stage);if(free.bavail*free.bsize<1500*1024**2)throw Error('At least 1.5 GB free is required for the space-efficient build. Prepared files are retained.');
const output=resolve(process.env.FRIDAY_RELEASE_DIR||join(desktop,'release'));mkdirSync(output,{recursive:true});
function linkPayload(from,to){mkdirSync(to,{recursive:true});for(const entry of readdirSync(from,{withFileTypes:true})){const a=join(from,entry.name),b=join(to,entry.name);if(entry.isDirectory())linkPayload(a,b);else try{linkSync(a,b);}catch(error){if(error.code==='EXDEV')copyFileSync(a,b);else throw error;}}}
// Resource files remain read-only during packaging. The installer archives all
// bytes normally; installed PCs never need these developer-side hard links.
// The PE executable is a private copy, since icon/version editing mutates it.
const carrier=join(context.electron,'electron.exe'),carrierBytes=readFileSync(carrier);
let signed=false;try{NtExecutable.from(carrierBytes);}catch(error){if(!error.message.includes('signed executable'))throw error;signed=true;}
const privateExecutable=NtExecutable.from(carrierBytes,{ignoreCert:true}),privateResources=NtExecutableResource.from(privateExecutable);
// Friday cannot retain the upstream application's signature or its ASAR hash.
// Rebuild these only in our private copy; keep integrity enforcement enabled.
const oldIntegrity=privateResources.entries.some(entry=>entry.type==='INTEGRITY'&&entry.id==='ELECTRONASAR');
if(signed||oldIntegrity){privateResources.entries=privateResources.entries.filter(entry=>!(entry.type==='INTEGRITY'&&entry.id==='ELECTRONASAR'));privateResources.outputResource(privateExecutable);unlinkSync(carrier);writeFileSync(carrier,Buffer.from(privateExecutable.generate()));}
function linkImmutableElectron(from,to){for(const entry of readdirSync(from,{withFileTypes:true})){if(entry.name==='resources'||entry.name==='electron.exe')continue;const a=join(from,entry.name),b=join(to,entry.name);if(!existsSync(b))continue;if(entry.isDirectory()){linkImmutableElectron(a,b);continue;}if(createHash('sha256').update(readFileSync(a)).digest('hex')!==createHash('sha256').update(readFileSync(b)).digest('hex'))continue;unlinkSync(b);try{linkSync(a,b);}catch{copyFileSync(a,b);}}}
const artifacts=await build({targets:Platform.WINDOWS.createTarget(['nsis'],Arch.x64),config:{appId:'dev.friday.desktop',productName:'Friday',electronVersion:context.metadata.electronVersion,electronDist:context.electron,
 directories:{app:context.application,output},asar:true,npmRebuild:false,files:['**/*'],afterPack:async event=>{linkImmutableElectron(context.electron,event.appOutDir);linkPayload(context.resources,join(event.appOutDir,'resources'));},
 win:{icon:join(desktop,'../assets/friday.png'),artifactName:'Friday-Setup-${version}-${arch}.${ext}'},
 nsis:{oneClick:false,perMachine:false,allowElevation:false,allowToChangeInstallationDirectory:true,createDesktopShortcut:true,createStartMenuShortcut:true,shortcutName:'Friday',runAfterFinish:false,deleteAppDataOnUninstall:false,useZip:true,differentialPackage:false},publish:null}});
for(const file of artifacts.filter(path=>path.endsWith('.exe'))){writeFileSync(file+'.sha256',createHash('sha256').update(readFileSync(file)).digest('hex')+'\n');console.log('Installer: '+file);}
