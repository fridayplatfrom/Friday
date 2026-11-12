import {mkdirSync,realpathSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {randomUUID} from 'node:crypto';
const canonical=value=>process.platform==='win32'?value.toLowerCase():value;
export function taskArtifacts(directory){
 const base=realpathSync(directory),expected=join(base,'.friday-browser-artifacts');mkdirSync(expected,{recursive:true});
 if(canonical(realpathSync(expected))!==canonical(resolve(expected)))throw Error('The task artifact directory must not redirect outside its workspace.');
 return expected;
}
export function acceptDownloadBehavior(params,directory){
 if(params.behavior==='deny'||params.behavior==='default')return false;
 if(!['allow','allowAndName'].includes(params.behavior)||typeof params.downloadPath!=='string'||canonical(resolve(params.downloadPath))!==canonical(taskArtifacts(directory)))throw Error('Downloads must remain in this task workspace artifact directory.');
 return true;
}
/** Electron DownloadItem -> scoped CDP events expected by the unchanged MCP tools. */
export function taskDownload(item,{guest,directory,send,validate=()=>{}}){
 validate();const guid=randomUUID(),path=join(taskArtifacts(directory),guid);
 const suggestedFilename=String(item.getFilename()||'download').replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,180)||'download';
 item.setSavePath(path);
 const frame=guest.debugger.sendCommand('Page.getFrameTree').then(tree=>{
  const frameId=tree.frameTree?.frame?.id;if(!frameId)throw Error('Download frame was not identified.');
  send({method:'Browser.downloadWillBegin',params:{frameId,guid,url:item.getURL(),suggestedFilename}});
 });
 const progress=state=>{void frame.then(()=>send({method:'Browser.downloadProgress',params:{guid,totalBytes:item.getTotalBytes(),receivedBytes:item.getReceivedBytes(),state}})).catch(()=>{});};
 item.on('updated',()=>progress('inProgress'));
 item.once('done',(_event,state)=>progress(state==='completed'?'completed':'canceled'));
 void frame.catch(()=>item.cancel());return {guid,path,suggestedFilename};
}
