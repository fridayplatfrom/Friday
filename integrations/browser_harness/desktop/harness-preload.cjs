const {contextBridge,ipcRenderer}=require('electron');
// Harness's original BrowserBody selects its retained Electron carrier through this contract.
const browserOpenListeners=new Map();
ipcRenderer.on('friday-native-browser-open',(_event,request)=>{if(typeof request?.lease!=='string'||typeof request.url!=='string')return;for(const callback of browserOpenListeners.get(request.lease)||[])callback(request.url);});
contextBridge.exposeInMainWorld('dshDesktop',{protocolVersion:1,browser:{
 acquire:workspace=>ipcRenderer.invoke('friday-native-browser-acquire',workspace),
 release:lease=>ipcRenderer.invoke('friday-native-browser-release',lease),
 onOpenRequested:(lease,callback)=>{let listeners=browserOpenListeners.get(lease);if(!listeners)browserOpenListeners.set(lease,listeners=new Set());listeners.add(callback);return()=>{listeners.delete(callback);if(!listeners.size)browserOpenListeners.delete(lease);};}
}});
window.addEventListener('error',event=>{if(event.error)ipcRenderer.send('friday-native-diagnostic',{kind:'runtime-error',message:String(event.error.message||event.message).slice(0,500)});});
window.addEventListener('unhandledrejection',event=>ipcRenderer.send('friday-native-diagnostic',{kind:'unhandled-rejection',message:String(event.reason?.message||event.reason).slice(0,500)}));
contextBridge.exposeInMainWorld('fridayDesktopWorkspace',{
 setup:input=>ipcRenderer.invoke('friday-onboarding',input),
 setupDock:input=>ipcRenderer.send('friday-onboarding-dock',input),
 onSetup:callback=>{const listener=()=>callback();ipcRenderer.on('friday-onboarding-show',listener);return()=>ipcRenderer.removeListener('friday-onboarding-show',listener);},
 registerTaskBrowser:input=>ipcRenderer.send('friday-task-browser-register',input),
 onTaskBrowser:callback=>{const listener=(_event,input)=>callback(input);ipcRenderer.on('friday-task-browser',listener);return()=>ipcRenderer.removeListener('friday-task-browser',listener);},
 taskBrowserResult:(nonce,result)=>ipcRenderer.send('friday-task-browser-result',{nonce,...result}),
 selectSession:id=>ipcRenderer.send('friday-native-session',id),
 dock:input=>ipcRenderer.send('friday-native-dock',input),
 revealProvider:(site,sessionId)=>ipcRenderer.send('friday-reveal-provider',{site,sessionId}),
 onFocus:callback=>{const listener=(_event,input)=>callback(input);ipcRenderer.on('friday-native-focus',listener);return()=>ipcRenderer.removeListener('friday-native-focus',listener);}
});
window.addEventListener('DOMContentLoaded',()=>{
 let applied=false;
 const collapse=()=>{if(applied)return;const close=document.querySelector('button[aria-label="Close sidebar"],button[title="Close sidebar"],button[aria-label="Collapse sidebar"],button[title="Collapse sidebar"]');if(close){close.click();applied=true;observer.disconnect();}else if(document.querySelector('button[aria-label="Open sidebar"]')){applied=true;observer.disconnect();}};
 const observer=new MutationObserver(collapse);observer.observe(document.documentElement,{subtree:true,childList:true});collapse();
},{once:true});
