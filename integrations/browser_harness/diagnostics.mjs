import {readFileSync} from 'node:fs';
export const BACKEND_VERSION=JSON.parse(readFileSync(new URL('./package.json',import.meta.url),'utf8')).version;

export function failureDetails(error){
 const message=String(error?.message||error||'');
 const rules=[
  [/too many people are chatting with kimi/i,'website-capacity','Kimi availability','Kimi is busy. Wait and retry, or select another model in this same task. Kimi offers paid priority access, but has not provided a retry time. Your saved chat and task progress are preserved.'],
  [/extension not connected|connection disabled/i,'connection','Browser connection','Enable this provider in Settings → Models and check the paired tab before retrying.'],
  [/message (?:channel|port) closed|extension context invalidated|receiving end does not exist|could not establish connection/i,'connection','Website page listener','The paired page listener disconnected. Preserve the saved chat and inspect its latest reply before reconnecting. An accepted request must not be sent again automatically.'],
  [/send control|editor did not retain|submission could not be identified|submitted message does not match|website controls/i,'website-layout','Website adapter','Inspect the paired turn and check provider health. Try verified alternative selectors; never resend an uncertain submission.'],
  [/already generating/i,'website-busy','Model website','Wait for the existing response to finish. This attempt sent nothing.'],
  [/ERR_BLOCKED_BY_CLIENT/,'browser-policy','Harness browser configuration','Allow the intended task origin in the existing Harness browser policy, then retry navigation.'],
  [/request exceeds|context exceeds|too many parts|CONTEXT_WINDOW_EXCEEDED/i,'context-pressure','Native context budget','Use native Harness Compact or a saved handoff. The rejected request was not silently truncated.'],
  [/account changed|sign.?in|log.?in|verification prompt/i,'website-access','Model website access','Review the paired website account or verification screen before retrying.'],
  [/attachment|upload|download|file transfer/i,'file-transfer','File transfer','Keep the saved original and inspect transfer status before retrying.'],
  [/limit|too many requests|try again later/i,'website-limit','Website or transport limit','Review the exact error and website limit; do not automatically resubmit an uncertain request.'],
  [/tool-request|tool request|not offered|rewrote already-streamed/i,'reply-format','Website reply format','Review the paired reply and connector version. No rejected tool request was executed.'],
  [/busy|waiting for the browser/i,'browser-slot','Browser connection','Wait for the accepted job to finish; check its receipt before submitting another.'],
  [/timed out|timeout|not connected/i,'connection','Browser connection','Check the existing paired tab and connector heartbeat; reconcile the last submission before retrying.'],
 ];
 const match=rules.find(([pattern])=>pattern.test(message));
 return match?{category:match[1],component:match[2],nextAction:match[3]}:{category:'execution',component:'Friday request',nextAction:'Inspect the actual error and saved task state before retrying.'};
}

export function recoveryDiagnostic(error,job={},now=Date.now()){
 const message=String(error?.message||error||'');
 const submission=job.submitted?'submitted':job.claimed===false||/no prompt was (?:sent|submitted)|nothing was (?:sent|submitted)|nothing was auto-submitted|no message was submitted/i.test(message)?'not-submitted':'unknown';
 return {at:now,requestId:job.id,provider:job.site,backendVersion:BACKEND_VERSION,...failureDetails(error),submission,
   retry:'manual',automaticResubmit:false,automaticProviderSwitch:false,canRetryWithoutDuplicateSubmission:submission==='not-submitted',
   nextAction:submission==='submitted'||submission==='unknown'?'Inspect the paired conversation and saved native tool results before retrying or switching providers. '+failureDetails(error).nextAction:failureDetails(error).nextAction};
}

/** Bounded local operational facts only: never return prompts, URLs, filenames or secrets. */
export function recentMetrics(events,{limit=2000}={}){
 const window=events.slice(-limit),requests=new Map(),latencies=[];
 let completed=0,failed=0,cancelled=0,waits=0;
 for(const event of window){
   const id=event.data?.id;
   if(event.type==='request'&&id)requests.set(id,{start:event.at,first:null,terminal:false});
   if(event.type==='waiting-image-job')waits++;
   const request=requests.get(id);if(!request)continue;
   if(event.type==='reply'&&request.first===null)request.first=event.at;
   if(!['complete','failed','cancelled'].includes(event.type)||request.terminal)continue;
   request.terminal=true;
   if(event.type==='complete')completed++;else if(event.type==='failed')failed++;else cancelled++;
   if(Number.isFinite(event.at-request.start)&&event.at>=request.start)latencies.push(event.at-request.start);
 }
 const first=[...requests.values()].filter(r=>r.first!==null&&r.first>=r.start).map(r=>r.first-r.start);
 const mean=values=>values.length?Math.round(values.reduce((sum,n)=>sum+n,0)/values.length):null;
 return {scope:'recent local transport attempts; not complete-task success or token usage',eventWindow:window.length,attempts:requests.size,completed,failed,cancelled,imageWaits:waits,meanDurationMs:mean(latencies),meanFirstObservedReplyMs:mean(first)};
}
