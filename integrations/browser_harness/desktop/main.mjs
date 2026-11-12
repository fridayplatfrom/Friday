import {DesktopBrowserGuests} from './native-browser-guests.mjs';
import {startTaskBrowserRelay} from './task-browser-relay.mjs';
import {realpathSync} from 'node:fs';
import {app,BrowserWindow,WebContentsView,session,ipcMain,dialog,Menu} from 'electron';
import fs from 'node:fs';
import {join,dirname,basename} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {homedir} from 'node:os';
import {randomUUID} from 'node:crypto';
import {DesktopState} from './state.mjs';
import {submitOnce} from './submission.mjs';
import {Signal,providerURL,siteForURL,desktopProviders,navigationAllowed,localHarness,pageMessageTypes} from './policy.mjs';
import {dockBounds} from './dock.mjs';
import {WebsiteTabManager} from '../extension/tab-manager.js';
import {RecoveryBudget,recoveryTarget} from './recovery.mjs';
import {arrangeBackgroundViews,presentedDock} from './background.mjs';
import {fridayTheme} from './theme.mjs';
import {FirstRunSetup} from './onboarding.mjs';
import {setupSession} from '../setup-test.mjs';
import {ensureBundledBackend} from './backend-runtime.mjs';

const here=dirname(fileURLToPath(import.meta.url)),extension=join(here,'../extension');
app.setName('Friday');
app.commandLine.appendSwitch('disable-renderer-backgrounding');
// Native task guests must keep rendering for visibility checks and screenshots
// even while another application covers Friday's window.
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows');
const root=join(homedir(),'.dsh/friday-desktop');
const existingInstallation=fs.existsSync(join(root,'state.json'))||fs.existsSync(join(root,'profile'));
fs.mkdirSync(root,{recursive:true});app.setPath('userData',join(root,'profile'));
if(!app.requestSingleInstanceLock())app.exit(0);
else void start().catch(error=>{dialog.showErrorBox('Friday desktop could not start',String(error.message));app.exit(1);});
app.on('window-all-closed',()=>app.quit());

async function start(){
 await app.whenReady();
 const bundledBackend=app.isPackaged?await ensureBundledBackend({resources:process.resourcesPath,executable:process.execPath}):null;
 const state=new DesktopState(join(root,'state.json'));
 state.data.clientId||=randomUUID();state.save();
 const connection=JSON.parse(fs.readFileSync(join(homedir(),'.dsh/browser-connector/connection.json'),'utf8'));
 if(connection.port!==8766||typeof connection.token!=='string')throw Error('Run Friday setup and start the existing Harness server first.');
 const nativeFetch=globalThis.fetch;
 const bridge=async(path,body)=>{const r=await nativeFetch('http://127.0.0.1:8766'+path,{method:body===undefined?'GET':'POST',headers:{Authorization:`Bearer ${connection.token}`,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)}),signal:AbortSignal.timeout(10000)});const data=await r.json();if(!r.ok)throw Error(data.error||'Friday bridge rejected the request');return data;};
 for(let attempt=0;;attempt++){
   try{await bridge('/desktop/claim',{clientId:state.data.clientId});break;}
   catch(error){if(attempt>=29||!/fetch failed|ECONNREFUSED|timed out|aborted/i.test(error.message))throw error;await new Promise(resolve=>setTimeout(resolve,1000));}
 }
 const pages=new Map(),pending=new Map(),backgroundListeners=[];
 const updated=new Signal(),removed=new Signal(),changed=new Signal(),downloadCreated=new Signal(),downloadChanged=new Signal();
 const downloads=new Map();let nextDownload=1,activeId=state.data.activeId||null,closing=false,restoringTabs=true;
 let selectedSite=state.data.selectedSite||'chatgpt-web';
 const lastTabs={...state.data.lastTabs};
 const workspaceSession=()=>state.data.nativeSessionId||Object.values(state.data.storage.harnessWebsitePairs||{}).find(pair=>pair.tabId===activeId)?.sessionId;
 const shellURL=pathToFileURL(join(here,'shell.html')).href;
 const win=new BrowserWindow({width:1450,height:930,minWidth:1000,minHeight:650,title:'Friday',icon:join(here,'../assets/friday.png'),backgroundColor:'#202023',webPreferences:{preload:join(here,'recovery-preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
 const recoveryBudget=new RecoveryBudget();let harnessHealthy=true;
 const diagnose=(event,details={})=>{try{const file=join(root,'renderer-health.jsonl');if(fs.existsSync(file)&&fs.statSync(file).size>1048576)fs.renameSync(file,file+'.previous');fs.appendFileSync(file,JSON.stringify({at:new Date().toISOString(),event,...details})+'\n');}catch{}};
 app.on('child-process-gone',(_event,details)=>diagnose('child-process-gone',{type:details.type,reason:details.reason,exitCode:details.exitCode}));
 const profiles=new Map();
 const getProfile=site=>{if(profiles.has(site))return profiles.get(site);const profile=session.fromPartition(site==='chatgpt-web'?'persist:friday-chatgpt':'persist:friday-'+site);profile.setPermissionRequestHandler((_wc,_permission,callback)=>callback(false));profile.setPermissionCheckHandler(()=>false);profile.on('will-download',onDownload);profiles.set(site,profile);return profile;};
 const describe=page=>({id:page.id,url:providerURL(page.view.webContents.getURL(),page.site)||page.lastChatURL,active:page.id===activeId,windowId:1,incognito:false,site:page.site});
 const publish=()=>{};
 const saveTabs=()=>{if(!restoringTabs){state.data.tabs=[...pages.values()].map(p=>({id:p.id,site:p.site,url:providerURL(p.view.webContents.getURL(),p.site)||p.lastChatURL}));state.data.activeId=activeId;state.data.selectedSite=selectedSite;state.save();}publish();};
 let harness;
 let dock=null;let dockQueue=Promise.resolve();let revealedProvider=null;
 let setupFlow,setupDock=null;
 const layout=()=>{if(win.isDestroyed())return;const [width,height]=win.getContentSize();arrangeBackgroundViews({contentView:win.contentView,harness,pages:pages.values(),dock:setupFlow?.visible?setupDock:presentedDock(dock,revealedProvider),healthy:harnessHealthy,width,height});};
 const focus=id=>{const p=pages.get(id);if(!p)throw Error('Unknown desktop tab');activeId=id;selectedSite=p.site;lastTabs[p.site]=id;state.data.lastTabs=lastTabs;ensureLoaded(p);const owner=Object.values(state.data.storage.harnessWebsitePairs||{}).find(pair=>pair.tabId===id);if(!restoringTabs){revealedProvider={site:p.site,sessionId:owner?.sessionId||workspaceSession()};harness?.webContents.send('friday-native-focus',revealedProvider);}layout();saveTabs();};
 const fromEvent=event=>{const p=[...pages.values()].find(p=>p.view.webContents===event.sender);if(!p||event.senderFrame!==event.sender.mainFrame||siteForURL(event.senderFrame.url)!==p.site)throw Error('Untrusted Friday page sender');return p;};
 ipcMain.on('friday-native-session',(event,id)=>{if(event.sender!==harness?.webContents||event.senderFrame!==event.sender.mainFrame||!localHarness(event.senderFrame.url)||!/^session-[a-f0-9-]{36}$/i.test(id||''))return;if(state.data.nativeSessionId!==id){state.data.nativeSessionId=id;dock=null;revealedProvider=null;layout();state.save();publish();}});
 ipcMain.on('friday-reveal-provider',(event,input)=>{if(event.sender!==harness?.webContents||event.senderFrame!==event.sender.mainFrame||!localHarness(event.senderFrame.url)||input?.sessionId!==state.data.nativeSessionId||!desktopProviders.some(p=>p.id===input.site))return;revealedProvider={site:input.site,sessionId:input.sessionId};layout();});
 ipcMain.on('friday-native-diagnostic',(event,input)=>{if(event.sender!==harness?.webContents||event.senderFrame!==event.sender.mainFrame||!localHarness(event.senderFrame.url)||!['runtime-error','unhandled-rejection'].includes(input?.kind))return;diagnose('interface-'+input.kind,{message:String(input.message).replace(/token=[^\s&]+/gi,'token=[redacted]').slice(0,500)});});
 ipcMain.on('friday-native-dock',(event,input)=>{
   if(event.sender!==harness?.webContents||event.senderFrame!==event.sender.mainFrame||!localHarness(event.senderFrame.url))return;
   const checked=dockBounds(input,state.data.nativeSessionId,...win.getContentSize());if(!checked)return;
   if(!checked.visible){if(dock?.tabId===input.tabId){dock=null;layout();}return;}
   // Serialize lookup/creation; repeated ResizeObserver reports cannot create duplicate chats.
   const request={...input};dock={...request,visible:false};layout();
   dockQueue=dockQueue.then(async()=>{
     if(dock?.tabId!==request.tabId||state.data.nativeSessionId!==request.sessionId)return;
     const manager=new WebsiteTabManager(globalThis.chrome);
     const pairs=Object.values(state.data.storage.harnessWebsitePairs||{});
     const pair=pairs.find(p=>p.sessionId===request.sessionId&&p.site===request.site);
     let page=pair&&pages.get(pair.tabId);
     if(!page){
       page=[...pages.values()].find(p=>p.site===request.site&&!pairs.some(pair=>pair.tabId===p.id));
       if(!page){const tab=await create({url:pair?.url||desktopProviders.find(p=>p.id===request.site).url,active:false,lazy:true});page=pages.get(tab.id);}
       await manager.pairExisting({sessionId:request.sessionId,site:request.site},describe(page));
     }
     if(dock?.tabId!==request.tabId||state.data.nativeSessionId!==request.sessionId)return;
     activeId=page.id;selectedSite=page.site;ensureLoaded(page);
     dock={...request,pageId:page.id,visible:true,bounds:{x:checked.x,y:checked.y,width:checked.width,height:checked.height}};layout();saveTabs();
   }).catch(error=>{state.data.storage.lastStatus=error.message;publish();});
 });
 const invokeBackground=(message,sender)=>new Promise((resolve,reject)=>{let settled=false;const timer=setTimeout(()=>{if(!settled)reject(Error('Friday page message timed out'));},35000);const respond=value=>{if(settled)return;settled=true;clearTimeout(timer);resolve(value);};try{for(const fn of backgroundListeners)fn(message,sender,respond);}catch(error){clearTimeout(timer);reject(error);}});
 ipcMain.handle('friday-page-message',(event,message)=>{const p=fromEvent(event);if(!message||!pageMessageTypes.has(message.type)||JSON.stringify(message).length>2100000)throw Error('Unsupported Friday message');return invokeBackground(message,{tab:describe(p)});});
 ipcMain.handle('friday-submit',(event,input)=>{
   const p=fromEvent(event);if(!p.ready||p.assignedJob!==input.id)throw Error('Unowned desktop submission');
   const {width,height}=p.view.getBounds();
   // Persist admission first. The isolated preload clicks the verified Send
   // control once; it does not require OS focus or expose the provider page.
   return submitOnce(state,{tabId:p.id,origin:new URL(event.senderFrame.url).origin,jobId:input.id,x:input.x,y:input.y,width,height},()=>{});
 });
 ipcMain.on('friday-receipts',(event,input)=>{try{const p=fromEvent(event),origin=new URL(event.senderFrame.url).origin;if(input?.action==='read')event.returnValue=state.receipts(p.id,origin);else{state.receipt(p.id,origin,input.key,input.value);event.returnValue={ok:true};}}catch{event.returnValue={ok:false};}});
 ipcMain.on('friday-command-result',(event,{nonce,result}={})=>{let p;try{p=fromEvent(event);}catch{return;}const call=pending.get(nonce);if(call?.id===p.id){clearTimeout(call.timer);pending.delete(nonce);call.resolve(result);}});
 const sendMessage=(id,message)=>new Promise((resolve,reject)=>{const p=pages.get(id);if(p)ensureLoaded(p);if(!p||!p.ready)return reject(Error('Receiving end does not exist; page loading.'));if(message.type==='harness-run')p.assignedJob=message.id;if(message.type==='harness-cancel'&&p.assignedJob===message.id)p.assignedJob=null;const nonce=randomUUID(),timer=setTimeout(()=>{pending.delete(nonce);reject(Error('Desktop page listener timed out'));},35000);pending.set(nonce,{id,resolve,reject,timer});p.view.webContents.send('friday-command',{nonce,message});});
 const protect=(wc,site)=>{
   const permitted=url=>navigationAllowed(url)&&(!siteForURL(url)||siteForURL(url)===site);
   wc.on('will-navigate',(event,url)=>{if(!permitted(url))event.preventDefault();});
   wc.on('will-redirect',(event,url)=>{if(!permitted(url))event.preventDefault();});
   wc.setWindowOpenHandler(({url})=>permitted(url)?{action:'allow',overrideBrowserWindowOptions:{title:'Friday · Sign in',webPreferences:{session:wc.session,contextIsolation:true,nodeIntegration:false,sandbox:true}}}:{action:'deny'});
   wc.on('did-create-window',popup=>protect(popup.webContents,site));
 };
 const ensureLoaded=p=>{if(p.loadingStarted)return;p.loadingStarted=true;void p.view.webContents.loadURL(p.lastChatURL).catch(()=>{p.loadingStarted=false;state.data.storage.lastStatus='Website could not load. Inspect its page before retrying; no prompt was submitted.';publish();});};
 const create=async({url='https://chatgpt.com/',id,active=true,lazy=false}={})=>{
   const site=siteForURL(url);if(!site)throw Error('Unsupported provider website');
   id??=Math.max(0,...pages.keys())+1;
   const view=new WebContentsView({webPreferences:{session:getProfile(site),preload:join(here,'provider-preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,backgroundThrottling:false,focusOnNavigation:false}});
   const p={id,site,view,ready:false,lastChatURL:providerURL(url),loadingStarted:false};pages.set(id,p);view.setBounds({x:0,y:0,width:1100,height:800});view.setVisible(true);win.contentView.addChildView(view);layout();protect(view.webContents,site);
   view.webContents.on('did-start-navigation',(_e,_url,_inPlace,main)=>{if(main&&!_inPlace)p.ready=false;});
   view.webContents.on('did-navigate-in-page',()=>{const value=providerURL(view.webContents.getURL(),site);if(value){p.lastChatURL=value;updated.emit(id,{url:value},describe(p));saveTabs();}});
   view.webContents.on('did-navigate',()=>{const value=providerURL(view.webContents.getURL(),site);if(value){p.lastChatURL=value;updated.emit(id,{url:value},describe(p));saveTabs();}});
   view.webContents.on('page-title-updated',publish);
   const keepRunning=()=>{view.webContents.setBackgroundThrottling(false);diagnose('provider-background-ready',{site:p.site,tabId:p.id});};
   view.webContents.on('dom-ready',keepRunning);view.webContents.on('did-finish-load',keepRunning);
   view.webContents.on('render-process-gone',(_event,details)=>{
     p.ready=false;diagnose('provider-renderer-gone',{site:p.site,tabId:p.id,reason:details.reason,exitCode:details.exitCode});
     if(p.assignedJob){void bridge('/event',{id:p.assignedJob,type:'error',message:'The provider renderer stopped. Review the saved chat and completed tool results before continuing; no prompt or action was replayed.'}).catch(()=>{});p.assignedJob=null;}
     state.data.storage.lastStatus='Provider page stopped. Restoring its saved chat without replaying the request.';publish();
     if(!closing&&recoveryBudget.admit('provider:'+p.id))setTimeout(()=>{
       if(closing||view.webContents.isDestroyed())return;
       const target=recoveryTarget(view.webContents.getURL(),p.lastChatURL,url=>!!providerURL(url,p.site));
       if(target)void view.webContents.loadURL(target).catch(error=>diagnose('provider-restore-failed',{site:p.site,code:error.code}));
     },1000);
   });
   view.webContents.on('preload-error',(_event,_path,error)=>diagnose('provider-preload-error',{site:p.site,message:String(error.message).slice(0,300)}));
   if(active)focus(id);else{if(!lazy)ensureLoaded(p);layout();saveTabs();}return describe(p);
 };
 ipcMain.on('friday-page-ready',event=>{let p;try{p=fromEvent(event);}catch{return;}if(p.ready)return;
   p.view.webContents.setBackgroundThrottling(false);
   const scripts=['provider-catalog.js','turns.js','transfers.js','two-way.js','content.js'].map(name=>({code:fs.readFileSync(join(extension,name),'utf8'),url:'friday-local://'+name}));
   void p.view.webContents.executeJavaScriptInIsolatedWorld(999,scripts).then(()=>{p.ready=true;publish();}).catch(()=>{state.data.storage.lastStatus='Page connector failed to initialize';publish();});
 });
 function onDownload(_event,item,wc){
   const p=[...pages.values()].find(p=>p.view.webContents===wc);if(!p||!providerURL(wc.getURL(),p.site)){item.cancel();return;}
   const filename=basename(item.getFilename()).replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,180)||'download';
   const directory=join(homedir(),'Downloads','FridayDesktop',randomUUID());fs.mkdirSync(directory,{recursive:true});const path=join(directory,filename);item.setSavePath(path);
   const record={id:nextDownload++,filename:path,startTime:new Date().toISOString(),referrer:wc.getURL(),url:item.getURL(),state:'in_progress',fileSize:0};downloads.set(record.id,record);downloadCreated.emit({...record});
   item.once('done',(_event,status)=>{record.state=status==='completed'?'complete':'interrupted';record.fileSize=status==='completed'?fs.statSync(path).size:0;downloadChanged.emit({id:record.id,state:{current:record.state}});});
 }
 const storage={
   get:async query=>typeof query==='string'?{[query]:state.data.storage[query]}:{...query,...state.data.storage},
   set:async values=>{Object.assign(state.data.storage,values);state.save();changed.emit(values,'local');publish();},
   remove:async key=>{delete state.data.storage[key];state.save();}
 };
 globalThis.chrome={runtime:{getManifest:()=>JSON.parse(fs.readFileSync(join(extension,'manifest.json'),'utf8')),getURL:()=> 'friday-desktop://config',onMessage:{addListener:fn=>backgroundListeners.push(fn)},reload:()=>{}},storage:{local:storage,onChanged:changed},
   fridayDesktop:{backgroundExecution:true,revealTab:async id=>focus(id)},
   tabs:{query:async query=>[...pages.values()].map(describe).filter(t=>(!query.active||t.active)&&(!query.url||t.url.startsWith(query.url.replace(/\*$/,'')))),get:async id=>{if(!pages.has(id))throw Error('No tab with id');return describe(pages.get(id));},create,update:async(id,_opts)=>{const p=pages.get(id);if(!p)throw Error('No tab with id');ensureLoaded(p);return describe(p);},reload:async id=>{const p=pages.get(id);if(!p)throw Error('No tab with id');p.ready=false;p.view.webContents.reload();},sendMessage,onUpdated:updated,onRemoved:removed},
   windows:{update:async()=>{}},permissions:{contains:async()=>true},downloads:{onCreated:downloadCreated,onChanged:downloadChanged,search:async({id})=>downloads.has(id)?[{...downloads.get(id)}]:[]},
   action:{setBadgeText:async()=>{}},alarms:{create:()=>{},onAlarm:new Signal()}};
 globalThis.fetch=async(url,options)=>{
   if(url==='friday-desktop://config')return Promise.resolve(new Response(JSON.stringify({token:connection.token,developmentAutoReload:false})));
   if(url==='http://127.0.0.1:8766/poll')options={...options,body:JSON.stringify({...JSON.parse(options.body),transport:'desktop',clientId:state.data.clientId})};
   const response=await nativeFetch(url,options);
   if(url==='http://127.0.0.1:8766/poll'&&response.status===409&&!closing){
     // Backend restart lost the in-memory lease. Reclaim only through its
     // idle/owner guard; retry the poll, never a submission or tool event.
     try{await bridge('/desktop/claim',{clientId:state.data.clientId});return nativeFetch(url,options);}catch{}
   }
   return response;
 };
 // Desktop owns a separate pairing map and never imports Chrome's tab IDs.
 state.data.storage.enabled??=true;state.data.storage.sites??=['chatgpt-web'];state.save();
 await win.loadFile(join(here,'shell.html'));
 harness=new WebContentsView({webPreferences:{partition:'persist:friday-harness',preload:join(here,'harness-preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,webviewTag:true}});win.contentView.addChildView(harness);
 const browserGuests=new DesktopBrowserGuests(()=> 'http://127.0.0.1:3030');
 browserGuests.bind(harness.webContents);
 const nativeBrowserSender=event=>{if(event.sender!==harness.webContents||event.senderFrame!==harness.webContents.mainFrame||!localHarness(event.senderFrame.url))throw Error('Untrusted native Browser sender');};
 setupFlow=new FirstRunSetup({state,existing:existingInstallation,
  disable:async site=>{state.data.storage.sites=(state.data.storage.sites||[]).filter(value=>value!==site);state.save();},
  complete:(site,id)=>bridge('/desktop/setup-default',{clientId:state.data.clientId,site,id}),
  open:async site=>{
   const pairedIds=new Set(Object.values(state.data.storage.harnessWebsitePairs||{}).filter(p=>p.sessionId!==setupSession(state.data.clientId,site)).map(p=>p.tabId));
   let page=[...pages.values()].find(p=>p.site===site&&!pairedIds.has(p.id));
   if(!page){const tab=await create({url:desktopProviders.find(p=>p.id===site).url,active:false});page=pages.get(tab.id);}
   ensureLoaded(page);setupFlow.pageId=page.id;setupDock=null;layout();
  },
  test:async(site,id)=>{
   const page=pages.get(setupFlow.pageId);if(!page?.ready)throw Error('The website is still loading. Finish sign-in or verification on the right, then test again. No test message was sent.');
   const sessionId=setupSession(state.data.clientId,site);
   const manager=new WebsiteTabManager(globalThis.chrome);
   await manager.pairExisting({sessionId,site},describe(page));
   const sites=new Set(state.data.storage.sites||[]);sites.add(site);state.data.storage.sites=[...sites];state.save();
   let result=await bridge('/desktop/setup-test',{clientId:state.data.clientId,site,id});
   for(let i=0;result.status==='running'&&i<130;i++){
    await new Promise(resolve=>setTimeout(resolve,1000));
    const response=await nativeFetch(`http://127.0.0.1:8766/desktop/setup-test/${id}`,{headers:{Authorization:`Bearer ${connection.token}`,'X-Friday-Client':state.data.clientId},signal:AbortSignal.timeout(10000)});
    result=await response.json();if(!response.ok)throw Error(result.error);
   }
   if(result.status==='running')throw Error('Still awaiting the test reply. Inspect the provider chat before starting another test.');
   return result;
  }});
 ipcMain.handle('friday-onboarding',async(event,input)=>{
  nativeBrowserSender(event);
  if(input?.action!=='status'&&(await bridge('/status')).pending)throw Error('Finish the active Friday task first.');
  const result=await setupFlow.action(input);
  if(setupFlow.visible&&result.site&&!setupFlow.pageId)await setupFlow.open(result.site);
  if(!setupFlow.visible)setupDock=null;layout();return result;
 });
 ipcMain.on('friday-onboarding-dock',(event,input)=>{
  nativeBrowserSender(event);if(!setupFlow.visible||!setupFlow.pageId)return;
  const [width,height]=win.getContentSize();const {x,y,width:w,height:h}=input||{};
  if(![x,y,w,h].every(Number.isFinite)||x<0||y<0||w<1||h<1||x+w>width+1||y+h>height+1)return;
  setupDock={visible:true,pageId:setupFlow.pageId,bounds:{x:Math.ceil(x),y:Math.ceil(y),width:Math.max(1,Math.floor(w)-1),height:Math.max(1,Math.floor(h)-1)}};layout();
 });
 ipcMain.handle('friday-native-browser-acquire',(event,workspace)=>{nativeBrowserSender(event);return browserGuests.acquire(event.sender,workspace);});
 ipcMain.handle('friday-native-browser-release',(event,lease)=>{nativeBrowserSender(event);return browserGuests.release(event.sender,lease);});
 const taskRequests=new Map();
 ipcMain.on('friday-task-browser-register',(event,input)=>{
   nativeBrowserSender(event);
   const lease=[...browserGuests.leases.values()].find(l=>l.owner===event.sender&&l.guest?.id===input?.guestId);
   if(!lease||typeof input.tabId!=='string'||!/^session-[a-f0-9-]{36}$/i.test(input.sessionId||''))return;
   if(lease.sessionId&&lease.sessionId!==input.sessionId)return;
   const changed=lease.sessionId!==input.sessionId||lease.tabId!==input.tabId;
   lease.sessionId=input.sessionId;lease.tabId=input.tabId;if(changed)browserGuests.notify();
 });
 ipcMain.on('friday-task-browser-result',(event,input)=>{nativeBrowserSender(event);const request=taskRequests.get(input?.nonce);if(request){taskRequests.delete(input.nonce);clearTimeout(request.timer);input.ok?request.resolve():request.reject(Error(input.error||'Native Browser request failed.'));}});
 const nativeTaskRequest=input=>new Promise((resolve,reject)=>{
   const nonce=randomUUID(),timer=setTimeout(()=>{taskRequests.delete(nonce);reject(Error('Native Browser UI did not respond. No browser action was replayed.'));},15000);
   taskRequests.set(nonce,{resolve,reject,timer});harness.webContents.send('friday-task-browser',{...input,nonce});
 });
 const taskRelay=await startTaskBrowserRelay({guests:browserGuests,file:join(homedir(),'.dsh/browser-connector/desktop-browser-control.json'),connect:async input=>{
   if(input.sessionId!==state.data.nativeSessionId)throw Error('Select this Friday conversation before controlling its native Browser.');
   if(typeof input.directory!=='string')throw Error('A workspace directory is required.');
   const normalize=directory=>{const value=realpathSync(directory);return process.platform==='win32'?value.toLowerCase():value;};
   const directory=normalize(input.directory),workspace='cwd:'+directory;
   const matches=()=>[...browserGuests.leases.values()].filter(l=>l.workspace.startsWith('cwd:')&&normalize(l.workspace.slice(4))===directory&&l.sessionId===input.sessionId&&l.guest&&!l.guest.isDestroyed());
   const open=async options=>{
     if(state.data.nativeSessionId!==input.sessionId)throw Error('The active Friday conversation changed. No action was replayed.');
     const previous=new Set(matches().map(l=>l.guest.id));
     const guestId=options.closeGuestId||options.focusGuestId;
     if(guestId){const lease=matches().find(l=>l.guest.id===guestId);if(!lease)throw Error('Unknown native task tab.');await nativeTaskRequest({sessionId:input.sessionId,tabId:lease.tabId,action:options.closeGuestId?'close':'focus'});if(options.focusGuestId)lease.guest.focus();return lease;}
     const existing=!options.fresh&&matches()[0];
     if(existing){await nativeTaskRequest({sessionId:input.sessionId,tabId:existing.tabId,action:'focus'});return existing;}
     await nativeTaskRequest({sessionId:input.sessionId,action:'open',fresh:!!options.fresh,url:options.url||'https://example.com/'});
     for(let i=0;i<150;i++){const lease=matches().find(l=>!previous.has(l.guest.id));if(lease)return lease;await new Promise(resolve=>setTimeout(resolve,100));}
     throw Error('The native Browser tab has not attached yet. No tool action was replayed.');
   };
   const first=await open({});
   // Use the exact upstream workspace spelling for partition/lease selection.
   return {workspace:first.workspace,directory,sessionId:input.sessionId,open,validate:()=>{if(state.data.nativeSessionId!==input.sessionId)throw Error('The active Friday conversation changed. Select the task conversation to continue.');}};
 }});
 harness.setBackgroundColor('#202023');
 const theme=fridayTheme({webContents:harness.webContents,
   css:()=>fs.readFileSync(join(here,'../friday.css'),'utf8'),allowed:localHarness,
   onError:error=>diagnose('theme-error',{message:String(error.message).slice(0,200)})});
 const interfaceStatus=(message,recovering)=>win.webContents.send('friday-interface-status',{message,recovering});
 const restoreHarness=async()=>{
   if(closing||harness.webContents.isDestroyed())return;
   harnessHealthy=false;dock=null;layout();interfaceStatus('Restoring Friday’s interface. Existing tasks are not resent.',true);
   const target=recoveryTarget(harness.webContents.getURL(),login,localHarness);
   try{if(!target)throw Error('No saved local Harness address');await harness.webContents.loadURL(target);}
   catch(error){diagnose('interface-restore-failed',{code:error.code});interfaceStatus('Friday could not restore its interface. Check that the Harness server is running, then try again.',false);}
 };
 ipcMain.handle('friday-restore-interface',event=>{
   if(event.sender!==win.webContents||event.senderFrame!==win.webContents.mainFrame||event.senderFrame.url!==shellURL)throw Error('Untrusted recovery sender');
   return restoreHarness();
 });
 harness.webContents.on('render-process-gone',(_event,details)=>{
   diagnose('interface-renderer-gone',{reason:details.reason,exitCode:details.exitCode});harnessHealthy=false;dock=null;layout();
   const retry=!closing&&recoveryBudget.admit('interface');
   interfaceStatus(retry?'Friday’s interface stopped. Restoring saved tabs…':'Friday’s interface stopped repeatedly. Use Restore interface to try again.',retry);
   if(retry)setTimeout(()=>void restoreHarness(),1000);
 });
 harness.webContents.on('did-finish-load',()=>{harnessHealthy=localHarness(harness.webContents.getURL());layout();if(harnessHealthy)diagnose('interface-loaded');});
 harness.webContents.on('did-fail-load',(_event,code,_description,_url,main)=>{if(!main||code===-3)return;diagnose('interface-load-failed',{code});harnessHealthy=false;dock=null;layout();interfaceStatus('Friday could not load its interface. Check the Harness server, then choose Restore interface.',false);});
 harness.webContents.on('preload-error',(_event,_path,error)=>diagnose('interface-preload-error',{message:String(error.message).slice(0,300)}));
 harness.webContents.on('did-start-navigation',(_event,_url,inPlace,main)=>{if(main&&!inPlace){dock=null;layout();}});
 harness.webContents.on('will-navigate',(event,url)=>{if(!localHarness(url))event.preventDefault();});harness.webContents.setWindowOpenHandler(()=>({action:'deny'}));
 const logs=join(homedir(),'.dsh/logs'),latest=fs.readdirSync(logs).filter(n=>/^browser-.*\.out\.log$/.test(n)).sort((a,b)=>fs.statSync(join(logs,b)).mtimeMs-fs.statSync(join(logs,a)).mtimeMs)[0];
 const login=latest&&fs.readFileSync(join(logs,latest),'utf8').match(/http:\/\/127\.0\.0\.1:3030\/\?token=[^\s]+/)?.[0];
 if(!login)throw Error('Start the existing Friday Harness server first');
 void harness.webContents.loadURL(login).catch(()=>{state.data.storage.lastStatus='Friday could not load. Wait for Harness and click Reconnect Friday.';publish();});
 const savedTabs=[...state.data.tabs],restoreActive=activeId;for(const tab of savedTabs.filter(t=>providerURL(t.url)))await create({...tab,active:false,lazy:true});
 if(!pages.size)await create();else focus(pages.has(restoreActive)?restoreActive:[...pages.keys()].at(-1));
 restoringTabs=false;layout();saveTabs();
 // Refresh appearance without navigating, touching profiles, or resending tasks.
 Menu.setApplicationMenu(Menu.buildFromTemplate([{label:'View',submenu:[
   {label:'Models',click:()=>harness.webContents.send('friday-onboarding-show')},
   {label:'Reload appearance',accelerator:'CommandOrControl+Shift+F12',click:()=>void theme.apply()},
   {type:'separator'},{role:'togglefullscreen'}
 ]}]));win.setAutoHideMenuBar(true);win.setMenuBarVisibility(false);
 win.on('resize',layout);layout();publish();
 win.on('close',event=>{if(closing)return;event.preventDefault();void(async()=>{closing=true;try{await bridge('/desktop/release',{clientId:state.data.clientId});taskRelay.close();await browserGuests.flush();for(const profile of profiles.values()){await profile.cookies.flushStore();profile.flushStorageData();}saveTabs();await bundledBackend?.close?.();for(const p of pages.values())p.view.webContents.close();harness.webContents.close();app.quit();}catch(error){closing=false;dialog.showMessageBox(win,{type:'info',message:'Finish or cancel the active Friday task before closing.',detail:error.message});}})();});
 app.on('second-instance',()=>{win.show();win.focus();});
 await import('../extension/background.js');
}
