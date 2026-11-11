import test from 'node:test';
import assert from 'node:assert/strict';
import {emptyActivity,projectEvent,consumeSSE,observeRun} from '../ag-ui-client.mjs';

const encode=(id,event)=>`id: ${id}\r\ndata: ${JSON.stringify(event)}\r\n\r\n`;
function response(text,split=7){const bytes=new TextEncoder().encode(text);let offset=0;return new Response(new ReadableStream({pull(c){if(offset>=bytes.length)return c.close();c.enqueue(bytes.slice(offset,offset+=split));}}),{headers:{'content-type':'text/event-stream'}});}

test('browser projection restores exact tool identity, errors and screenshot state without duplicate events',()=>{
 const events=[{type:'RUN_STARTED'},{type:'TOOL_CALL_START',toolCallId:'one',toolCallName:'pwsh'},{type:'TOOL_CALL_ARGS',toolCallId:'one',delta:'{"command":"fixture"}'},{type:'TOOL_CALL_RESULT',toolCallId:'one',content:'denied',metadata:{friday:{isError:true}}},{type:'STATE_SNAPSHOT',snapshot:{friday:{phase:'executing',message:'Working',screenshots:[{id:'image',url:'/browser-models/media/uuid'}]}}},{type:'RUN_FINISHED',outcome:{type:'success'}}];
 const result=events.reduce((a,e,i)=>projectEvent(a,e,i+1),emptyActivity());
 assert.equal(result.phase,'completed');assert.equal(result.tools.length,1);assert.equal(result.tools[0].status,'error');assert.equal(result.tools[0].result,'denied');assert.equal(result.screenshots[0].id,'image');
 assert.equal(projectEvent(result,events[1],2),result);
 assert.equal(projectEvent(result,{type:'RUN_ERROR',code:'HARNESS_RESTARTED',message:'Review native history'},7).phase,'interrupted');
});

test('SSE parser preserves split Unicode and ignores heartbeat comments',async()=>{
 const events=[];
 await consumeSSE(response(': heartbeat\r\n\r\n'+encode(1,{type:'TEXT_MESSAGE_CONTENT',delta:'हेलो 🐕'})+encode(2,{type:'RUN_FINISHED'}),1),{onEvent:(e,id)=>events.push({e,id})});
 assert.equal(events[0].e.delta,'हेलो 🐕');assert.equal(events[1].id,2);
 await assert.rejects(consumeSSE(response(encode(1,{type:'RUN_STARTED'})),{onEvent:()=>{}}),/interrupted/);
});

test('observer reconnects from the last complete cursor and never submits or cancels tasks',async()=>{
 const requests=[],statuses=[],snapshots=[];
 const observer=observeRun({threadId:'thread',runId:'run',retryMs:1,onStatus:s=>statuses.push(s),onActivity:a=>snapshots.push(a),fetchImpl:async(url,options)=>{
  requests.push({url,options});return requests.length===1?response(encode(4,{type:'RUN_STARTED'})+encode(5,{type:'TOOL_CALL_START',toolCallId:'a',toolCallName:'browser'})):response(encode(6,{type:'TOOL_CALL_RESULT',toolCallId:'a',content:'42'})+encode(7,{type:'RUN_FINISHED',outcome:{type:'success'}}));
 }});
 await observer.done;
 assert.equal(requests.length,2);assert.match(requests[1].url,/after=5$/);assert.equal(requests[0].options.method,undefined);assert.equal(requests[0].options.credentials,'same-origin');
 assert.equal(snapshots.at(-1).tools[0].result,'42');assert.ok(statuses.some(s=>s.includes('reconnecting')));assert.equal(statuses.at(-1),'');
});

test('fresh UI observer replays persisted events while unmount aborts only the observer',async()=>{
 let called=false;
 const observer=observeRun({threadId:'thread',runId:'run',onStatus:()=>{},onActivity:()=>{},fetchImpl:async(url,{signal})=>{called=true;assert.match(url,/after=0$/);return new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted')),{once:true}));}});
 observer.stop();await observer.done;assert.equal(called,true);
});
