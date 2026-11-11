import test from 'node:test';
import assert from 'node:assert/strict';
import {buildContextTransfer,TOOL_PREFIX} from '../protocol.mjs';
import {prepareContext} from '../context.mjs';
import {BrowserAdapter} from '../index.mjs';
import {SessionStore} from '../session-store.mjs';

const frame=part=>JSON.parse(part.prompt.split('\nFRIDAY_CONTEXT_PART_JSON\n')[1]);
const collect=async stream=>{const result=[];for await(const chunk of stream)result.push(chunk);return result;};
const large=()=>({sessionId:'long-task',model:'chatgpt-web',system:'Harness owns permissions. Keep original constraints.',tools:[{name:'read',parameters:{type:'object',properties:{path:{type:'string'}},required:['path']},description:'Detailed tool reference '.repeat(2000)}],messages:[{role:'user',content:[{type:'text',text:'Preserve every instruction. '+ 'Unicode 🐾, quotes " and escapes \\ '.repeat(3000)}]}]});

test('multipart context is lossless, bounded per message, and keeps exact schemas and user instructions',()=>{
 const input=large();const before=JSON.stringify(input);const transfer=buildContextTransfer(input,{transferId:'test-transfer'});
 assert.ok(transfer.parts.length>1);assert.ok(transfer.parts.every(part=>part.prompt.length<=80000));
 const frames=transfer.parts.map(frame);assert.deepEqual(frames.map(x=>x.part),frames.map((_,i)=>i+1));
 assert.ok(frames.every(x=>x.total===frames.length&&x.transferId==='test-transfer'));
 const restored=JSON.parse(frames.map(x=>x.content).join(''));
 assert.deepEqual(restored,{system:input.system,tools:input.tools,messages:input.messages});
 assert.equal(JSON.stringify(input),before);assert.ok(transfer.parts.every(part=>part.prompt.includes('Do not act')));
 assert.match(transfer.prompt,/test-transfer is complete/);
});

test('oversized envelopes use transfer fallback, but unsupported blocks and total-budget violations fail explicitly',()=>{
 const prepared=prepareContext(large());assert.ok(prepared.parts.length>1);assert.equal(prepared.incremental,false);
 assert.throws(()=>prepareContext({model:'chatgpt-web',messages:[{role:'user',content:[{type:'image'}]}]}),/text only/);
 assert.throws(()=>buildContextTransfer(large(),{maxTotalChars:100}),error=>error.code==='FRIDAY_CONTEXT_LIMIT'&&/Harness Compact/.test(error.message));
 assert.throws(()=>buildContextTransfer(large(),{maxChars:10}),/Invalid/);
});

function harness({badAck=false,abort}={}) {
 const calls=[];const bridge={sessions:new SessionStore(),async *request(site,prompt,signal,options){
   signal?.throwIfAborted();calls.push({prompt,...options});
   if(options.purpose==='context'){
     if(abort){abort.abort();signal.throwIfAborted();}
     const ack=prompt.match(/Reply ONLY with exactly: ([^\n]+)/)?.[1];
     yield {type:'done',text:badAck?TOOL_PREFIX+'{"name":"read","arguments":{"path":"never.txt"}}':ack};
   }else yield {type:'done',text:TOOL_PREFIX+'{"name":"read","arguments":{"path":"goodbowl-store/QA.md"}}'};
 }};
 return {bridge,calls,adapter:new BrowserAdapter(bridge,{introduction:false})};
}

test('Harness receives only the final validated tool call after all context parts acknowledge',async()=>{
 const f=harness(),options=large();const chunks=await collect(f.adapter.stream(options));
 assert.ok(f.calls.length>2);assert.ok(f.calls.slice(0,-1).every(call=>call.purpose==='context'));
 assert.equal(f.calls.at(-1).purpose,'task');
 const call=chunks.find(chunk=>chunk.type==='block-end').block;assert.equal(call.name,'read');
 assert.deepEqual(JSON.parse(call.arguments),{path:'goodbowl-store/QA.md'});
 assert.equal(chunks.filter(chunk=>chunk.type==='tool-call-delta').length,1);
 assert.equal(chunks.some(chunk=>chunk.type==='text-delta'),false,'acknowledgements are not assistant replies');
 assert.ok(f.bridge.sessions.get(options.sessionId).contextCheckpoint);
 const next=prepareContext({...options,messages:[...options.messages,{role:'assistant',content:[{type:'text',text:'Read completed'}]},{role:'user',content:[{type:'text',text:'Continue'}]}]},f.bridge.sessions.get(options.sessionId).contextCheckpoint);
 assert.equal(next.incremental,true);assert.equal(next.parts,undefined);
});

test('bad context acknowledgement, including a tool prefix, prevents task commit and checkpoint advancement',async()=>{
 const f=harness({badAck:true});await assert.rejects(collect(f.adapter.stream(large())),/not acknowledged/);
 assert.equal(f.calls.length,1);assert.equal(f.calls[0].purpose,'context');assert.equal(f.bridge.sessions.get('long-task').contextCheckpoint,undefined);
});

test('cancellation during context transfer cannot commit or replay a task',async()=>{
 const abort=new AbortController(),f=harness({abort});await assert.rejects(collect(f.adapter.stream({...large(),signal:abort.signal})),{name:'AbortError'});
 assert.equal(f.calls.length,1);assert.equal(f.calls[0].purpose,'context');assert.equal(f.bridge.sessions.get('long-task').contextCheckpoint,undefined);
});
