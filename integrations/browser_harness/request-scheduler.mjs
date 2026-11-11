/** Bounded inference admission. Native Harness still owns tools and approvals. */
export class RequestScheduler {
  constructor(limit = 2) { this.limit=limit; this.active=new Map(); this.queue=[]; this.closed=false; }
  setLimit(limit) { this.limit=limit; this.drain(); }
  acquire(key, signal, notify=()=>{}) {
    signal?.throwIfAborted();
    if(this.closed)throw new Error('Friday bridge is stopping. No request was submitted.');
    if(this.active.size<this.limit&&!this.active.has(key))return this.reserve(key);
    return new Promise((resolve,reject)=>{
      const item={key,signal,notify,resolve,reject};
      item.abort=()=>{const at=this.queue.indexOf(item);if(at<0)return;this.queue.splice(at,1);signal.removeEventListener('abort',item.abort);reject(signal.reason||new DOMException('Request cancelled','AbortError'));this.drain();};
      this.queue.push(item);signal?.addEventListener('abort',item.abort,{once:true});this.report();
    });
  }
  reserve(key) {
    const token=Symbol(key);this.active.set(key,token);let released=false;
    return ()=>{if(released)return;released=true;if(this.active.get(key)===token)this.active.delete(key);this.drain();};
  }
  report() { this.queue.forEach((item,index)=>{try{item.notify({position:index+1,sameSession:this.active.has(item.key)});}catch{}}); }
  drain() {
    if(this.closed)return;
    while(this.active.size<this.limit){
      const index=this.queue.findIndex(item=>!this.active.has(item.key));if(index<0)break;
      const [item]=this.queue.splice(index,1);item.signal?.removeEventListener('abort',item.abort);
      item.resolve(this.reserve(item.key));
    }
    this.report();
  }
  close() {
    this.closed=true;
    for(const item of this.queue.splice(0)){item.signal?.removeEventListener('abort',item.abort);item.reject(new Error('Friday bridge stopped while queued. No request was submitted.'));}
  }
}
