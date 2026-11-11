// This preload and the existing connector run only in Electron's isolated world.
// No bridge token, Node API, or IPC function is exposed to website JavaScript.
const {ipcRenderer}=require('electron');
if(process.isMainFrame&&['chatgpt.com','gemini.google.com','chat.deepseek.com','www.kimi.ai','www.kimi.com','kimi.com'].includes(location.hostname)){
  const listeners=[];
  const nativeStorage=globalThis.sessionStorage;
  const initial=ipcRenderer.sendSync('friday-receipts',{action:'read'});
  for(const [key,value]of Object.entries(initial||{}))nativeStorage.setItem(key,value);
  const storage={getItem:key=>nativeStorage.getItem(key),setItem:(key,value)=>{
    if(/^(harness-job:|harness-pending-files:|harness-captures:)/.test(key)){
      const result=ipcRenderer.sendSync('friday-receipts',{action:'write',key,value:String(value)});
      if(!result?.ok)throw new Error('Could not persist Friday submission receipt. Nothing was sent.');
    }
    nativeStorage.setItem(key,String(value));
  }};
  Object.defineProperty(globalThis,'sessionStorage',{value:storage});
  globalThis.chrome={runtime:{sendMessage:message=>ipcRenderer.invoke('friday-page-message',message),onMessage:{addListener:fn=>listeners.push(fn)}}};
  globalThis.FridayDesktopSubmit=async(id,button)=>{
    if(!button?.isConnected||button.disabled||button.getAttribute('aria-disabled')==='true')throw Error('Send control is unavailable. Nothing was sent.');
    const r=button.getBoundingClientRect();
    const admission=await ipcRenderer.invoke('friday-submit',{id,x:r.x+r.width/2,y:r.y+r.height/2});
    if(!admission?.ok)throw Error('Background submission was not admitted. Nothing was sent.');
    // A disappeared/replaced control after admission is uncertain: never fall
    // back to mouse input, refocus the window, or request a second admission.
    if(!button.isConnected||button.disabled||button.getAttribute('aria-disabled')==='true')throw Error('Send control changed after admission. Inspect the saved chat before retrying.');
    button.click();return {ok:true};
  };
  ipcRenderer.on('friday-command',(_event,{nonce,message})=>{
    let answered=false;
    const respond=result=>{if(!answered){answered=true;ipcRenderer.send('friday-command-result',{nonce,result});}};
    try{for(const listener of listeners)listener(message,{},respond);}catch(error){respond({ok:false,error:error.message});}
  });
  window.addEventListener('DOMContentLoaded',()=>ipcRenderer.send('friday-page-ready'),{once:true});
}
