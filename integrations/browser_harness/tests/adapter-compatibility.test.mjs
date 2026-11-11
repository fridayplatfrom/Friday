import test from 'node:test';
import assert from 'node:assert/strict';
import {activeTools,requestControls,StopSequences} from '../adapter-compatibility.mjs';
import {BrowserAdapter} from '../index.mjs';
import {SessionStore} from '../session-store.mjs';
import {prepareContext} from '../context.mjs';
import {buildContextTransfer,TOOL_PREFIX} from '../protocol.mjs';
import {ReplyDecoder} from '../protocol.mjs';

const collect=async stream=>{const chunks=[];for await(const chunk of stream)chunks.push(chunk);return chunks;};
const tool=name=>({name,parameters:{type:'object',properties:{}}});
const message=text=>({role:'user',content:[{type:'text',text}]});
function fixture(replies){
 const calls=[];let closed=0;
 const bridge={sessions:new SessionStore(),async *request(site,prompt,signal,meta){
   calls.push({site,prompt,meta});
   try{for(const reply of replies){signal?.throwIfAborted();if(reply instanceof Error)throw reply;yield reply;}}
   finally{closed++;}
 }};
 return {calls,bridge,adapter:new BrowserAdapter(bridge,{introduction:false}),get closed(){return closed;}};
}
const options={sessionId:'compat',provider:'browser-web',model:'chatgpt-web',messages:[message('Inspect the project')],tools:[tool('read'),tool('list')]};

test('all context paths preserve source forms and identities while excluding opaque replay data',()=>{
 const first={...message('Continue'),id:'msg-1',source:{kind:'model',form:'notice',summary:'Previous result',replayState:{private:'NEVER_FORWARD'}}};
 const input={...options,messages:[first]};const initial=prepareContext(input);
 assert.ok(initial.prompt.includes('msg-1'));assert.ok(initial.prompt.includes('Previous result'));assert.ok(!initial.prompt.includes('NEVER_FORWARD'));
 const next={...message('Another message'),id:'msg-2',source:{kind:'model',replayState:'SECRET'}};
 const incremental=prepareContext({...input,messages:[first,next]},initial.checkpoint);
 assert.equal(incremental.incremental,true);assert.ok(!incremental.prompt.includes('SECRET'));assert.ok(incremental.prompt.includes('msg-2'));
 const transfer=buildContextTransfer(input);assert.ok(!JSON.stringify(transfer).includes('NEVER_FORWARD'));
 const changed=prepareContext({...input,maxTokens:1024,messages:[first,next]},initial.checkpoint);
 assert.equal(changed.incremental,false);assert.ok(changed.prompt.includes('advisory'));
});

test('unsupported sampling controls fail before a website submission; maxTokens is explicitly advisory',async()=>{
 const f=fixture([{type:'done',text:'Done'}]);
 for(const overrides of [{temperature:0},{reasoningEffort:'high'},{maxTokens:0},{stop:['']},{stop:Array(17).fill('x')}]){
   await assert.rejects(collect(f.adapter.stream({...options,...overrides})));
 }
 assert.equal(f.calls.length,0);
 const chunks=await collect(f.adapter.stream({...options,maxTokens:1024}));
 assert.ok(f.calls[0].prompt.includes('"maxTokens":1024'));assert.ok(f.calls[0].prompt.includes('advisory'));
 assert.equal(chunks.some(x=>x.type==='usage'||x.type==='reasoning-delta'),false);
 assert.deepEqual(requestControls({}),{});
});

test('tool history activates deferred additions, removes tools, and binds replacement schemas',async()=>{
 const replacement={...tool('read'),description:'Replacement schema'};
 const history={tools:[tool('read'),{...tool('later'),deferLoading:true}],updates:[{messageId:'change',additions:[replacement,tool('later')]}]};
 const messages=[{id:'change',role:'developer',content:[{type:'tool-removal',toolName:'read'},{type:'tool-addition',toolName:'read'},{type:'tool-addition',toolName:'later'}]},
 {id:'remove',role:'developer',content:[{type:'tool-removal',toolName:'later'}]}];
 assert.deepEqual(activeTools({toolHistory:history,messages}),[replacement]);
 assert.deepEqual(activeTools({toolHistory:history,messages:[],tools:[tool('current')]}),[tool('current')]);
 const f=fixture([{type:'done',text:TOOL_PREFIX+JSON.stringify({name:'later',arguments:{}})}]);
 await assert.rejects(collect(f.adapter.stream({...options,messages,toolHistory:history})),/not offered/);
 const payload=JSON.parse(f.calls[0].prompt.slice(f.calls[0].prompt.indexOf('{"system":')));
 assert.deepEqual(payload.tools,[replacement]);assert.equal(payload.messages[0].role,'developer');
 assert.equal((await f.adapter.resolveModel('browser-web','chatgpt-web')).toolUpdate,'in-history');
});

test('independent tool batches emit indexed native blocks and unique call identities',async()=>{
 const body=[{name:'read',arguments:{}},{name:'list',arguments:{}}];
 const f=fixture([{type:'snapshot',text:TOOL_PREFIX+'['},{type:'done',text:TOOL_PREFIX+JSON.stringify(body)}]);
 const chunks=await collect(f.adapter.stream(options));
 assert.deepEqual(chunks.filter(x=>x.type==='block-start').map(x=>[x.index,x.blockType]),[[0,'tool-call'],[1,'tool-call']]);
 const blocks=chunks.filter(x=>x.type==='block-end');assert.equal(new Set(blocks.map(x=>x.block.id)).size,2);
 assert.deepEqual(blocks.map(x=>x.block.name),['read','list']);assert.equal(chunks.some(x=>x.type==='text-delta'),false);
 assert.equal(chunks.at(-1).reason.kind,'tool-calls');
});

test('a malformed or unauthorized batch emits no partial tool calls',async()=>{
 for(const body of [[],Array(9).fill({name:'read',arguments:{}}),[{name:'read',arguments:{}},{name:'unknown',arguments:{}}],
 [{name:'read',arguments:{}},{name:'list',arguments:[]}]] ){
   const f=fixture([{type:'done',text:TOOL_PREFIX+JSON.stringify(body)}]);const prepared=await f.adapter.prepareCall('browser-web','chatgpt-web');
   const chunks=await collect(prepared.stream(options));assert.equal(chunks.some(x=>x.type==='tool-call-delta'),false);
   assert.equal(chunks.at(-1).reason.kind,'error');assert.equal(f.calls.length,1);
 }
});

test('stop markers split across snapshots never leak, close transport and suppress following output',async()=>{
 const f=fixture([{type:'snapshot',text:'Hello <EN'},{type:'snapshot',text:'Hello <END> hidden'}, {type:'done',text:'UNREACHABLE'}]);
 const chunks=await collect(f.adapter.stream({...options,stop:['<END>']}));
 assert.equal(chunks.filter(x=>x.type==='text-delta').map(x=>x.text).join(''),'Hello ');
 assert.equal(chunks.find(x=>x.type==='block-end').block.text,'Hello ');assert.equal(chunks.at(-1).reason.kind,'stop');
 assert.equal(f.closed,1);assert.equal(f.calls.length,1);
 const unmatched=new StopSequences(['STOP']);assert.equal(unmatched.push('Hello ST'),'Hello ');assert.equal(unmatched.push('Hello ST',true),'Hello ST');
 const earliest=new StopSequences(['END','STOP']);assert.equal(earliest.push('a STOP b END',true),'a ');
});

test('stopping inside a tool request cannot execute or retry its truncated arguments',async()=>{
 const f=fixture([{type:'done',text:TOOL_PREFIX+'{"name":"read","arguments":{"value":"STOP hidden"}}'}]);
 const prepared=await f.adapter.prepareCall('browser-web','chatgpt-web');
 const chunks=await collect(prepared.stream({...options,stop:['STOP']}));
 assert.equal(chunks.some(x=>x.type==='tool-call-delta'),false);assert.equal(chunks.at(-1).reason.kind,'error');assert.equal(f.calls.length,1);
});

test('prepared calls preserve native failures and cancellation without automatic website replay',async()=>{
 const error=Object.assign(new Error('Compact before retrying'),{code:'FRIDAY_CONTEXT_LIMIT'});
 const f=fixture([error]);const prepared=await f.adapter.prepareCall('browser-web','chatgpt-web');
 let chunks=await collect(prepared.stream(options));assert.equal(chunks.at(-1).reason.failure.code,'CONTEXT_WINDOW_EXCEEDED');
 const abort=new AbortController();const cancelled=await f.adapter.prepareCall('browser-web','chatgpt-web',abort.signal);abort.abort();
 chunks=await collect(cancelled.stream(options));assert.equal(chunks.at(-1).reason.kind,'aborted');assert.equal(chunks.at(-1).reason.failure.code,'ABORTED');
 assert.equal(f.calls.length,1);assert.equal(f.adapter.providerRetryPolicy().maxRetries,0);
});

test('native compaction cannot take an image shortcut or execute task tools',async()=>{
 const f=fixture([{type:'done',text:'Summary: image task remains unfinished.'}]);
 await collect(f.adapter.stream({...options,purpose:'compaction',messages:[message('Create a dog image')]}));
 const payload=JSON.parse(f.calls[0].prompt.slice(f.calls[0].prompt.indexOf('{"system":')));
 assert.deepEqual(payload.tools,[]);assert.equal(payload.controls.purpose,'compaction');
 assert.ok(f.calls[0].prompt.includes('Create a dog image'));
});

test('literal fenced JSON preserves PowerShell dollars, backslashes and multiline arguments',async()=>{
 const command="$job='x'; Write-Output $job\nGet-Item C:\\demo";
 const text=TOOL_PREFIX+'```json\n'+JSON.stringify({name:'read',arguments:{command}})+'\n```';
 const f=fixture([{type:'done',text}]);const chunks=await collect(f.adapter.stream(options));
 assert.equal(JSON.parse(chunks.find(x=>x.type==='block-end').block.arguments).command,command);
 assert.equal(chunks.some(x=>x.type==='text-delta'),false);
 for(const body of ['```javascript\n{}\n```','```json\n{"name":"read","arguments":{}}\n```\nEXTRA']){
   const decoder=new ReplyDecoder(options.tools);decoder.push(TOOL_PREFIX+body);assert.throws(()=>decoder.finish(),/Invalid/);
 }
});

test('short transient placeholders and uncommitted tool rewrites never leak or execute earlier arguments',async()=>{
 const first=TOOL_PREFIX+'{"name":"read","arguments":{"path":"unfinished';
 const final=TOOL_PREFIX+'```json\n'+JSON.stringify({name:'read',arguments:{path:'verified.txt'}})+'\n```';
 const f=fixture([{type:'snapshot',text:'Verifying generated image'},{type:'snapshot',text:first},{type:'done',text:final}]);
 const chunks=await collect(f.adapter.stream(options));assert.equal(chunks.some(x=>x.type==='text-delta'),false);
 assert.equal(chunks.filter(x=>x.type==='tool-call-delta').length,1);
 assert.deepEqual(JSON.parse(chunks.find(x=>x.type==='block-end').block.arguments),{path:'verified.txt'});
 const ordinary=fixture([{type:'done',text:'Short final answer'}]);
 assert.equal((await collect(ordinary.adapter.stream(options))).find(x=>x.type==='block-end').block.text,'Short final answer');
});

test('already streamed prose cannot change into a tool request even with buffered-rewrite support',async()=>{
 const f=fixture([{type:'snapshot',text:'Ordinary visible answer. '.repeat(20)},{type:'done',text:TOOL_PREFIX+'{"name":"read","arguments":{}}'}]);
 const prepared=await f.adapter.prepareCall('browser-web','chatgpt-web');const chunks=await collect(prepared.stream(options));
 assert.equal(chunks.some(x=>x.type==='tool-call-delta'),false);assert.equal(chunks.at(-1).reason.kind,'error');
 assert.equal(f.calls.length,1);
});

test('native browser failures retain actionable sanitized diagnostics without stopping valid model continuation',async()=>{
 const f=fixture([{type:'done',text:'The browser policy needs the intended website origin.'}]);
 const chunks=await collect(f.adapter.stream({...options,messages:[...options.messages,{role:'tool',toolCallId:'denied',isError:true,content:[{type:'text',text:'Error: net::ERR_BLOCKED_BY_CLIENT PRIVATE_DETAIL'}]}]}));
 const issue=f.bridge.sessions.get(options.sessionId).lastToolIssue;
 assert.equal(issue.category,'browser-policy');assert.ok(!JSON.stringify(issue).includes('PRIVATE_DETAIL'));
 assert.equal(chunks.at(-1).reason.kind,'stop');assert.equal(f.calls.length,1);
});
