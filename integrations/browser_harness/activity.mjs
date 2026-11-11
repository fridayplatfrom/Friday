import { randomUUID } from 'node:crypto';

const LIMIT = 180;
const clip = (value, size = 12000) => String(value ?? '').slice(0, size);
const active = new Set(['queued','waiting','receiving','uploading','reconnecting','generating','executing','requested','reply-received','approval','question']);

/** Local projection of facts, not an execution engine. Native Harness remains authoritative. */
export class Activity {
  constructor(sessions) { this.sessions = sessions; }
  get(id) { return this.sessions.get(id)?.activity || { revision:0, events:[], tools:[], phase:'idle' }; }
  emit(id, type, data = {}, changes = {}) {
    const previous = this.get(id), revision = previous.revision + 1;
    const event = { type, timestamp:Date.now(), ...data, metadata:{ ...data.metadata, friday:{ revision } } };
    const next = { ...previous, ...changes, revision, events:[...previous.events,event].slice(-LIMIT) };
    this.sessions.update(id, { activity:next });
    this.onEvent?.(id,event,next);
    return next;
  }
  status(id, phase, message, requestId) {
    const old = this.get(id);
    if (old.phase === phase && old.message === message && old.requestId === requestId) return;
    return this.emit(id,'CUSTOM',{name:'friday.connection',value:{phase,message:clip(message,500),requestId}},
      {phase,message:clip(message,500),requestId});
  }
  ensure(id) {
    const old = this.get(id);
    if (!old.runId || !active.has(old.phase)) {
      const runId=randomUUID();
      this.emit(id,'RUN_STARTED',{threadId:id,runId},{runId,phase:'queued',message:'Preparing the website request'});
    }
  }
  native(id, event) {
    if (!Number.isSafeInteger(event.seq) || event.seq <= (this.get(id).nativeSeq || 0)) return false;
    const d = event.data || {}, old = this.get(id), changes = { nativeSeq:event.seq };
    if (event.type === 'turn/start') {
      const runId = `${id}:${d.turn}`;
      this.emit(id,'RUN_STARTED',{threadId:id,runId},{...changes,runId,phase:'queued',message:'Harness started the task'});
    } else if (event.type === 'tool/call') {
      const tool = { id:d.callId,name:clip(d.name,160),arguments:clip(d.arguments,4000),status:'requested',at:Date.now() };
      const tools = [...old.tools.filter(t=>t.id!==tool.id),tool].slice(-40);
      this.emit(id,'TOOL_CALL_START',{toolCallId:tool.id,toolCallName:tool.name},
        {...changes,tools,phase:d.name==='ask_user_question'?'question':'requested',message:d.name==='ask_user_question'?'Waiting for your answer in the native question card':`${tool.name} requested — awaiting Harness result`});
    } else if(event.type==='approval/asked'){
      this.emit(id,'CUSTOM',{name:'friday.approval',value:{id:d.id,callId:d.callId,status:'requested'}},{...changes,phase:'approval',message:'Waiting for your decision in the native approval card'});
    } else if(event.type==='approval/decided'){
      this.emit(id,'CUSTOM',{name:'friday.approval',value:{id:d.id,status:d.outcome}},{...changes,phase:'executing',message:`Harness approval: ${d.outcome}`});
    } else if (event.type === 'tool/result') {
      const m = d.message || {}, callId = m.toolCallId || m.callId;
      const text = clip((m.content||[]).filter(b=>b.type==='text').map(b=>b.text).join('\n'));
      const tools = old.tools.map(tool=>tool.id===callId?{...tool,status:m.isError?'error':'completed',result:text,finishedAt:Date.now()}:tool);
      this.emit(id,'TOOL_CALL_RESULT',{toolCallId:callId,messageId:m.id || `native:${event.seq}`,content:text,role:'tool'},
        {...changes,tools,phase:'executing',message:m.isError?'Harness returned a tool error':'Harness returned the tool result'});
    } else if (event.type === 'turn/end') {
      const kind = d.reason?.kind, phase = kind==='completed'?'completed':kind==='aborted'?'cancelled':kind==='error'?'error':'paused';
      const message = phase==='completed'?'Task completed':phase==='cancelled'?'Task cancelled':phase==='error'?clip(d.reason?.error?.message||'Harness task failed',500):`Harness paused: ${kind || 'awaiting input'}`;
      this.emit(id,phase==='error'?'RUN_ERROR':'RUN_FINISHED',phase==='error'?{message}:{threadId:id,runId:old.runId},
        {...changes,phase,message});
    } else return false;
    return true;
  }
  interrupted(id) {
    const old=this.get(id);
    if(active.has(old.phase))this.status(id,'interrupted','Harness restarted. Saved activity restored; review pending actions before continuing. Nothing was replayed.',old.requestId);
  }
  snapshot(id, after=0) {
    const a=this.get(id), earliest=a.events[0]?.metadata.friday.revision || a.revision;
    const reset=after>a.revision || after<earliest-1;
    return {...a, reset,
      events:reset?a.events:a.events.filter(e=>e.metadata.friday.revision>after), screenshots:this.sessions.get(id)?.activityScreenshots||[]};
  }
}

/** Read native attachment references only; never fetch a URL supplied in model text. */
export async function captureToolImages(bridge, id, event) {
  if(event.type!=='tool/result' || !bridge.readImage)return;
  const message=event.data?.message;
  for(const block of (message?.content||[]).filter(b=>b.type==='image'&&b.attachment).slice(0,8)) {
    const key=`${event.seq}:${block.attachment.attachmentId}`;
    if(bridge.sessions.get(id)?.activityScreenshots?.some(image=>image.key===key))continue;
    const image=await bridge.readImage(block.attachment);
    const saved=bridge.sessions.saveImage(Buffer.from(image.data),image.mediaType,'Harness tool screenshot');
    bridge.sessions.update(id,{activityScreenshots:[...(bridge.sessions.get(id)?.activityScreenshots||[]),{...saved,key,callId:message.toolCallId||message.callId}].slice(-20)});
    bridge.activity.emit(id,'CUSTOM',{name:'friday.screenshot',value:{id:saved.id,callId:message.toolCallId||message.callId}});
  }
}
