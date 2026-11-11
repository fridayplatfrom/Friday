import '../extension/provider-catalog.js';
export const desktopProviders=['chatgpt-web','gemini-web','deepseek-web','kimi-web'].map(id=>{const p=globalThis.FridayProviderCatalog[id];return {id,name:p.name,url:p.url,hosts:p.selectors.hosts};});
export function siteForURL(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?desktopProviders.find(p=>p.hosts.includes(u.host))?.id:null;}catch{return null;}}
export function providerURL(value,site){try{const u=new URL(value),id=siteForURL(value);return id&&(!site||id===site)?u.origin+u.pathname:null;}catch{return null;}}
export function chatURL(value){return providerURL(value,'chatgpt-web');}
export function navigationAllowed(value){try{const u=new URL(value);return !!providerURL(value)||u.protocol==='https:'&&['auth.openai.com','auth0.openai.com','accounts.google.com','login.microsoftonline.com','appleid.apple.com'].includes(u.host)&&!u.username&&!u.password;}catch{return false;}}
export function localHarness(value){try{const u=new URL(value);return u.origin==='http://127.0.0.1:3030';}catch{return false;}}
export const pageMessageTypes=new Set(['harness-event','harness-job-file','harness-file-transfer','harness-download-watch','harness-download-result','harness-listener-refresh','harness-web-message','harness-web-stop']);
export class Signal {
  listeners=new Set();
  addListener=fn=>this.listeners.add(fn);
  removeListener=fn=>this.listeners.delete(fn);
  emit(...args){for(const fn of this.listeners)fn(...args);}
}
