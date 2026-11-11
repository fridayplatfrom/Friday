const nameMatches=(expected,filename)=>{
  const actual=filename.split(/[\\/]/).at(-1),dot=expected.lastIndexOf('.');
  const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const stem=dot<0?expected:expected.slice(0,dot),ext=dot<0?'':expected.slice(dot);
  return new RegExp('^'+escape(stem)+'(?: ?\\(\\d+\\))?'+escape(ext)+'$').test(actual);
};
export class BrowserDownloadWatch {
  constructor(chrome,{importFile,isActive,now=()=>Date.now(),id=()=>crypto.randomUUID(),timeoutMs=120000}={}){
    Object.assign(this,{chrome,importFile,isActive,now,id,timeoutMs});this.watches=new Map();this.origins=new Map();
  }
  async arm(job,tab,name){
    if(!await this.chrome.permissions?.contains({permissions:['downloads']}))return {available:false};
    if(!this.isActive(job.id)||typeof name!=='string'||/[\\/\x00-\x1f]/.test(name)||name.length>180)throw new Error('Invalid browser download watch.');
    const watchId=this.id(),started=this.now(),origin=new URL(tab.url).origin,ids=new Set(),processing=new Set();
    if(this.origins.has(origin))return {available:false,busy:true};
    this.origins.set(origin,watchId);
    let resolve,reject,timer,finished=false;
    const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});promise.catch(()=>{});
    const sourceMatches=item=>{
      try{const source=new URL(item.referrer||item.url);return source.origin===origin&&Date.parse(item.startTime)>=started-1000;}catch{return false;}
    };
    const cleanup=()=>{clearTimeout(timer);if(this.origins.get(origin)===watchId)this.origins.delete(origin);this.chrome.downloads.onCreated.removeListener(created);this.chrome.downloads.onChanged.removeListener(changed);};
    const finish=(error,file)=>{if(finished)return;finished=true;cleanup();error?reject(error):resolve(file);};
    const complete=async downloadId=>{
      if(processing.has(downloadId)||finished)return;processing.add(downloadId);
      try{
        const [item]=await this.chrome.downloads.search({id:downloadId});
        if(!item||item.state!=='complete'||!sourceMatches(item)||!nameMatches(name,item.filename))return;
        if(!this.isActive(job.id))throw new Error('Download task was cancelled.');
        const file=await this.importFile(job,{downloadId:item.id,filename:item.filename,size:item.fileSize,startTime:item.startTime,referrer:item.referrer,url:item.url});
        finish(null,file);
      }catch(error){finish(error);}
    };
    const created=item=>{if(!sourceMatches(item))return;ids.add(item.id);if(item.state==='complete')void complete(item.id);};
    const changed=delta=>{if(!ids.has(delta.id))return;if(delta.state?.current==='complete')void complete(delta.id);else if(delta.state?.current==='interrupted')finish(new Error('Browser download was interrupted.'));};
    this.chrome.downloads.onCreated.addListener(created);this.chrome.downloads.onChanged.addListener(changed);
    timer=setTimeout(()=>finish(new Error('No matching new browser download completed for this file.')),this.timeoutMs);
    this.watches.set(watchId,{jobId:job.id,promise,finish});return {available:true,watchId};
  }
  async wait(watchId,jobId){const watch=this.watches.get(watchId);if(!watch||watch.jobId!==jobId)throw new Error('Unowned browser download.');
    try{return await watch.promise;}finally{this.watches.delete(watchId);}}
  cancel(jobId){for(const [id,watch]of this.watches)if(watch.jobId===jobId){watch.finish(new Error('Download task was cancelled.'));this.watches.delete(id);}}
}
