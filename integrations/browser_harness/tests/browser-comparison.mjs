// Explicit real-engine comparison: npm run test:browser-comparison.
// No provider/API calls, user cookies, existing tabs or live Friday processes.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdirSync,readFileSync,writeFileSync,existsSync,unlinkSync,readdirSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright-core';
import {DemoFormServer} from '../demo-form.mjs';
import {fixtureBytes} from '../native-browser-fixture.mjs';
import {upstreamConnection} from '../workspace-browser-upstream.mjs';
import {WorkspaceBrowserManager} from '../workspace-browser-manager.mjs';
import {argumentDigest} from '../workspace-browser-state.mjs';
import {nativeTaskContext} from '../native-task-context.mjs';
const home=resolve(fileURLToPath(new URL('../../../output/browser-comparison/',import.meta.url)),new Date().toISOString().replace(/[:.]/g,'-'));
mkdirSync(home,{recursive:true});
const evidence=join(home,'evidence'),server=await new DemoFormServer({port:0,testRoot:evidence}).start();
const origin=`http://127.0.0.1:${server.port}`,configuration={browser:{isolated:false},snapshot:{mode:'full'},network:{allowedOrigins:[origin]}};
const report={scope:'Browser-tool comparison, not full original-app/model transport comparison',home,startedAt:new Date().toISOString(),runs:[]};
const text=result=>(result.content||[]).filter(c=>c.type==='text').map(c=>c.text).join('\n');
const files=dir=>existsSync(dir)?readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(join(dir,e.name)):[join(dir,e.name)]):[];
let child;
async function startElectron(root,restore=false){
 const relayFile=join(root,'relay.json');if(existsSync(relayFile))unlinkSync(relayFile);if(existsSync(join(root,'stop')))unlinkSync(join(root,'stop'));
 const executable=resolve(fileURLToPath(new URL('../desktop/node_modules/electron/dist/electron.exe',import.meta.url)));
 const env={...process.env,FRIDAY_COMPARISON_ROOT:root,FRIDAY_COMPARISON_RESTORE:restore?'1':''};delete env.ELECTRON_RUN_AS_NODE;
 child=spawn(executable,[fileURLToPath(new URL('./fixtures/browser-comparison-electron.mjs',import.meta.url))],{env,windowsHide:true,stdio:['ignore','pipe','pipe']});
 let logs='';child.stdout.on('data',d=>logs+=d);child.stderr.on('data',d=>logs+=d);
 const until=Date.now()+30000;while(!existsSync(relayFile)){if(child.exitCode!==null||child.signalCode||Date.now()>until){writeFileSync(join(root,'electron.log'),logs);throw Error(`Isolated Electron host failed (${child.exitCode}/${child.signalCode}): `+logs.slice(-1600));}await new Promise(r=>setTimeout(r,100));}
 return relayFile;
}
async function stopElectron(root){if(!child||child.exitCode!==null||child.signalCode)return;writeFileSync(join(root,'stop'),'stop');const until=Date.now()+10000;while(child.exitCode===null&&!child.signalCode&&Date.now()<until)await new Promise(r=>setTimeout(r,100));if(child.exitCode===null&&!child.signalCode){child.kill();throw Error('Disposable test host did not flush and exit');}child=null;}
try{
 for(const mode of ['upstream','friday']){
  const root=join(home,mode);mkdirSync(root);const base=origin+'/_browser-test/'+mode,upload=join(root,'synthetic-upload.txt');writeFileSync(upload,fixtureBytes);
  const run={mode,steps:[],passed:false};report.runs.push(run);let context,client,manager;
  try{
   if(mode==='upstream'){
    context=await chromium.launchPersistentContext(join(root,'chrome-profile'),{executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,acceptDownloads:true});
    client=await upstreamConnection(()=>new Proxy(context,{get:(target,key)=>key==='close'?async()=>{}:typeof target[key]==='function'?target[key].bind(target):target[key]}),{...configuration,outputDir:root},root);
   }else{
    const relayFile=await startElectron(root);
    manager=new WorkspaceBrowserManager({root:join(root,'receipts'),origins:[origin],nativeDesktop:true,launch:()=>nativeTaskContext(chromium,{directory:root,sessionId:'comparison'},relayFile),upstream:factory=>upstreamConnection(factory,{...configuration,outputDir:root},root)});
   }
   let latest='';
   async function call(name,args={},expectedError=false){
    const began=Date.now(),id=randomUUID();let result;
    if(manager){manager.select({id,sessionId:'comparison',directory:root,tool:name,digest:argumentDigest(args)});try{result=await manager.call(name,args);if(!result.isError)manager.lease.workspace.state.acknowledge(id,'comparison');}finally{manager.release(id);}}
    else result=await client.callTool({name,arguments:args},undefined,{timeout:45000});
    latest=text(result);for(const match of latest.matchAll(/\[Snapshot\]\(\.\/([^\n)]+)\)/g)){const snapshot=resolve(root,match[1]);if(snapshot.startsWith(root+'\\')&&existsSync(snapshot))latest+='\n'+readFileSync(snapshot,'utf8');}run.steps.push({name,args,ms:Date.now()-began,isError:!!result.isError,expectedError,result:latest});writeFileSync(join(root,'steps.json'),JSON.stringify(run.steps,null,2));assert.equal(result.isError||false,expectedError,latest);return latest;
   }
   const click=target=>call('browser_click',{target});
   await call('browser_navigate',{url:base});
   await call('browser_tabs',{action:'select',index:999},true);
   if(manager){const state=manager.workspace(root).state;assert.equal(state.pending().length,0);assert.equal(state.state.activeIndex,0);run.missingTabRecovery=true;}
   await click('button:has-text("Use fictional test account")');
   await click('a[href$="/details"]');assert.match(latest,/Link click succeeded/);await click(`a[href="/_browser-test/${mode}"]`);
   await click('a[target="_blank"]');await call('browser_tabs',{action:'list'});
   await call('browser_tabs',{action:'select',index:1});await call('browser_snapshot');assert.match(latest,/Second tab opened/);
   await call('browser_tabs',{action:'select',index:0});
   await call('browser_fill_form',{fields:[{target:'input[name="name"]',name:'Name',type:'textbox',value:'Friday Test User'},{target:'input[name="email"]',name:'Email',type:'textbox',value:'friday@example.invalid'},{target:'select[name="topic"]',name:'Topic',type:'combobox',value:'Uploads and downloads'},{target:'textarea[name="notes"]',name:'Notes',type:'textbox',value:'identical browser comparison'},{target:'input[name="confirm"]',name:'Confirmation',type:'checkbox',value:'true'}]});
   await click('button:has-text("Submit test form once")');
   await click('input[type="file"]');await call('browser_file_upload',{paths:[upload]});await click('button:has-text("Upload test file once")');
   await click('a[download]');await call('browser_snapshot');
   const until=Date.now()+10000;let downloaded;do{downloaded=files(root).find(f=>!f.includes('profile')&&!f.includes('synthetic-upload')&&readFileSync(f).equals(fixtureBytes));if(downloaded)break;await new Promise(r=>setTimeout(r,100));}while(Date.now()<until);
   assert.ok(downloaded,'Browser download bytes must exist on disk');run.download={path:downloaded,sha256:createHash('sha256').update(readFileSync(downloaded)).digest('hex')};
   const before=JSON.parse(readFileSync(join(evidence,mode+'.json'),'utf8'));assert.equal(before.signIns,1);assert.equal(before.formSubmissions,1);assert.equal(before.uploads.length,1);assert.equal(before.downloads,1);assert.equal(before.uploads[0].sha256,run.download.sha256);
   if(manager){const state=manager.workspace(root).state,record=state.state.actions.find(action=>action.tool==='browser_click'&&action.digest===argumentDigest({target:'button:has-text("Submit test form once")'}));assert.ok(record);manager.select({...record,directory:root});try{await assert.rejects(manager.call(record.tool,{target:'button:has-text("Submit test form once")'}),/not replayed/);}finally{manager.release(record.id);}run.duplicateDispatchBlocked=true;}
   await call('browser_navigate',{url:base});assert.match(latest,/Signed in as Fictional Friday Tester/);
   await call('browser_take_screenshot',{filename:join(root,'completed.png')});
   if(manager){await manager.close();manager=null;await stopElectron(root);const relayFile=await startElectron(root,true);context=await nativeTaskContext(chromium,{directory:root,sessionId:'comparison'},relayFile);}
   else{await client.close();client=null;await context.close();context=await chromium.launchPersistentContext(join(root,'chrome-profile'),{executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});for(const url of [base,base+'/secondary'])await context.newPage().then(p=>p.goto(url));}
   const pages=context.pages();assert.ok(pages.some(p=>p.url()===base));assert.ok(pages.some(p=>p.url()===base+'/secondary'));const main=pages.find(p=>p.url()===base);assert.match(await main.locator('[role="status"]').innerText(),/Signed in as Fictional Friday Tester/);
   assert.deepEqual(JSON.parse(readFileSync(join(evidence,mode+'.json'),'utf8')),before,'Restart must not repeat committed actions');run.recovery={login:true,tabs:true,restoration:mode==='friday'?'isolated Electron host restores saved URLs':'test explicitly reopens URLs; no stock tab-restoration claim',noRepeatedActions:true};run.counters=before;run.passed=true;
  }catch(error){run.error=error.stack;console.error(mode+': '+error.message);}
  finally{await client?.close().catch(()=>{});await manager?.close().catch(()=>{});await context?.close().catch(()=>{});if(mode==='friday')await stopElectron(root);writeFileSync(join(home,'report.json'),JSON.stringify(report,null,2));}
  console.log(mode+': '+(run.passed?'PASS':'FAIL'));
 }
}finally{await server.close();}
console.log('Report: '+join(home,'report.json'));if(report.runs.some(run=>!run.passed))process.exitCode=1;
