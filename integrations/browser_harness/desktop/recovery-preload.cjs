const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('fridayRecovery',{
 restore:()=>ipcRenderer.invoke('friday-restore-interface'),
 onStatus:callback=>ipcRenderer.on('friday-interface-status',(_event,status)=>callback(status))
});
