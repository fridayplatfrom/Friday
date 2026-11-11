// Reloading a crashed renderer restores a page; it must never dispatch an agent job.
export class RecoveryBudget {
 constructor({limit=2,windowMs=60000}={}){this.limit=limit;this.windowMs=windowMs;this.attempts=new Map();}
 admit(key,now=Date.now()){
  const recent=(this.attempts.get(key)||[]).filter(at=>now-at<this.windowMs);
  if(recent.length>=this.limit){this.attempts.set(key,recent);return false;}
  recent.push(now);this.attempts.set(key,recent);return true;
 }
}
export function recoveryTarget(current,saved,allowed){
 // A crashed WebContents can lose its URL. Only the saved, validated page is used.
 if(allowed(current))return current;
 if(allowed(saved))return saved;
 return null;
}
