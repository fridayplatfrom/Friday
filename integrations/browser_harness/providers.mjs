import './extension/provider-catalog.js';
export const PROVIDERS=globalThis.FridayProviderCatalog;
export const SITES=Object.freeze(Object.fromEntries(Object.entries(PROVIDERS).map(([id,p])=>[id,{name:p.name,url:p.url}])));
export function publicProvider(id,health){if(!Object.hasOwn(PROVIDERS,id))throw new Error('Unknown provider.');const p=PROVIDERS[id];return {id,name:p.name,url:p.url,revision:p.revision,experimental:p.experimental,backup:p.backup,capabilities:p.capabilities,health:health||{state:'unchecked'}};}
export function providerProbe(input){
 if(!Object.hasOwn(PROVIDERS,input.site))throw new Error('Unknown provider.');const p=PROVIDERS[input.site];
 const page=input.page||{},matched=page.provider===p.id;
 return {state:input.probeStatus==='missing-tab'?'needs-reconnect':input.notOpen?'not-open':!matched?'unavailable':page.hasEditor?page.isGenerating?'busy':'ready':'needs-attention',checkedAt:Date.now(),scopeSession:typeof input.scopeSession==='string'?input.scopeSession.slice(0,200):null,adapterRevision:p.revision,listenerResponded:!!input.page,reportedProvider:Object.hasOwn(PROVIDERS,page.provider)?page.provider:null,editorObserved:page.hasEditor===true,
  probeStatus:['no-paired-tab','responded','empty-response','missing-tab','listener-missing','probe-timeout','probe-failed'].includes(input.probeStatus)?input.probeStatus:'unchecked',hasEditor:matched&&page.hasEditor===true,isGenerating:matched&&page.isGenerating===true,scope:input.probeStatus==='missing-tab'?'Saved Chrome tab ID is missing; the saved chat URL may still be open under another ID. The next explicit task uses normal saved-chat recovery.':'Existing paired tab; readiness is not a verified task result'};
}
