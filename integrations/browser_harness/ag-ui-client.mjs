// Browser-only observer. It has no task submission, tool execution or cancel path.
export function emptyActivity(){return {revision:0,phase:'waiting',message:'Connecting to task stream',events:[],tools:[],screenshots:[],interactions:[]};}
export function projectEvent(previous,event,cursor){
 if(cursor<=previous.revision)return previous;
 const next={...previous,revision:cursor,events:[...previous.events,{...event,metadata:{...event.metadata,friday:{...event.metadata?.friday,revision:cursor}}}].slice(-180),tools:previous.tools.map(t=>({...t}))};
 if(event.type==='RUN_STARTED'){next.phase='running';next.message='Harness task started';}
 if(event.type==='CUSTOM'&&event.name==='friday.native-interaction'){
  const item=event.value;next.interactions=[...(previous.interactions||[]).filter(x=>x.id!==item.id),item].slice(-40);
  if(item.status==='requested'){next.phase=item.kind==='approval'?'approval':'question';next.message=item.kind==='approval'?'Waiting for your decision in Harness':'Waiting for your answer in Harness';}
 }
 if(event.type==='STATE_SNAPSHOT'&&event.snapshot?.friday){const state=event.snapshot.friday;next.phase=state.phase;next.message=state.message;next.screenshots=state.screenshots||[];}
 if(event.type==='TOOL_CALL_START'&&!next.tools.some(t=>t.id===event.toolCallId))next.tools.push({id:event.toolCallId,name:event.toolCallName,status:'requested',arguments:'',result:''});
 const tool=next.tools.find(t=>t.id===event.toolCallId);
 if(event.type==='TOOL_CALL_ARGS'&&tool)tool.arguments=(tool.arguments+event.delta).slice(0,16000);
 if(event.type==='TOOL_CALL_RESULT'&&tool){tool.status=event.metadata?.friday?.isError?'error':'completed';tool.result=event.content.length>24000?event.content.slice(0,24000)+'\n[Preview shortened; full result is in the native transcript.]':event.content;}
 if(event.type==='RUN_FINISHED'){next.phase=event.outcome?.type==='cancelled'?'cancelled':'completed';next.message=event.outcome?.type==='cancelled'?'Task stopped':'Task completed';}
 if(event.type==='RUN_ERROR'){next.phase=event.code==='HARNESS_RESTARTED'?'interrupted':'error';next.message=event.message;}
 if(['RUN_ERROR','RUN_FINISHED'].includes(event.type))next.interactions=(next.interactions||[]).map(item=>item.status==='requested'?{...item,status:'interrupted'}:item);
 next.tools=next.tools.slice(-12);return next;
}

// Incremental SSE framing handles arbitrary UTF-8/network chunk boundaries.
export async function consumeSSE(response,{signal,onEvent}){
 if(!response.ok)throw new Error(`Task stream unavailable (${response.status})`);
 if(!response.headers.get('content-type')?.includes('text/event-stream'))throw new Error('Invalid task stream response');
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',id='',data=[],terminal=false;
 function line(value){
  if(value===''){if(data.length){const cursor=Number(id);if(!Number.isSafeInteger(cursor)||cursor<1)throw new Error('Invalid task stream cursor');const event=JSON.parse(data.join('\n'));onEvent(event,cursor);if(['RUN_FINISHED','RUN_ERROR'].includes(event.type))terminal=true;}id='';data=[];}
  else if(value.startsWith('id:'))id=value.slice(3).trim();else if(value.startsWith('data:'))data.push(value.slice(5).replace(/^ /,''));
 }
 const stopRead=()=>{void reader.cancel().catch(()=>{});};
 signal?.addEventListener('abort',stopRead,{once:true});
 try{while(!signal?.aborted&&!terminal){const {done,value}=await reader.read();if(done||signal?.aborted)break;buffer+=decoder.decode(value,{stream:true});if(buffer.length>12*1024*1024)throw new Error('Task stream frame too large');let end;while(!terminal&&(end=buffer.indexOf('\n'))>=0){line(buffer.slice(0,end).replace(/\r$/,''));buffer=buffer.slice(end+1);}}}
 finally{signal?.removeEventListener('abort',stopRead);await reader.cancel().catch(()=>{});reader.releaseLock();}
 if(!terminal&&!signal?.aborted)throw new Error('Task stream interrupted; reconnecting');
 return terminal;
}

export function observeRun({threadId,runId,onActivity,onStatus,fetchImpl=fetch,retryMs=1200}){
 const controller=new AbortController();let activity=emptyActivity();onActivity(activity);
 const done=(async()=>{while(!controller.signal.aborted){
  try{
   const response=await fetchImpl(`/browser-models/ag-ui/runs/${encodeURIComponent(runId)}?threadId=${encodeURIComponent(threadId)}&after=${activity.revision}`,{credentials:'same-origin',headers:{'X-Harness-Models':'1'},signal:controller.signal});
   onStatus('');
   await consumeSSE(response,{signal:controller.signal,onEvent:(event,cursor)=>{activity=projectEvent(activity,event,cursor);onActivity(activity);}});
   return;
  }catch(error){if(controller.signal.aborted)return;onStatus('Friday reconnecting — saved task activity is retained. '+error.message);}
  await new Promise(resolve=>{const finish=()=>{clearTimeout(timer);controller.signal.removeEventListener('abort',finish);resolve();};const timer=setTimeout(finish,retryMs);controller.signal.addEventListener('abort',finish,{once:true});});
 }})();
 return {stop:()=>controller.abort(),done};
}
