// Isolated integration-test host. Never reads the installed Friday profile.
import {app,BrowserWindow,ipcMain} from 'electron';
import {join} from 'node:path';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {DesktopBrowserGuests} from '../../desktop/native-browser-guests.mjs';
import {startTaskBrowserRelay} from '../../desktop/task-browser-relay.mjs';
const root=process.env.FRIDAY_COMPARISON_ROOT;
if(!root)throw Error('Explicit isolated comparison directory required');
mkdirSync(join(root,'electron-profile'),{recursive:true});
writeFileSync(join(root,'startup.txt'),'module loaded');
app.setPath('userData',join(root,'electron-profile'));
app.commandLine.appendSwitch('disable-renderer-backgrounding');
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows');
app.whenReady().then(async()=>{
writeFileSync(join(root,'startup.txt'),'app ready');
const window=new BrowserWindow({width:1100,height:800,show:true,webPreferences:{webviewTag:true,nodeIntegration:true,contextIsolation:false,backgroundThrottling:false}});
const guests=new DesktopBrowserGuests(()=>undefined),sessionId='comparison',workspace='comparison-workspace';
guests.bind(window.webContents,()=>{guests.notify();return()=>{};});
await window.loadURL('data:text/html,'+encodeURIComponent('<!doctype html><title>Friday isolated browser comparison</title><style>html,body{margin:0;height:100%}webview{position:absolute;inset:0;width:100%;height:100%}</style><main></main>'));
writeFileSync(join(root,'startup.txt'),'host loaded');
async function create(url){
 const issued=guests.acquire(window.webContents,workspace),lease=guests.leases.get(issued.lease);lease.sessionId=sessionId;
 await window.webContents.executeJavaScript(`(()=>{for(const tab of document.querySelectorAll('webview'))tab.style.visibility='hidden';const tab=document.createElement('webview');tab.id=${JSON.stringify(issued.lease)};tab.setAttribute('partition',${JSON.stringify(issued.partition)});tab.setAttribute('allowpopups','');tab.src=${JSON.stringify('about:blank#'+issued.lease)};document.querySelector('main').append(tab);})()`);
 const until=Date.now()+15000;while(!lease.guest){if(Date.now()>until)throw Error('Test guest attachment timed out');await new Promise(r=>setTimeout(r,20));}
 await lease.guest.loadURL(url);return lease;
}
async function focus(guestId){const entry=[...guests.leases].find(([,lease])=>lease.guest?.id===guestId);if(!entry)throw Error('Unknown test guest');await window.webContents.executeJavaScript(`(()=>{for(const tab of document.querySelectorAll('webview'))tab.style.visibility=tab.id===${JSON.stringify(entry[0])}?'visible':'hidden';document.getElementById(${JSON.stringify(entry[0])}).focus();})()`);entry[1].guest.focus();}
// Exercise the production window-open handler and lease checks for popup tabs.
await window.webContents.executeJavaScript(`require('electron').ipcRenderer.on('friday-native-browser-open',(_event,request)=>require('electron').ipcRenderer.invoke('comparison-popup',request));void 0;`);
ipcMain.handle('comparison-popup',async(event,request)=>{if(event.sender!==window.webContents||!guests.leases.has(request.lease))throw Error('Unknown test popup');await create(request.url);});
const saved=process.env.FRIDAY_COMPARISON_RESTORE?JSON.parse(readFileSync(join(root,'tabs.json'),'utf8')):['about:blank'];
for(const url of saved)await create(url);
writeFileSync(join(root,'startup.txt'),'guest loaded');
const relay=await startTaskBrowserRelay({guests,file:join(root,'relay.json'),connect:async input=>{
 if(input.directory!==root||input.sessionId!==sessionId)throw Error('Wrong comparison scope');
 return {workspace,directory:root,sessionId,open:async options=>{
  if(options.focusGuestId){await focus(options.focusGuestId);return;}
  if(options.closeGuestId){const entry=[...guests.leases].find(([,l])=>l.guest?.id===options.closeGuestId);if(entry)await guests.release(window.webContents,entry[0]);return;}
  return create(options.url);
 }};
}});
let closing=false;
async function shutdown(){if(closing)return;closing=true;writeFileSync(join(root,'host.png'),(await window.webContents.capturePage()).toPNG());writeFileSync(join(root,'tabs.json'),JSON.stringify([...guests.leases.values()].map(l=>l.guest?.getURL()).filter(url=>/^http/.test(url))));await guests.flush();relay.close();app.exit(0);}
// Parent owns only this disposable process; a file signal supports graceful flush.
const timer=setInterval(()=>{try{readFileSync(join(root,'stop'));clearInterval(timer);void shutdown();}catch{}},100);
window.on('closed',()=>void shutdown());
}).catch(error=>{writeFileSync(join(root,'startup-error.txt'),error.stack);app.exit(1);});
