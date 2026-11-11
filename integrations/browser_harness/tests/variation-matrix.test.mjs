import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {ReplyDecoder,buildContextTransfer} from '../protocol.mjs';
import {consumeSSE} from '../ag-ui-client.mjs';
import {WebsiteTabManager} from '../extension/tab-manager.js';
import {FileStore,digest,CHUNK_BYTES} from '../file-store.mjs';
import {BrowserAdapter} from '../index.mjs';
import {SessionStore} from '../session-store.mjs';

const payloads=['plain','हिन्दी 🐕 中文','C:\\Users\\name\\a.txt',"$env:NAME; `literal` \"quotes\"",'line 1\nline 2\r\nend','```json\n{embedded:true}\n```'];
test('matrix: every tool-reply split preserves literal arguments without streaming executable text',()=>{
 let cases=0;
 for(const text of payloads)for(const fence of [true,false])for(const newline of ['\n','\r\n']){
  const call={name:'fixture',arguments:{text}},json=JSON.stringify(call);
  const reply='HARNESS_TOOL_CALL'+newline+(fence?'```json'+newline+json+newline+'```':json);
  for(let cut=0;cut<=reply.length;cut++){
   const decoder=new ReplyDecoder([{name:'fixture'}]);
   assert.equal(decoder.push(reply.slice(0,cut)),'');assert.equal(decoder.push(reply),'');
   assert.deepEqual(JSON.parse(decoder.finish().arguments),call.arguments);cases++;
  }
 }
 assert.ok(cases>2000);console.log('tool reply split variations:',cases);
});

test('matrix: UTF-8 task events survive every two-chunk byte boundary',async()=>{
 const expected=[{type:'TEXT_MESSAGE_CONTENT',delta:payloads.join(' | ')},{type:'RUN_FINISHED'}];
 const wire=Buffer.from(':heartbeat\r\n\r\n'+expected.map((event,i)=>`id: ${i+1}\r\ndata: ${JSON.stringify(event)}\r\n\r\n`).join(''));
 for(let cut=0;cut<=wire.length;cut++){
  const chunks=[wire.subarray(0,cut),wire.subarray(cut)];
  const response=new Response(new ReadableStream({pull(c){if(chunks.length)c.enqueue(chunks.shift());else c.close();}}),{headers:{'content-type':'text/event-stream'}});
  const received=[];assert.equal(await consumeSSE(response,{onEvent:(e,id)=>received.push({e,id})}),true);
  assert.deepEqual(received,expected.map((e,i)=>({e,id:i+1})));
 }
 console.log('SSE byte boundary variations:',wire.length+1);
});

test('matrix: saved chats reuse one tab across all providers, concurrent requests and changed Chrome tab IDs',async()=>{
 const urls={'chatgpt-web':'https://chatgpt.com/c/saved','deepseek-web':'https://chat.deepseek.com/a/chat/s/saved','gemini-web':'https://gemini.google.com/app/saved','kimi-web':'https://www.kimi.ai/chat/saved'};
 let cases=0;
 for(const [site,url]of Object.entries(urls))for(const mode of ['same-id','changed-id','closed','storage-cleared']){
  const task={site,sessionId:'matrix',conversationUrl:url},key=JSON.stringify(['matrix',site]);
  const values={harnessWebsitePairs:mode==='storage-cleared'?{}:{[key]:{...task,tabId:1,url}}};
  const tabs=new Map();if(mode!=='closed')tabs.set(mode==='same-id'?1:2,{id:mode==='same-id'?1:2,url,active:true});let created=0;
  const chrome={storage:{local:{async get(k){return structuredClone({[k]:values[k]});},async set(v){Object.assign(values,structuredClone(v));}}},tabs:{async get(id){if(!tabs.has(id))throw Error('No tab with id: '+id);return tabs.get(id);},async query(){return [...tabs.values()];},async create(props){created++;const tab={...props,id:100+created};tabs.set(tab.id,tab);return tab;}}};
  let manager=new WebsiteTabManager(chrome);
  const group=await Promise.all(Array.from({length:8},()=>manager.acquire(task)));
  assert.ok(group.every(result=>result.tab.id===group[0].tab.id));assert.equal(created,mode==='closed'?1:0);
  manager=new WebsiteTabManager(chrome);assert.equal((await manager.acquire(task)).tab.id,group[0].tab.id);
  assert.equal(created,mode==='closed'?1:0);cases++;
 }
 assert.equal(cases,16);console.log('provider/tab recovery scenarios:',cases);
});

test('matrix: context fragments round-trip Unicode and Markdown under multiple transport budgets',()=>{
 let cases=0;
 for(const size of [1,100,9000,25000])for(const budget of [4096,8192,80000]){
  const text=payloads.join('\n').repeat(size),options={tools:[],messages:[{role:'user',content:[{type:'text',text}]}]};
  if(text.length>1000000)continue;
  try{
   const transfer=buildContextTransfer(options,{maxChars:budget,transferId:'matrix'});
   const fragments=transfer.parts.map(part=>{assert.ok(part.prompt.length<=budget);return JSON.parse(part.prompt.split('FRIDAY_CONTEXT_PART_JSON\n')[1]).content;});
   assert.equal(JSON.parse(fragments.join('')).messages[0].content[0].text,text);cases++;
  }catch(error){assert.equal(error.code,'FRIDAY_CONTEXT_LIMIT');}
 }
 assert.ok(cases>=6);console.log('context budget round trips:',cases);
});

test('matrix: file transfers preserve bytes at each small chunk boundary and reject changed duplicates',()=>{
 const bytes=Buffer.from(payloads.join('\n'));
 for(let width=1;width<=bytes.length;width++){
  const store=new FileStore(),record=store.begin({sessionId:'matrix',name:'matrix.txt',size:bytes.length,sha256:digest(bytes)});
  let index=0;
  for(let offset=0;offset<bytes.length;offset+=width){const input={id:record.id,sessionId:'matrix',index:index++,data:bytes.subarray(offset,offset+width).toString('base64')};store.chunk(input);store.chunk(input);}
  assert.deepEqual(store.bytes(store.get(record.id,'matrix')),bytes);assert.equal(store.finish({id:record.id,sessionId:'matrix'}).sha256,digest(bytes));
  assert.throws(()=>store.chunk({id:record.id,sessionId:'matrix',index:0,data:Buffer.from('changed').toString('base64')}),/Conflicting/);
 }
 console.log('file chunk boundary variations:',bytes.length);
});

test('matrix: malformed durable file indexes are preserved and fail closed',t=>{
 const directory=mkdtempSync(join(tmpdir(),'friday-index-matrix-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));
 const file=join(directory,'index.json');
 for(const value of [[],null,7,'invalid',{bad:{id:'../../outside',sessionId:'matrix',chunks:[]}}]){
  const bytes=JSON.stringify(value);writeFileSync(file,bytes);
  assert.throws(()=>new FileStore(directory),/invalid|damaged/i);assert.equal(readFileSync(file,'utf8'),bytes);
 }
});

test('task observer completes a terminal event even when a proxy keeps the response open',async()=>{
 let streamController,cancelled=false;
 const response=new Response(new ReadableStream({start(c){streamController=c;c.enqueue(Buffer.from('id: 1\ndata: {"type":"RUN_FINISHED"}\n\n'));},cancel(){cancelled=true;}}),{headers:{'content-type':'text/event-stream'}});
 const read=consumeSSE(response,{onEvent(){}});let timer;
 const outcome=await Promise.race([read,new Promise(resolve=>{timer=setTimeout(()=>resolve('stalled'),100);})]);clearTimeout(timer);
 if(outcome==='stalled'){streamController.close();await read;}
 assert.equal(outcome,true);assert.equal(cancelled,true);
});

test('task observer stop cancels a stalled body read without requiring the server to send another byte',async()=>{
 let streamController,cancelled=false;
 const response=new Response(new ReadableStream({start(c){streamController=c;},cancel(){cancelled=true;}}),{headers:{'content-type':'text/event-stream'}});
 const abort=new AbortController(),read=consumeSSE(response,{signal:abort.signal,onEvent(){}});abort.abort();let timer;
 const outcome=await Promise.race([read,new Promise(resolve=>{timer=setTimeout(()=>resolve('stalled'),100);})]);clearTimeout(timer);
 if(outcome==='stalled'){streamController.close();await read;}
 assert.equal(outcome,false);assert.equal(cancelled,true);
});

test('file metadata cannot claim acceptance or completion after a failed durable save',t=>{
 const directory=mkdtempSync(join(tmpdir(),'friday-file-save-matrix-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));
 const store=new FileStore(directory),persist=store.persist.bind(store),bytes=Buffer.from('durable fixture');
 const input={id:'12345678-1234-4234-8234-123456789abc',sessionId:'matrix',name:'durable.txt',size:bytes.length,sha256:digest(bytes)};
 const fail=()=>{throw Error('simulated disk full');};store.persist=fail;
 assert.throws(()=>store.begin(input),/disk full/);assert.throws(()=>store.get(input.id,'matrix'),/not found/);
 store.persist=persist;store.begin(input);
 const chunk={id:input.id,sessionId:'matrix',index:0,data:bytes.toString('base64')};
 store.persist=fail;assert.throws(()=>store.chunk(chunk),/disk full/);assert.equal(store.get(input.id,'matrix').received,0);
 store.persist=persist;store.chunk(chunk);store.persist=fail;
 assert.throws(()=>store.finish(input),/disk full/);assert.equal(store.get(input.id,'matrix').status,'uploading');
 store.persist=persist;assert.equal(store.finish(input).status,'ready');assert.equal(new FileStore(directory).get(input.id,'matrix').status,'ready');
});

test('file status batches reject a foreign attachment without partially changing valid attachments',()=>{
 const store=new FileStore(),one=store.put('one','one.txt',Buffer.from('one')),two=store.put('two','two.txt',Buffer.from('two'));
 assert.throws(()=>store.mark([one.id,two.id],'one','cancelled'),/not found/);
 assert.equal(store.get(one.id,'one').status,'ready');assert.equal(store.get(two.id,'two').status,'ready');
 const persist=store.persist;store.persist=()=>{throw Error('simulated disk full');};
 assert.throws(()=>store.mark([one.id],'one','delivered'),/disk full/);assert.equal(store.get(one.id,'one').status,'ready');
 store.persist=persist;
});

test('file transfers cover empty files and the exact maximum chunk boundary',()=>{
 for(const size of [0,1,CHUNK_BYTES-1,CHUNK_BYTES,CHUNK_BYTES+1,2*CHUNK_BYTES+3]){
  const store=new FileStore(),bytes=Buffer.alloc(size,7),file=store.put('matrix','boundary.zip',bytes);
  assert.equal(file.status,'ready');assert.deepEqual(store.bytes(store.get(file.id,'matrix')),bytes);
 }
 const store=new FileStore(),bytes=Buffer.alloc(CHUNK_BYTES+1,7),file=store.begin({sessionId:'matrix',name:'too-large-chunk.zip',size:bytes.length,sha256:digest(bytes)});
 assert.throws(()=>store.chunk({id:file.id,sessionId:'matrix',index:0,data:bytes.toString('base64')}),/chunk/i);
 assert.equal(file.received,0);
});

test('matrix: all twelve provider switches and returns preserve native results and reject pending calls',async()=>{
 const providers=['chatgpt-web','deepseek-web','gemini-web','kimi-web'];let cases=0;
 const collect=async stream=>{for await(const _event of stream){}};
 for(const from of providers)for(const to of providers){
  if(from===to)continue;
  const sessions=new SessionStore(),requests=[],bridge={sessions,jobs:new Map(),journal:{append(){}},activity:{status(){}},async *request(site,prompt){requests.push({site,prompt});yield {type:'done',text:'Synthetic acknowledged answer'};}};
  const adapter=new BrowserAdapter(bridge,{introduction:false}),options={sessionId:'matrix',model:from,system:'Native approvals remain required.',tools:[{name:'fixture',parameters:{type:'object'}}],messages:[{role:'user',content:[{type:'text',text:'Continue the same workspace.'}]}]};
  await collect(adapter.stream(options));
  const call={role:'assistant',content:[{type:'tool-call',id:'actual-result',name:'fixture',arguments:'{}'}]};
  await assert.rejects(collect(adapter.stream({...options,model:to,messages:[...options.messages,call]})),/pending native tool/);assert.equal(requests.length,1);
  const messages=[...options.messages,call,{role:'tool',toolCallId:'actual-result',content:[{type:'text',text:'CONFIRMED_FILE_CREATED; do not create it twice.'}]}];
  await collect(adapter.stream({...options,model:to,messages}));
  assert.equal(requests.at(-1).site,to);assert.match(requests.at(-1).prompt,/CONFIRMED_FILE_CREATED/);assert.match(requests.at(-1).prompt,/Native approvals remain required/);
  await collect(adapter.stream({...options,messages:[...messages,{role:'user',content:[{type:'text',text:'Return without repeating the confirmed action.'}]}]}));
  assert.equal(sessions.get('matrix').activeProvider,from);assert.equal(sessions.get('matrix').handoffs.length,2);
  assert.ok(sessions.get('matrix').providerContexts[from]);assert.ok(sessions.get('matrix').providerContexts[to]);assert.equal(requests.length,3);cases++;
 }
 assert.equal(cases,12);console.log('provider switch-and-return variations:',cases);
});
