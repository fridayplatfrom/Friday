import './provider-catalog.js';
const URLS=Object.fromEntries(Object.entries(globalThis.FridayProviderCatalog).map(([id,p])=>[id,p.url]));
const KEY = 'harnessWebsitePairs';
const keyFor = command => JSON.stringify([command.sessionId || 'unscoped', command.site]);
const provisionalURL=(site,value)=>{try{const pattern=globalThis.FridayProviderCatalog[site]?.provisionalConversationPath;return !!pattern&&new RegExp(pattern).test(new URL(value).pathname);}catch{return false;}};
const safeURL = (site, value) => {
  try { const url = new URL(value); return url.protocol==='https:'&&!url.username&&!url.password&&globalThis.FridayProviderCatalog[site]?.selectors.hosts.includes(url.host) ? url.origin + url.pathname : null; } catch { return null; }
};
const conversationURL=(site,value)=>{const url=safeURL(site,value);if(!url)return null;const path=new URL(url).pathname,provider=globalThis.FridayProviderCatalog[site],pattern=provider?.conversationPath;if(provider?.provisionalConversationPath&&new RegExp(provider.provisionalConversationPath).test(path))return null;return site==='chatgpt-web'&&/^\/c\/[^/]+\/?$/.test(path)||site==='deepseek-web'&&/^\/a\/chat\/s\/[^/]+\/?$/.test(path)||pattern&&new RegExp(pattern).test(path)?url:null;};
export async function browserRead(action,timeoutMs=1500){
 let timer;try{return await Promise.race([Promise.resolve().then(action),new Promise((_,reject)=>{timer=setTimeout(()=>{const error=new Error('Chrome tab lookup timed out. The saved tab was preserved; no replacement tab was opened.');error.code='FRIDAY_BROWSER_READ_TIMEOUT';reject(error);},timeoutMs);})]);}finally{clearTimeout(timer);}
}
const missingTab=error=>/no tab with id|invalid tab id|^closed$/i.test(error?.message||'');

/** Positive exact-URL discovery is valid even when a stale tab-ID lookup stalls. */
export async function findSavedTab(chrome,pair,pairs=[],readTimeoutMs=1500){
 const pinned=conversationURL(pair.site,pair.url);let failure;
 if(pinned&&chrome.tabs.query){
  let candidates;
  try{candidates=await browserRead(()=>chrome.tabs.query({url:new URL(pinned).origin+'/*'}),readTimeoutMs);}catch(error){failure=error;}
  if(candidates){
   const matches=candidates.filter(tab=>!tab.incognito&&safeURL(pair.site,tab.url)===pinned);
   const available=matches.filter(tab=>!pairs.some(p=>p.tabId===tab.id&&(p.sessionId!==pair.sessionId||p.site!==pair.site)));
   if(matches.length&&!available.length)throw new Error('This saved provider chat is already paired with another Friday conversation.');
   const found=available.find(tab=>tab.id===pair.tabId)||available.find(tab=>tab.active)||available[0];
   if(found)return found;
  }
 }
 if(Number.isInteger(pair.tabId)){
  try{
   const tab=await browserRead(()=>chrome.tabs.get(pair.tabId),readTimeoutMs);
   if(!safeURL(pair.site,tab.url))throw Object.assign(new Error('The paired website tab was navigated to another website. Return it to '+pair.url+' and retry.'),{code:'FRIDAY_PAIRED_TAB_MOVED'});
   if(!pinned||safeURL(pair.site,tab.url)===pinned)return tab;
  }catch(error){if(error.code==='FRIDAY_PAIRED_TAB_MOVED')throw error;if(!missingTab(error))failure=error;}
 }
 if(failure)throw failure;
 return null;
}

/** One persistent website tab per Harness session/provider. Never adopt unrelated tabs. */
export class WebsiteTabManager {
  constructor(chrome,{readTimeoutMs=1500}={}) { this.chrome = chrome; this.readTimeoutMs=readTimeoutMs;this.queue = Promise.resolve(); }
  exclusive(action) {
    const result = this.queue.then(action); this.queue = result.catch(() => {}); return result;
  }
  async bindings() { return Object.values((await this.chrome.storage.local.get(KEY))[KEY] || {}); }
  async lookup(pair){return findSavedTab(this.chrome,pair,await this.bindings(),this.readTimeoutMs);}
  pairExisting(command,tab){return this.exclusive(async()=>{
    const url=safeURL(command.site,tab?.url);if(!url||!Number.isInteger(tab?.id))throw new Error('Open the intended provider tab in Chrome before pairing.');
    const pairs=(await this.chrome.storage.local.get(KEY))[KEY]||{};
    if(Object.values(pairs).some(p=>p.tabId===tab.id&&(p.sessionId!==command.sessionId||p.site!==command.site)))throw new Error('This tab belongs to another Friday conversation.');
    const cleaned=Object.fromEntries(Object.entries(pairs).filter(([,p])=>!(p.sessionId===command.sessionId&&p.site===command.site)));
    const binding={sessionId:command.sessionId,site:command.site,tabId:tab.id,url};cleaned[keyFor(command)]=binding;
    await this.chrome.storage.local.set({[KEY]:cleaned});return binding;
  });}
  acquire(command) { return this.exclusive(async () => {
    if (!Object.hasOwn(URLS,command.site)) throw new Error('Unknown website.');
    const pairs = (await this.chrome.storage.local.get(KEY))[KEY] || {};
    // Migrate only our previously owned tab, never discover/adopt other website tabs.
    const legacy = (await this.chrome.storage.local.get('managedBrowserTab')).managedBrowserTab;
    if (legacy && !Object.keys(pairs).length) {
      pairs[keyFor(legacy)] = { sessionId: legacy.sessionId || 'unscoped', site: legacy.site, tabId: legacy.tabId, url: URLS[legacy.site] };
      await this.chrome.storage.local.remove('managedBrowserTab');
    }
    const key = keyFor(command); let state = pairs[key]; let tab; let navigationUrl = null;
    if(!state&&conversationURL(command.site,command.conversationUrl))state={sessionId:command.sessionId,site:command.site,url:conversationURL(command.site,command.conversationUrl)};
    const pinned=conversationURL(command.site,state?.url);
    if(pinned)navigationUrl=pinned;
    if(state)tab=await findSavedTab(this.chrome,state,Object.values(pairs),this.readTimeoutMs);
    if (!tab) {
      navigationUrl = !provisionalURL(command.site,state?.url)&&safeURL(command.site, state?.url) || URLS[command.site];
      try{tab = await this.chrome.tabs.create({ url: navigationUrl, active: false });}
      catch(error){if(!this.chrome.windows?.create||!/no current window|no normal window/i.test(error.message))throw error;const window=await this.chrome.windows.create({url:navigationUrl,type:'normal',focused:true});tab=window.tabs?.[0];if(!tab)throw new Error('Chrome opened without a usable provider tab.');}
    }
    state = { sessionId: command.sessionId || 'unscoped', site: command.site, tabId: tab.id,
      url: provisionalURL(command.site,tab.url)?URLS[command.site]:safeURL(command.site, tab.url) || navigationUrl || state.url };
    for(const [oldKey,p]of Object.entries(pairs))if(oldKey!==key&&p.sessionId===state.sessionId&&p.site===state.site)delete pairs[oldKey];
    pairs[key] = state; await this.chrome.storage.local.set({ [KEY]: pairs });
    return { tab, reset: false, navigationUrl, binding: state };
  }); }
  updateURL(tabId, url) { return this.exclusive(async () => {
    const pairs = (await this.chrome.storage.local.get(KEY))[KEY] || {}; let changed = false;
    for (const state of Object.values(pairs)) if (state.tabId === tabId) {
      const safe = safeURL(state.site, url);
      if(provisionalURL(state.site,safe))continue;
      // Pin an established conversation. Only the initial home -> chat promotion
      // may update its URL automatically; manual re-pairing is explicit.
      if(conversationURL(state.site,state.url)&&safe!==state.url)continue;
      if (safe && safe !== state.url) { state.url = safe; changed = true; }
    }
    if (changed) await this.chrome.storage.local.set({ [KEY]: pairs });
  }); }
  async complete(tabId) {
    try { const tab = await browserRead(()=>this.chrome.tabs.get(tabId),this.readTimeoutMs); await this.updateURL(tabId, tab.url); } catch {}
  }
  async focus(command) {
    const { tab } = await this.acquire(command);
    if(this.chrome.fridayDesktop?.backgroundExecution){await this.chrome.fridayDesktop.revealTab(tab.id);return;}
    await this.chrome.tabs.update(tab.id, { active: true });
    if (tab.windowId !== undefined) await this.chrome.windows.update(tab.windowId, { focused: true });
  }
  async failed() {} // Transport failures never discard the paired conversation.
  forget(tabId) { return this.exclusive(async () => {
    const pairs = (await this.chrome.storage.local.get(KEY))[KEY] || {};
    for (const state of Object.values(pairs)) if (state.tabId === tabId) state.tabId = null;
    await this.chrome.storage.local.set({ [KEY]: pairs });
  }); }
}

/** A navigation can leave an old listener alive briefly. A trusted extension
 * reply must identify the exact expected document before dispatch. */
export async function waitForWebsiteTab(chrome, tabId, { navigationUrl, isActive = () => true,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), attempts = 120,
  timeoutMs = 60000, probeTimeoutMs = 1500, now = () => Date.now(),onUnresponsive } = {}) {
  const deadline=now()+timeoutMs;
  let wakeAttempted=false;
  const probe=async action=>{
    let timer;
    try{return await Promise.race([Promise.resolve().then(action),new Promise((_,reject)=>{
      timer=setTimeout(()=>reject(new Error('Website readiness probe timed out.')),Math.max(1,Math.min(probeTimeoutMs,deadline-now())));
    })]);}finally{clearTimeout(timer);}
  };
  for (let i = 0; i < attempts && isActive() && now()<deadline; i++) {
    try {
      if(isActive()&&now()<deadline){
        const page = await probe(()=>chrome.tabs.sendMessage(tabId, { type: 'harness-ping' }));
        const expected = navigationUrl && new URL(navigationUrl);
        const actual = page?.url && new URL(page.url);
        if (isActive() && page?.ok && (page.readyState === 'complete'||page.readyState==='interactive'&&page.hasEditor) && (!expected ||
          (actual?.origin === expected.origin && actual.pathname === expected.pathname))) return true;
      }
    } catch {}
    if(i>=1&&!wakeAttempted&&onUnresponsive&&isActive()&&now()<deadline){
      wakeAttempted=true;try{await probe(onUnresponsive);}catch{}
    }
    await sleep(500);
  }
  return false;
}
