const {contextBridge,ipcRenderer}=require('electron');
window.addEventListener('error',event=>{if(event.error)ipcRenderer.send('friday-native-diagnostic',{kind:'runtime-error',message:String(event.error.message||event.message).slice(0,500)});});
window.addEventListener('unhandledrejection',event=>ipcRenderer.send('friday-native-diagnostic',{kind:'unhandled-rejection',message:String(event.reason?.message||event.reason).slice(0,500)}));
contextBridge.exposeInMainWorld('fridayDesktopWorkspace',{
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
