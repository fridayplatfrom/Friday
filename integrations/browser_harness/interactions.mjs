// Read-only native interaction facts. This module cannot approve tools or answer questions.
const text=m=>(m?.content||[]).filter(b=>b.type==='text').map(b=>b.text).join('\n');
const clip=v=>String(v??'').slice(0,12000);
export function interactionFact(event){
 const d=event.data||{};
 if(event.type==='approval/asked')return {id:`approval:${d.id}`,kind:'approval',status:'requested',toolName:d.toolName,callId:d.callId,reason:clip(d.reason)};
 if(event.type==='approval/decided')return {id:`approval:${d.id}`,kind:'approval',status:d.outcome,requiresExisting:true};
 if(event.type==='tool/call'&&d.name==='ask_user_question'){
  try{const value=JSON.parse(d.arguments);if(!Array.isArray(value.questions)||!value.questions.length)return null;
   return {id:`question:${d.callId}`,kind:'question',callId:d.callId,status:'requested',questions:value.questions.slice(0,20).map(q=>({id:q.id,question:clip(q.question),header:clip(q.header),detail:clip(q.detail),multiSelect:!!q.multi_select,options:(q.options||[]).slice(0,30).map(o=>({label:clip(o.label),description:clip(o.description)}))}))};
  }catch{return null;}
 }
 if(event.type==='tool/result'){
  const m=d.message||{};let value;try{value=JSON.parse(text(m));}catch{}
  return {id:`question:${m.toolCallId||m.callId}`,kind:'question',requiresExisting:true,status:m.isError?'error':value?.pending?'continued':Array.isArray(value?.answers)?'answered':'closed',...(Array.isArray(value?.answers)?{answers:value.answers}:{}),...(m.isError?{message:clip(text(m))}:{})};
 }
 if(event.type==='user/message'&&d.source?.kind==='user-question-reply'){
  let answers;try{answers=JSON.parse(text(d)).answers;}catch{}
  return {id:`question:${d.source.callId}`,kind:'question',requiresExisting:true,status:'answered',answers:Array.isArray(answers)?answers:[]};
 }
 return null;
}
export function mergeInteraction(items,fact){
 if(!fact)return items;
 const old=items.find(x=>x.id===fact.id);if(fact.requiresExisting&&!old)return items;
 const {requiresExisting,...value}=fact;
 return [...items.filter(x=>x.id!==fact.id),{...old,...value}].slice(-40);
}
export function interactionDefinitions(){
 return ['approval','question'].map(kind=>({
  kind:`friday-native-${kind}`,target:'chat',
  match:event=>{const fact=interactionFact(event);return fact?.kind===kind?{id:fact.id,role:fact.requiresExisting?'update':'start',exclusive:false}:null;},
  start:(_context,{event})=>({seq:event.seq,time:event.time,...interactionFact(event)}),
  update:(context,{event})=>({...context.state,...interactionFact(event)}),
  buildViewNode:context=>context.state&&context.start?{key:context.key,kind:'friday-native-interaction',id:context.id,target:'chat',anchorSeq:context.state.seq,location:context.start.location||{kind:'unresolved'},visibility:'visible',data:context.state}:null,
 }));
}
