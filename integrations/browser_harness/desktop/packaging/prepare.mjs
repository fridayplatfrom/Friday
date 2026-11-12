import {mkdirSync,readdirSync,statSync,existsSync,linkSync,copyFileSync,readFileSync,writeFileSync,realpathSync} from 'node:fs';
import {join,dirname,resolve,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {nativeCompactionPatch} from '../../native-compaction.mjs';
import {stableNativeQuestions} from '../../native-question-config.mjs';
import {materializeHarness} from './materialize-harness.mjs';
const desktop=resolve(dirname(fileURLToPath(import.meta.url)),'..'),provider=resolve(desktop,'..');
const source=resolve(process.env.FRIDAY_HARNESS_DIST||join(process.env.LOCALAPPDATA,'Programs','DeepSeek Harness'));
const electronSource=resolve(process.env.FRIDAY_ELECTRON_DIST||join(desktop,'node_modules','electron','dist'));
const stage=resolve(desktop,'.packaging');
const target=resolve(process.env.FRIDAY_BUILD_STAGE||stage);if(existsSync(target))throw Error('Build stage must be new.');
mkdirSync(target,{recursive:true});
function tree(from,to,ancestors=new Set()){
 const canonical=realpathSync(from);if(ancestors.has(canonical))throw Error('Dependency link cycle: '+from);const next=new Set(ancestors).add(canonical);mkdirSync(to,{recursive:true});
 for(const entry of readdirSync(from,{withFileTypes:true})){const a=join(from,entry.name),b=join(to,entry.name);if(entry.isDirectory()||entry.isSymbolicLink()&&statSync(a).isDirectory())tree(a,b,next);else{try{linkSync(a,b);}catch(error){if(error.code==='EXDEV'||error.code==='EPERM')copyFileSync(a,b);else throw error;}}}
}
function file(from,to){mkdirSync(dirname(to),{recursive:true});try{linkSync(from,to);}catch{copyFileSync(from,to);}}
const carrier=join(source,'DeepSeek Harness.exe'),original=join(source,'resources','app.asar');for(const path of [carrier,original])if(!existsSync(path))throw Error('Missing verified Harness distribution file: '+path);
// Keep the existing desktop's browser version: downgrading Chromium could
// damage saved profiles. The native addon compatibility test gates this runtime.
const electron=join(target,'electron-dist');mkdirSync(join(electron,'resources'),{recursive:true});
for(const entry of readdirSync(electronSource,{withFileTypes:true})){if(entry.isFile()&&entry.name!=='electron.exe')file(join(electronSource,entry.name),join(electron,entry.name));}
file(join(electronSource,'electron.exe'),join(electron,'electron.exe'));
for(const name of ['locales','swiftshader'])if(existsSync(join(electronSource,name)))tree(join(electronSource,name),join(electron,name));
file(join(electronSource,'resources','default_app.asar'),join(electron,'resources','default_app.asar'));
const resources=join(target,'resources'),harness=join(resources,'harness');mkdirSync(harness,{recursive:true});materializeHarness(original,harness);tree(join(source,'resources','runtime'),join(harness,'runtime'));
const payload=join(resources,'provider');mkdirSync(payload,{recursive:true});
for(const entry of readdirSync(provider,{withFileTypes:true})){if(entry.isFile()&&(/\.(?:mjs|js|css)$/.test(entry.name)||entry.name==='package.json'))file(join(provider,entry.name),join(payload,entry.name));}
for(const name of ['assets','extension','plugins'])if(existsSync(join(provider,name)))tree(join(provider,name),join(payload,name));
mkdirSync(join(payload,'desktop'));for(const entry of readdirSync(desktop,{withFileTypes:true}))if(entry.isFile()&&/\.(?:mjs|cjs|js|html|css|txt)$/.test(entry.name))file(join(desktop,entry.name),join(payload,'desktop',entry.name));
// Enumerate only the provider's production dependency closure. Build tools,
// tests, transcripts, local connection config and node_modules caches stay out.
const list=spawnSync(process.env.ComSpec||'cmd.exe',['/d','/s','/c','npm ls --omit=dev --all --parseable'],{cwd:provider,encoding:'utf8',windowsHide:true});
if(list.status!==0)throw Error('Production dependency inventory failed: '+list.stderr);
for(const dependency of list.stdout.trim().split(/\r?\n/).slice(1)){const rel=relative(provider,dependency);if(rel.startsWith('..')||!rel.startsWith('node_modules'))throw Error('External dependency requires review: '+dependency);if(!existsSync(join(payload,rel)))tree(dependency,join(payload,rel));}
// UI bundle preparation is reproducible from shipped defaults, never from the
// developer's live profile or conversations.
const dump=spawnSync(carrier,['--expose-internals',join(original,'dsh','node_modules','@deepseek-ai','dsh-desktop-host','lib','cli.js'),'--profile','web','--dump-default-config'],{env:{...process.env,ELECTRON_RUN_AS_NODE:'1'},encoding:'utf8',windowsHide:true,maxBuffer:4*1024*1024});
if(dump.status!==0)throw Error('Cannot read shipped profile defaults: '+dump.stderr);
const branding=[...['llm-deepseek','llm-deepseek-account','ui-settings-account','ui-brand-official','ui-deepseek-model-label-1017','session-log-deepseek','ui-settings-session-log'].map(id=>({id,disabled:true})),{id:'ui-sidebar-browser',name:'@deepseek-ai/dsh-client-ui-sidebar-browser',disabled:false},{id:'agent-default-model',config:{provider:'browser-web',model:'chatgpt-web'}}];
const {yaml}=createRequire(import.meta.url)('playwright-core/lib/utilsBundle');
writeFileSync(join(harness,'friday-default-patch.yml'),stableNativeQuestions(nativeCompactionPatch(dump.stdout)).yaml.replace(/^# ==.*(?:\r?\n|$)/gm,'')+'\n'+yaml.stringify(branding));
file(join(desktop,'native-browser-LICENSE.txt'),join(harness,'LICENSE-DeepSeek.txt'));
const application=join(target,'app');mkdirSync(application);const version=JSON.parse(readFileSync(join(desktop,'package.json'),'utf8')).version;
writeFileSync(join(application,'package.json'),JSON.stringify({name:'friday',productName:'Friday',version,private:true,type:'commonjs',main:'bootstrap.cjs',description:'Friday desktop workspace',author:'Friday',license:'UNLICENSED'},null,2));
writeFileSync(join(application,'bootstrap.cjs'),"const {pathToFileURL}=require('node:url');const {join}=require('node:path');import(pathToFileURL(join(process.resourcesPath,'provider','desktop','main.mjs')).href).catch(error=>{require('electron').dialog.showErrorBox('Friday could not start',error.message);require('electron').app.exit(1);});\n");
const metadata={version,electronVersion:readFileSync(join(electronSource,'version'),'utf8').trim(),harnessSha256:createHash('sha256').update(readFileSync(original)).digest('hex'),sourceRuntime:'DeepSeek Harness 0.2.1-rc.5',preparedAt:new Date().toISOString(),containsUserData:false};writeFileSync(join(resources,'bundle-manifest.json'),JSON.stringify(metadata,null,2));
writeFileSync(join(target,'build-context.json'),JSON.stringify({target,application,resources,electron,metadata},null,2));
console.log('Prepared standalone payload: '+target);
