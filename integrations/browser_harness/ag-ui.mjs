import {randomUUID,createHash} from 'node:crypto';
import {join} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {EventSchema,RunAgentInputSchema} from '@ag-ui/core/schemas';
import {EventEncoder} from '@ag-ui/encoder';
import {DeliveryJournal} from './journal.mjs';
import {interactionFact,mergeInteraction} from './interactions.mjs';

const uuid=/^[a-f0-9-]{36}$/i;
const terminal=new Set(['RUN_FINISHED','RUN_ERROR']);
const textOf=m=>(m?.content||[]).filter(b=>b.type==='text').map(b=>b.text).join('\n');
const digest=value=>createHash('sha256').update(JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item)).digest('hex');

/** AG-UI 1.0 adapter. All execution and approvals stay in the native agent. */
export class FridayAGUI {
  constructor(bridge,directory,{maxEvents=4096,maxBytes=8*1024*1024}={}) {
    this.bridge=bridge;this.journal=new DeliveryJournal(directory&&join(directory,'ag-ui'));
    this.runtime=new Map();this.connections=0;this.maxEvents=maxEvents;this.maxBytes=maxBytes;
    for(const [id,s] of Object.entries(bridge.sessions.sessions))for(const r of s.aguiRuns||[])if(r.status==='running'){
      this.emit(id,r.runId,{type:'RUN_ERROR',message:'Harness restarted. Review the native transcript; no action was replayed.',code:'HARNESS_RESTARTED'});
    }
  }
  runs(id){return this.bridge.sessions.get(id)?.aguiRuns||[];}
  run(id,runId){return this.runs(id).find(r=>r.runId===runId);}
  active(id){return this.runs(id).findLast(r=>r.status==='running');}
  lastSnapshot(id,type){const record=this.journal.list(id).findLast(r=>r.data.event.type===type);return record?.data.event;}
  save(id,run){const runs=this.runs(id).filter(r=>r.runId!==run.runId);this.bridge.sessions.update(id,{aguiRuns:[...runs,run].slice(-100)});}
  create(id,runId=randomUUID(),inputHash=null,messages=[]) {
    const run={runId,status:'running',inputHash,events:0,bytes:0,startedAt:Date.now()};
    this.save(id,run);this.runtime.set(runId,{messages:[...messages],texts:new Map(),calls:new Set(),steps:new Set(),interactions:[]});
    this.emit(id,runId,{type:'RUN_STARTED',threadId:id,runId,protocolVersion:'1.0'});
    this.emit(id,runId,{type:'MESSAGES_SNAPSHOT',messages});
    return this.run(id,runId);
  }
  ensure(id){return this.active(id)||this.create(id);}
  emit(id,runId,event) {
    const run=this.run(id,runId);if(!run||run.status!=='running')return;
    let parsed=EventSchema.parse({...event,timestamp:Date.now()});
    const bytes=Buffer.byteLength(JSON.stringify(parsed));
    if(!terminal.has(parsed.type)&&(run.events>=this.maxEvents||run.bytes+bytes>this.maxBytes))parsed={type:'RUN_ERROR',message:'AG-UI output budget exceeded. Full results remain in Harness. Native execution was not cancelled.',code:'AGUI_OUTPUT_LIMIT'};
    const seq=this.journal.append(id,'ag-ui',{runId,event:parsed});
    this.save(id,{...run,events:run.events+1,bytes:run.bytes+bytes,...(terminal.has(parsed.type)?{status:parsed.type==='RUN_ERROR'?'error':'finished',endedAt:Date.now()}:{}),lastSeq:seq});
    if(terminal.has(parsed.type))this.runtime.delete(runId);
    return seq;
  }
  state(id,activity) {
    const run=this.active(id);if(!run)return;
    const screenshots=(this.bridge.sessions.get(id)?.activityScreenshots||[]).map(({id,url,mime,alt,callId})=>({id,url,mime,alt,callId}));
    this.emit(id,run.runId,{type:'STATE_SNAPSHOT',snapshot:{friday:{phase:activity.phase,message:activity.message,screenshots}}});
  }
  stream(id,frame) {
    const run=this.active(id);if(!run||frame.type!=='chunk')return;
    const rt=this.runtime.get(run.runId),chunk=frame.chunk;if(!rt||chunk.type!=='text-delta'||!chunk.text)return;
    const messageId=`${frame.attemptId}:${chunk.index}`;
    if(!rt.texts.has(messageId)){rt.texts.set(messageId,'');this.emit(id,run.runId,{type:'TEXT_MESSAGE_START',messageId,role:'assistant'});}
    rt.texts.set(messageId,rt.texts.get(messageId)+chunk.text);
    this.emit(id,run.runId,{type:'TEXT_MESSAGE_CONTENT',messageId,delta:chunk.text});
  }
  closeText(id,runId){const rt=this.runtime.get(runId);if(!rt)return;for(const messageId of rt.texts.keys())this.emit(id,runId,{type:'TEXT_MESSAGE_END',messageId});rt.texts.clear();}
  native(id,event) {
    if(event.type==='turn/start'&&!this.active(id))this.create(id);
    const run=this.active(id);if(!run)return;
    if(event.seq<=(run.nativeSeq||0))return;
    this.save(id,{...run,nativeSeq:event.seq});
    const rt=this.runtime.get(run.runId);if(!rt)return;const d=event.data||{};
    const fact=interactionFact(event),interactions=mergeInteraction(rt.interactions,fact);
    if(interactions!==rt.interactions){rt.interactions=interactions;this.emit(id,run.runId,{type:'CUSTOM',name:'friday.native-interaction',value:interactions.find(item=>item.id===fact.id)});}
    if(event.type==='assistant/message') {
      this.closeText(id,run.runId);
      const m=d.message||d;const content=textOf(m);
      const message={id:m.id||`native:${event.seq}`,role:'assistant',content};
      rt.messages.push(message);rt.parentMessageId=message.id;
      // Native committed text is authoritative even when the website rewrites a streamed draft.
      this.emit(id,run.runId,{type:'MESSAGES_SNAPSHOT',messages:rt.messages});
    }else if(event.type==='tool/call'){
      rt.calls.add(d.callId);
      const parent=rt.messages.find(m=>m.id===rt.parentMessageId);if(parent)(parent.toolCalls||=[]).push({id:d.callId,type:'function',function:{name:d.name,arguments:d.arguments}});
      this.emit(id,run.runId,{type:'TOOL_CALL_START',toolCallId:d.callId,toolCallName:d.name,...(rt.parentMessageId?{parentMessageId:rt.parentMessageId}:{})});
      this.emit(id,run.runId,{type:'TOOL_CALL_ARGS',toolCallId:d.callId,delta:d.arguments});
      this.emit(id,run.runId,{type:'TOOL_CALL_END',toolCallId:d.callId});
    }else if(event.type==='tool/result'){
      const m=d.message,toolCallId=m?.toolCallId||m?.callId;if(!rt.calls.has(toolCallId))return;
      const message={id:m.id||`native:${event.seq}`,role:'tool',toolCallId,content:textOf(m)};rt.messages.push(message);
      this.emit(id,run.runId,{type:'TOOL_CALL_RESULT',messageId:message.id,toolCallId,role:'tool',content:message.content,metadata:{friday:{isError:!!m.isError}}});
    }else if(event.type==='step/start'){rt.steps.add(d.step);this.emit(id,run.runId,{type:'STEP_STARTED',stepName:`step-${d.step}`});}
    else if(event.type==='step/end'&&rt.steps.has(d.step)){rt.steps.delete(d.step);this.emit(id,run.runId,{type:'STEP_FINISHED',stepName:`step-${d.step}`});}
    else if(event.type==='turn/end'){
      this.closeText(id,run.runId);
      this.emit(id,run.runId,{type:'MESSAGES_SNAPSHOT',messages:rt.messages});
      const kind=d.reason?.kind;
      if(kind==='error')this.emit(id,run.runId,{type:'RUN_ERROR',message:String(d.reason.error?.message||'Harness task failed'),code:'HARNESS_ERROR'});
      else if(!['completed','aborted'].includes(kind))this.emit(id,run.runId,{type:'RUN_ERROR',message:`Harness stopped with ${kind||'unknown outcome'}. Continue or review permissions in the native Harness interface.`,code:'HARNESS_NOT_COMPLETED'});
      else this.emit(id,run.runId,{type:'RUN_FINISHED',threadId:id,runId:run.runId,outcome:{type:kind==='aborted'?'cancelled':'success'},metadata:{friday:{nativeOutcome:kind}}});
    }
  }
  records(id,runId,after=0){return this.journal.list(id).filter(e=>e.data.runId===runId&&e.seq>after);}
  admit(raw) {
    const input=RunAgentInputSchema.parse(raw),id=input.threadId;
    if(!uuid.test(input.runId)||id.length>200||!this.bridge.sessions.get(id))throw new Error('Select an existing Friday session and supply a UUID runId.');
    if(input.tools.length||input.context.length||Object.keys(input.forwardedProps||{}).length||input.resume?.length)throw new Error('Friday retains native tools, context, state and approval controls. Client tool/state injection and protocol resume are unsupported.');
    const message=input.messages.at(-1);
    if(!message||message.role!=='user'||typeof message.content!=='string'||!message.content.trim()||message.content.length>80000)throw new Error('Append one new text user message. Harness retains its existing history and attachments.');
    if(!uuid.test(message.id))throw new Error('The user message needs a UUID id.');
    if(input.protocolVersion&&input.protocolVersion!=='1.0')throw new Error('Friday supports AG-UI 1.0.');
    const inputHash=digest(input.messages),previous=this.run(id,input.runId);
    if(previous){if(previous.inputHash!==inputHash)throw new Error('runId already belongs to another input. Nothing was resubmitted.');return previous;}
    const knownMessages=this.lastSnapshot(id,'MESSAGES_SNAPSHOT')?.messages||[];
    if(input.messages.length>1&&digest(input.messages.slice(0,-1))!==digest(knownMessages))throw new Error('Client history does not match the saved AG-UI transcript. Native history was not replaced.');
    if(Object.keys(input.state||{}).length&&digest(input.state)!==digest(this.lastSnapshot(id,'STATE_SNAPSHOT')?.snapshot||{}))throw new Error('Friday state is read-only. Refresh the saved state instead of overwriting native state.');
    if(input.parentRunId&&!this.run(id,input.parentRunId))throw new Error('Unknown parent run.');
    const agent=this.bridge.resolveAgent?.(id),route=agent?.session?.requestHeader?.()?.config;
    if(!agent||route?.provider!=='browser-web')throw new Error('Open the existing Friday browser-model session first.');
    if(agent.status==='running'||this.active(id))throw new Error('Harness is busy. This adapter will not interrupt its native task.');
    if(this.runs(id).some(r=>r.messageId===message.id))throw new Error('This user message was already admitted. Reconnect using its original runId.');
    const run=this.create(id,input.runId,inputHash,input.messages);this.save(id,{...run,messageId:message.id});
    try{agent.followup(Object.freeze({id:message.id,role:'user',source:Object.freeze({kind:'user',rpcId:message.id}),content:Object.freeze([Object.freeze({type:'text',text:message.content})])}));}
    catch(error){this.emit(id,input.runId,{type:'RUN_ERROR',message:'Native admission outcome is uncertain; inspect Harness before continuing. No automatic retry.',code:'ADMISSION_UNCERTAIN'});}
    return this.run(id,input.runId);
  }
  async serve(req,res,id,runId,after=0) {
    if(!this.run(id,runId))throw new Error('Unknown AG-UI run.');
    if(!Number.isSafeInteger(after)||after<0||after>this.journal.sequence)throw new Error('Invalid event cursor.');
    if(this.connections>=8)throw new Error('Too many AG-UI subscribers.');
    const encoder=new EventEncoder({accept:'text/event-stream'});this.connections++;
    res.writeHead(200,{'Content-Type':encoder.getContentType(),'Cache-Control':'no-store','X-Accel-Buffering':'no','X-Content-Type-Options':'nosniff'});res.flushHeaders?.();
    let cursor=after,lastHeartbeat=Date.now();
    try{while(!res.destroyed&&!this.closing){
      for(const record of this.records(id,runId,cursor)){
        if(res.destroyed)break;cursor=record.seq;
        if(!res.write(`id: ${cursor}\n`+encoder.encode(record.data.event)))await new Promise(resolve=>{
          const done=()=>{clearTimeout(timer);res.off('drain',done);res.off('close',done);resolve();};
          const timer=setTimeout(()=>{res.destroy();done();},5000);res.once('drain',done);res.once('close',done);
        });
      }
      if(this.run(id,runId)?.status!=='running')break;
      if(Date.now()-lastHeartbeat>10000){res.write(': keepalive\n\n');lastHeartbeat=Date.now();}
      await delay(100);
    }}finally{this.connections--;res.end();}
  }
}
