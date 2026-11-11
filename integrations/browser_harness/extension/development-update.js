// Opt-in for this unpacked local development installation. No remote code,
// extension installation, new permissions, or inference endpoints are involved.
import {browserRead} from './tab-manager.js';
export class DevelopmentUpdater {
  constructor(chrome,{enabled,readManifest,bindings,now=()=>Date.now(),probeMs=800}={}){
    Object.assign(this,{chrome,enabled,readManifest,bindings,now,probeMs});
    this.version=chrome.runtime.getManifest().version;this.nextCheck=0;this.checking=false;this.reloading=false;
  }
  async probe(id){
    let timer;
    try{return await Promise.race([this.chrome.tabs.sendMessage(id,{type:'harness-ping'}),new Promise((_,reject)=>{
      timer=setTimeout(()=>reject(new Error('Tab unavailable')),this.probeMs);
    })]);}finally{clearTimeout(timer);}
  }
  async resolve(pair){
    const matches=tab=>{try{const url=new URL(tab.url);return !tab.incognito&&url.origin+url.pathname===pair.url;}catch{return false;}};
    // Chrome can assign a new ID after restoring a window. Never open a tab or
    // adopt another conversation just to update the connector.
    let queryFailure;
    if(this.chrome.tabs.query)try{const tabs=await browserRead(()=>this.chrome.tabs.query({}),this.probeMs);const found=tabs.filter(matches);if(found.length)return found;}catch(error){queryFailure=error;}
    try{const tab=await browserRead(()=>this.chrome.tabs.get(pair.tabId),this.probeMs);if(matches(tab))return [{...tab,id:pair.tabId}];}catch(error){if(!/no tab|invalid tab id|^closed$/i.test(error.message))throw error;}
    if(queryFailure)throw queryFailure;
    return [];
  }
  async check(isBusy){
    if(this.checking||this.reloading||isBusy()||this.now()<this.nextCheck)return false;
    this.checking=true;this.nextCheck=this.now()+3000;
    try{
      if(!await this.enabled())return false;
      const manifest=await this.readManifest();
      if(!/^\d+\.\d+\.\d+$/.test(manifest?.version||'')||manifest.version===this.version)return false;
      const refresh=[];const seen=new Set();
      for(const pair of (await this.bindings()).slice(0,200)){
        for(const tab of await this.resolve(pair)){
          if(seen.has(tab.id))continue;seen.add(tab.id);
          let state;try{state=await this.probe(tab.id);}catch{}
          // Reloading the extension invalidates every old page listener. Defer
          // the entire update rather than strand a draft or an active reply.
          if(!state?.ok||state.hasDraft!==false||state.isGenerating!==false){
            await this.chrome.storage.local.set({lastStatus:'Local connector update waiting for paired tabs to become idle.'});
            return false;
          }
          refresh.push({tabId:tab.id,url:pair.url});
        }
      }
      if(isBusy())return false;
      await this.chrome.storage.local.set({harnessDevelopmentUpdate:{version:manifest.version,refresh},lastStatus:'Loading local connector update '+manifest.version});
      if(isBusy()){await this.chrome.storage.local.set({harnessDevelopmentUpdate:null});return false;}
      this.reloading=true;this.chrome.runtime.reload();return true;
    }catch{return false;}finally{this.checking=false;}
  }
  async restore(){
    const pending=(await this.chrome.storage.local.get('harnessDevelopmentUpdate')).harnessDevelopmentUpdate;
    if(!pending||pending.version!==this.version)return;
    await this.chrome.storage.local.set({harnessDevelopmentUpdate:null,lastStatus:pending.preserved?'Connector updated; draft or unavailable tabs were preserved. Refresh them when ready.':'Connector updated automatically.'});
    for(const pair of pending.refresh||[]){
      try{for(const tab of await this.resolve(pair))await this.chrome.tabs.reload(tab.id);}catch{}
    }
  }
}
