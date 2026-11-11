import { WebsiteTabManager, waitForWebsiteTab,browserRead } from './tab-manager.js';
import { DevelopmentUpdater } from './development-update.js';
import { BrowserDownloadWatch } from './download-watch.js';
const BASE = 'http://127.0.0.1:8766';
const tabManager = new WebsiteTabManager(chrome);
const running = new Map();
let polling = false;
let updateRestored = false;
let configPromise;
let lastListeners = [];
let bridgeOnline = false; let bridgeHeartbeatAt = 0;
let publishing = false;
async function pairedFor(action){
  const pairs=(await tabManager.bindings()).filter(p=>p.site===action.site&&(!action.sessionId||p.sessionId===action.sessionId));
  if(typeof tabManager.lookup==='function'){
    for(const pair of pairs.reverse()){const tab=await tabManager.lookup(pair);if(tab)return {...pair,tabId:tab.id};}
    return;
  }
  if(action.sessionId)return pairs.at(-1);
  for(const pair of pairs.reverse())try{const tab=await browserRead(()=>chrome.tabs.get(pair.tabId)),url=new URL(tab.url);if(url.origin+url.pathname===pair.url)return pair;}catch(error){if(error.code==='FRIDAY_BROWSER_READ_TIMEOUT')throw error;}
}
function publishInBackground(listeners, online) {
  if(publishing)return;
  publishing=true;
  void publishConnection(listeners,online).catch(()=>{}).finally(()=>{publishing=false;});
}
const listenerKey = 'harnessListenerState';
async function publishConnection(listeners, online) {
  const saved = (await chrome.storage.local.get(listenerKey))[listenerKey] || {};
  let changed = false;
  for (const listener of listeners) {
    try {
      const tab = await chrome.tabs.get(listener.tabId);
      const url = new URL(tab.url);
      if (url.origin + url.pathname !== listener.url) continue;
      await chrome.tabs.sendMessage(listener.tabId, { type: 'harness-listen', config: {
        ...listener, online, status: online ? listener.status : 'Harness is offline — waiting to reconnect. Local tools cannot run.',
      } });
      const previous = saved[listener.sessionId] || {};
      let notice = previous.notice || null;
      if (listener.enabled && (!online && notice !== 'offline' || online && notice === 'offline')) {
        const result = await chrome.tabs.sendMessage(listener.tabId, { type: 'harness-connection-notice', url: listener.url, online });
        if (result?.sent) notice = online ? null : 'offline';
      }
      const next = { ...listener, notice };
      if (JSON.stringify(previous) !== JSON.stringify(next)) { saved[listener.sessionId] = next; changed = true; }
    } catch {}
  }
  if (changed) await chrome.storage.local.set({ [listenerKey]: saved });
}
const config = () => configPromise ||= fetch(chrome.runtime.getURL('bridge-config.json')).then(r => r.json());
const updater=new DevelopmentUpdater(chrome,{enabled:async()=>(await config()).developmentAutoReload===true,
  // Chrome caches unpacked extension resources, including manifest.json.
  // The authenticated loopback bridge reads the fully installed version afresh.
  readManifest:async()=>({version:(await request('/status')).availableExtensionVersion}),
  bindings:()=>tabManager.bindings()});
const downloadWatch=new BrowserDownloadWatch(chrome,{isActive:id=>running.has(id),importFile:(job,input)=>request('/download-file',{jobId:job.id,...input})});

async function request(path, body) {
  const connection = await config();
  const response = await fetch(BASE + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${connection.token}`, 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    signal: AbortSignal.timeout(30000),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Bridge HTTP ${response.status}`);
  return result;
}

async function run(command) {
  // Reserve before the first await. A slow tab acquisition must not appear to
  // the bridge as a lost worker and trigger a second run of the same request.
  let finish;const finished=new Promise(resolve=>{finish=resolve;});
  running.set(command.id, { tabId: null, site: command.site,sessionId:command.sessionId,finish });
  let tab; let navigationUrl; let binding;
  try { ({ tab, navigationUrl, binding } = await tabManager.acquire(command)); }
  catch (error) {
    await request('/event', { id: command.id, type: 'error', message: String(error.message).slice(0, 1800) }).catch(() => {});
    running.delete(command.id);
    return;
  }
  if(!running.has(command.id))return;
  if([...running.entries()].some(([id,job])=>id!==command.id&&job.tabId===tab.id)){
    running.delete(command.id);
    await request('/event',{id:command.id,type:'error',message:'This provider tab is already owned by another active request. No prompt was submitted.'}).catch(()=>{});return;
  }
  const pageCommand={type:'harness-run',id:command.id,streamEvents:true,resume:command.resume,purpose:command.purpose,site:command.site,prompt:command.prompt,attachments:command.attachments||[],timeoutMs:command.timeoutMs,externalMessageId:command.externalMessageId};
  running.set(command.id, { tabId: tab.id, site: command.site,sessionId:command.sessionId,finish,pageCommand,recoveryUrl:command.conversationUrl||binding?.url });
  await request('/event', { id: command.id, type: 'binding', ...binding }).catch(() => {});
  await chrome.storage.local.set({ lastStatus: `Using the managed ${command.site} tab; log in there if asked.` });
  try {
    await request('/event',{id:command.id,type:'status',state:'reconnecting'}).catch(()=>{});
    const ready = await waitForWebsiteTab(chrome, tab.id, { navigationUrl, isActive: () => running.has(command.id),onUnresponsive:async()=>{
      if(chrome.fridayDesktop?.backgroundExecution)return;
      const current=await tabManager.lookup(binding);
      if(!current||current.id!==tab.id||!running.has(command.id))return;
      await chrome.tabs.update(tab.id,{active:true});
      if(current.windowId!==undefined&&running.has(command.id))await chrome.windows.update(current.windowId,{focused:true});
    } });
    if (!running.has(command.id)) return;
    if (!ready) throw new Error('The paired website did not respond. Open its tab and wait for the chat editor, then retry. Sign in only if the website requires it. No prompt was submitted.');
    // A lost/rejected start port is not proof that the page did not start.
    // Retain admission until a job-owned terminal event or backend cancellation;
    // never resend the command to resolve that uncertainty.
    const startRequest=Promise.resolve().then(()=>chrome.tabs.sendMessage(tab.id,pageCommand)).catch(()=>finished);
    let result = await Promise.race([finished,startRequest]);
    if(result?.ok&&result.started)result=await finished;
    if (!result?.ok && running.has(command.id)) throw new Error(result?.error || 'Website connector stopped unexpectedly.');
    if (result?.ok && running.has(command.id)) await tabManager.complete(tab.id, command.prompt.length);
  } catch (error) {
    await tabManager.failed(tab.id);
    if (running.has(command.id)) await request('/event', { id: command.id, type: 'error', message: String(error.message).slice(0, 1800) }).catch(() => {});
    await chrome.storage.local.set({ lastStatus: error.message });
  } finally { running.delete(command.id); downloadWatch.cancel(command.id); }
}

async function poll() {
  if (polling || !updateRestored) return;
  polling = true;
  try {
    const settings = await chrome.storage.local.get({ enabled: true, sites: Object.keys(globalThis.FridayProviderCatalog) });
    const result = await request('/poll', { version: chrome.runtime.getManifest().version,runningIds:[...running.keys()], sites: settings.enabled ? settings.sites : [], bindings: (await tabManager.bindings()).filter(pair => Number.isInteger(pair.tabId)) });
    bridgeOnline = true; bridgeHeartbeatAt = Date.now();
    lastListeners = (result.listeners || []).map(listener => ({ ...listener,
      enabled: !!settings.enabled && listener.enabled && settings.sites.includes(listener.site) }));
    for (const [id, job] of running) {
      if (!result.activeIds.includes(id) || !settings.enabled || !settings.sites.includes(job.site)) {
        running.delete(id);
        job.finish?.({ok:true,cancelled:true});
        downloadWatch.cancel(id);
        if(Number.isInteger(job.tabId))void chrome.tabs.sendMessage(job.tabId, { type: 'harness-cancel', id }).catch(() => {});
        if (result.activeIds.includes(id)) await request('/event', { id, type: 'error', message: 'Website connection disabled in extension popup.' }).catch(() => {});
      }
      else if(Number.isInteger(job.tabId)&&!job.pulsePending){
        job.pulsePending=true;
        void browserRead(()=>chrome.tabs.sendMessage(job.tabId,{type:'harness-pulse',id}),1500).then(async page=>{
          // A freshly reloaded page can resume only a persisted submitted turn.
          // Never repeat Send, upload files, or navigate to resolve uncertainty.
          if(page?.ok!==false||page.busy||!page.resumeAvailable||job.resuming||job.site!=='chatgpt-web'||job.pageCommand?.purpose!=='task'||job.pageCommand.externalMessageId||!job.recoveryUrl||running.get(id)!==job)return;
          let current;try{current=new URL(page.url);if(current.origin+current.pathname!==job.recoveryUrl)return;}catch{return;}
          job.resuming=true;
          try{
            await request('/event',{id,type:'status',state:'reconnecting'});
            if(running.get(id)!==job)return;
            await browserRead(()=>chrome.tabs.sendMessage(job.tabId,{...job.pageCommand,resume:true}),1500);
          }finally{job.resuming=false;}
        })
          .catch(()=>{}).finally(()=>{job.pulsePending=false;});
      }
    }
    for (const command of result.commands) {
      if(running.has(command.id))continue;
      if (running.size<2&&! [...running.values()].some(job=>job.sessionId===command.sessionId)) void run(command);
      // Leave excess dispatch unacknowledged; the backend retains its owned
      // request and re-offers it after recovery grace, never submits it here.
    }
    // A frozen listener tab must not hold up dispatch or cancellation polling.
    publishInBackground(lastListeners, true);
    for(const action of result.actions||[]){
      if(action.type==='pair-site'&&!running.size&&action.sessionId&&Object.hasOwn(globalThis.FridayProviderCatalog,action.site)){
        void (async()=>{const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true});if(running.size)return;await tabManager.pairExisting(action,tab);await chrome.storage.local.set({lastStatus:'Active provider tab paired with the selected Friday conversation.'});})().catch(error=>chrome.storage.local.set({lastStatus:error.message}));
      }
      if(action.type==='refresh-site'&&!running.size&&Object.hasOwn(globalThis.FridayProviderCatalog,action.site)){
        void (async()=>{
          const pair=await pairedFor(action);if(!pair)return;
          const tab=await chrome.tabs.get(pair.tabId),url=new URL(tab.url);if(url.origin+url.pathname!==pair.url)return;
          const page=await updater.probe(pair.tabId);
          if(page?.hasDraft===false&&page.isGenerating===false&&!running.size)await chrome.tabs.reload(pair.tabId);
        })().catch(()=>{});
      }
      if(action.type==='probe-site'&&Object.hasOwn(globalThis.FridayProviderCatalog,action.site)){
        void (async()=>{
          let pair,page,probeStatus='no-paired-tab';try{pair=await pairedFor(action);if(pair){if(typeof tabManager.lookup!=='function')await browserRead(()=>chrome.tabs.get(pair.tabId));page=await updater.probe(pair.tabId);probeStatus=page?'responded':'empty-response';}}catch(error){probeStatus=/no tab|invalid tab/i.test(error.message)?'missing-tab':/receiving end|connection/i.test(error.message)?'listener-missing':/unavailable|timeout|timed out/i.test(error.message)?'probe-timeout':'probe-failed';}
          await request('/provider-health',{site:action.site,scopeSession:action.sessionId||null,probeStatus,page:page?{provider:page.provider,hasEditor:page.hasEditor,isGenerating:page.isGenerating}:undefined,notOpen:probeStatus==='no-paired-tab'||probeStatus==='missing-tab'});
        })().catch(()=>{});
      }
      if(action.type==='focus')void tabManager.focus(action).catch(()=>{});
      if(action.type==='configure-site'&&Object.hasOwn(globalThis.FridayProviderCatalog,action.site)&&typeof action.enabled==='boolean'){
        const previous=await chrome.storage.local.get({enabled:true,sites:Object.keys(globalThis.FridayProviderCatalog)});
        const sites=new Set(previous.sites||[]);if(action.enabled)sites.add(action.site);else sites.delete(action.site);
        await chrome.storage.local.set({enabled:sites.size>0,sites:[...sites],lastStatus:'Connection settings updated from Harness Models.'});
      }
    }
    void updater.check(()=>running.size>0||result.activeIds.length>0||result.commands.length>0||result.queuedRequests>0);
    await chrome.action.setBadgeText({ text: settings.enabled ? 'ON' : '' });
  } catch (error) {
    bridgeOnline = false;
    if (!lastListeners.length) lastListeners = Object.values((await chrome.storage.local.get(listenerKey))[listenerKey] || {});
    const settings = await chrome.storage.local.get({ enabled: true, sites: Object.keys(globalThis.FridayProviderCatalog) });
    publishInBackground(lastListeners.map(listener => ({ ...listener,
      enabled: !!settings.enabled && listener.enabled && settings.sites.includes(listener.site) })), false);
    await chrome.action.setBadgeText({ text: 'OFF' });
    await chrome.storage.local.set({ lastStatus: `Bridge unavailable: ${error.message}` });
  } finally { polling = false; }
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if(['harness-download-watch','harness-download-result'].includes(message.type)){
    const job=running.get(message.jobId);
    if(!job||job.tabId!==sender.tab?.id){respond({ok:false,error:'Unowned download job.'});return;}
    (message.type==='harness-download-watch'?downloadWatch.arm({id:message.jobId},sender.tab,message.name):downloadWatch.wait(message.watchId,message.jobId))
      .then(result=>respond({ok:true,...(message.type==='harness-download-watch'?result:{file:result})})).catch(error=>respond({ok:false,error:error.message}));return true;
  }
  if(message.type==='harness-job-file'){
    const job=running.get(message.jobId);if(!job||job.tabId!==sender.tab?.id){respond({ok:false,error:'Unowned file job.'});return;}
    request('/job-file',{jobId:message.jobId,id:message.id,index:message.index}).then(result=>respond({ok:true,result})).catch(error=>respond({ok:false,error:error.message}));return true;
  }
  if(message.type==='harness-file-transfer'){
    (async()=>{
      if(!['begin','chunk','finish'].includes(message.action))throw new Error('Invalid transfer operation.');
      const settings=await chrome.storage.local.get({enabled:true,sites:Object.keys(globalThis.FridayProviderCatalog)});
      if(!settings.enabled||!settings.sites.includes('chatgpt-web'))throw new Error('Enable the paired ChatGPT connection first.');
      const binding=(await tabManager.bindings()).find(pair=>pair.tabId===sender.tab?.id&&pair.site==='chatgpt-web');
      if(!binding||!sender.tab?.url)throw new Error('No paired file destination.');
      if(message.jobId&&running.get(message.jobId)?.tabId!==sender.tab.id)throw new Error('Unowned file job.');
      const result=await request('/files/'+message.action,{...message.input,sessionId:binding.sessionId,site:binding.site,tabId:sender.tab.id,url:sender.tab.url,jobId:message.jobId});
      return {ok:true,result};
    })().then(respond).catch(error=>respond({ok:false,error:error.message}));return true;
  }
  if (message.type === 'harness-listener-refresh') {
    (async () => {
      const settings = await chrome.storage.local.get({ enabled: true, sites: Object.keys(globalThis.FridayProviderCatalog) });
      const listener = lastListeners.find(item => item.tabId === sender.tab?.id && item.site === 'chatgpt-web');
      if (!listener || !sender.tab?.url) return { ok: false };
      const url = new URL(sender.tab.url);
      if (url.origin + url.pathname !== listener.url) return { ok: false };
      const online = bridgeOnline && Date.now() - bridgeHeartbeatAt < 15000;
      return { ok: true, config: { ...listener, online,
        enabled: !!settings.enabled && listener.enabled && settings.sites.includes(listener.site),
        status: online ? listener.status : 'Harness is offline — waiting to reconnect. Local tools cannot run.' } };
    })().then(respond).catch(() => respond({ ok: false }));
    return true;
  }
  if (['harness-web-message', 'harness-web-stop'].includes(message.type)) {
    (async () => {
      const settings = await chrome.storage.local.get({ enabled: true, sites: Object.keys(globalThis.FridayProviderCatalog) });
      const binding = (await tabManager.bindings()).find(pair => pair.tabId === sender.tab?.id && pair.site === 'chatgpt-web');
      if (!settings.enabled || !settings.sites.includes('chatgpt-web') || !binding || !sender.tab?.url) throw new Error('No enabled paired ChatGPT connection.');
      return request(message.type === 'harness-web-stop' ? '/inbound/stop' : '/inbound', {
        sessionId: binding.sessionId, site: binding.site, tabId: sender.tab.id, url: sender.tab.url,
        id: message.id, text: message.text, jobId: message.jobId, fileIds:message.fileIds,
      });
    })().then(result => respond(result)).catch(error => respond({ ok: false, error: error.message }));
    return true;
  }
  if (message.type === 'connector-status' && !sender.tab) {
    request('/status').then(status => respond({ ok: true, ...status })).catch(error => respond({ ok: false, error: error.message }));
    return true;
  }
  if (message.type === 'connector-wake' && !sender.tab) { void poll(); respond({ ok: true }); return; }
  if (message.type !== 'harness-event') return;
  const job = running.get(message.event?.id);
  if (!job || sender.tab?.id !== job.tabId) { respond({ ok: false, error: 'Unowned browser job.' }); return; }
  request('/event', message.event).then(async () => {
    if(['done','error'].includes(message.event.type))job.finish?.({ok:message.event.type==='done',error:message.event.message});
    if (message.event.type === 'status') await chrome.storage.local.set({ lastStatus: message.event.state === 'response-loading'
      ? 'Response couldn’t load — waiting to load' : 'Response loaded — receiving reply' });
    if (['done', 'error'].includes(message.event.type)) await chrome.storage.local.set({ lastStatus:
      message.event.type === 'done' ? 'Reply returned to Harness.' : message.event.message });
    respond({ ok: true });
  }).catch(error => respond({ ok: false, error: error.message }));
  return true;
});

chrome.tabs.onUpdated.addListener((tabId, change) => { if (change.url) void tabManager.updateURL(tabId, change.url); });

chrome.tabs.onRemoved.addListener(tabId => {
  void tabManager.forget(tabId);
  for (const [id, job] of running) if (job.tabId === tabId) {
    void request('/event', { id, type: 'error', message: 'Website tab was closed.' }).catch(() => {});
    job.finish?.({ok:false,error:'Website tab was closed.'});
    running.delete(id);
  }
});
chrome.alarms.create('connector-poll', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(() => void poll());
chrome.storage.onChanged.addListener(() => void poll());
setInterval(() => void poll(), 1200);
void updater.restore().catch(()=>{}).finally(()=>{updateRestored=true;void poll();});
