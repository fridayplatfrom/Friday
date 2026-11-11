import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,rmSync,readFileSync,appendFileSync,writeFileSync } from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {setTimeout as delay} from 'node:timers/promises';
import {FileStore,digest,CHUNK_BYTES,FILE_TYPES,MAX_FILE_BYTES} from '../file-store.mjs';
import {DeliveryJournal} from '../journal.mjs';
import {prepareContext} from '../context.mjs';
import {BrowserBridge} from '../bridge.mjs';
import {BrowserAdapter} from '../index.mjs';
import {SessionStore} from '../session-store.mjs';
import {readNativeFile,captureNativeFiles,restoreNativeFiles} from '../native-attachments.mjs';

const collect=async iterable=>{const events=[];for await(const event of iterable)events.push(event);return events;};
const directory=t=>{const dir=mkdtempSync(join(tmpdir(),'harness-files-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));return dir;};

test('all supported file extensions preserve original bytes, digest and download metadata',()=>{
 const store=new FileStore();for(const ext of Object.keys(FILE_TYPES)){const bytes=Buffer.from('opaque test bytes');const file=store.put('one','sample.'+ext,bytes);
 assert.equal(file.sha256,digest(bytes));assert.deepEqual(store.bytes(store.get(file.id,'one')),bytes);assert.equal(file.mime,FILE_TYPES[ext]);}
});
test('a chunk transfer resumes across restart; duplicate chunks are idempotent and conflicts fail',t=>{
 const dir=directory(t);let store=new FileStore(dir);const bytes=Buffer.alloc(CHUNK_BYTES+50,6);const input={id:randomUUID(),sessionId:'one',name:'project.zip',size:bytes.length,sha256:digest(bytes)};
 store.begin(input);const chunk={id:input.id,sessionId:'one',index:0,data:bytes.subarray(0,CHUNK_BYTES).toString('base64')};store.chunk(chunk);
 store=new FileStore(dir);assert.equal(store.begin(input).chunks.length,1);store.chunk(chunk);
 assert.throws(()=>store.chunk({...chunk,data:Buffer.from('different').toString('base64')}),/Conflicting/);
 assert.throws(()=>store.finish(input),/integrity/);store.chunk({...chunk,index:1,data:bytes.subarray(CHUNK_BYTES).toString('base64')});
 const file=store.finish(input);assert.equal(file.status,'ready');assert.deepEqual(readFileSync(store.path(file.id,'one')),bytes);
 assert.equal(new FileStore(dir).finish(input).sha256,digest(bytes));
});
test('transfer validation rejects traversal, executables, oversized files, foreign sessions, and reordered chunks',()=>{
 const store=new FileStore();const input={sessionId:'one',name:'a.txt',size:3,sha256:digest(Buffer.from('abc'))};
 for(const name of ['../a.txt','C:\\secret.txt','evil.exe','bad/name.pdf'])assert.throws(()=>store.begin({...input,name}));
 assert.throws(()=>store.begin({...input,size:MAX_FILE_BYTES+1}));
 const record=store.begin(input);assert.throws(()=>store.get(record.id,'two'),/not found/);
 assert.throws(()=>store.chunk({id:record.id,sessionId:'one',index:1,data:'YWJj'}),/order/);
 assert.throws(()=>store.begin({...input,id:record.id,name:'other.txt'}),/conflict/);
});
test('delivery journal retains full context and interrupted work across restarts without replaying it',t=>{
 const dir=directory(t);let journal=new DeliveryJournal(dir);journal.append('one','request',{id:'a',prompt:'Original task'});journal.append('one','submitted',{id:'a',turnKey:'turn-a'});
 journal.append('two','request',{id:'b',prompt:'Other task'});journal.append('two','complete',{id:'b',text:'Done'});
 journal=new DeliveryJournal(dir);assert.equal(journal.interrupted().length,1);assert.equal(journal.list('one')[0].data.prompt,'Original task');
});
test('a crash mid-journal-append preserves complete entries and saves the incomplete tail',t=>{
 const dir=directory(t);new DeliveryJournal(dir).append('one','request',{id:'a'});appendFileSync(join(dir,'delivery.jsonl'),'{"partial":');
 const restored=new DeliveryJournal(dir);assert.equal(restored.events.length,1);assert.equal(readFileSync(join(dir,'delivery.jsonl.interrupted-tail'),'utf8'),'{"partial":');
 restored.append('one','complete',{id:'a'});assert.equal(new DeliveryJournal(dir).interrupted().length,0);
});
test('damaged pairing metadata is never silently replaced by empty state',t=>{
 const dir=directory(t);writeFileSync(join(dir,'sessions.json'),'{broken');assert.throws(()=>new SessionStore(dir),/no state was erased/);
});
test('context sends only new messages after confirmed prefix; changed tools or rewritten history use a full snapshot',()=>{
 const options={model:'chatgpt-web',tools:[{name:'write'}],system:'Keep paths inside workspace',messages:[{role:'user',content:[{type:'text',text:'Build it'}]}]};
 const first=prepareContext(options);const next={...options,messages:[...options.messages,{role:'tool',content:[{type:'text',text:'Created file'}]}]};
 assert.equal(prepareContext(next,first.checkpoint).incremental,true);
 assert.ok(!prepareContext(next,first.checkpoint).prompt.includes('Keep paths inside workspace'));
 assert.equal(prepareContext({...next,tools:[]},first.checkpoint).incremental,false);
 assert.equal(prepareContext({...next,messages:[{role:'user',content:[{type:'text',text:'Different'}]}]},first.checkpoint).incremental,false);
});

async function fixture(t){const token='test-harness-file-token-at-least-32-characters';const bridge=await new BrowserBridge({token,port:0,stateDirectory:directory(t)}).start();t.after(()=>bridge.close());
 const post=async(path,input)=>{const response=await fetch(`http://127.0.0.1:${bridge.port}${path}`,{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(input)});return {status:response.status,body:await response.json()};};
 const next=async()=>{for(let i=0;i<100;i++){const result=await post('/poll',{version:'0.4.0',sites:['chatgpt-web']});if(result.body.commands.length)return result.body.commands[0];await delay(10);}throw new Error('No job');};return {bridge,post,next};}

test('durable generated images use the native filesystem image renderer and retain per-image progress on later turns',async t=>{
 const {bridge,post,next}=await fixture(t);
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({model:'chatgpt-web',sessionId:'image-path',messages:[{role:'user',content:[{type:'text',text:'Create a fox image'}]}]}));
 const job=await next();assert.equal(job.purpose,'image');
 const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jp1sAAAAASUVORK5CYII=','base64');
 for(const percent of [18,68])await post('/event',{id:job.id,type:'progress',percent});
 await post('/event',{id:job.id,type:'image-start',mime:'image/png'});
 await post('/event',{id:job.id,type:'image-chunk',index:0,data:png.toString('base64')});
 await post('/event',{id:job.id,type:'image-end'});await post('/event',{id:job.id,type:'done',text:''});
 const image=bridge.sessions.get('image-path').images[0],path=bridge.sessions.imagePath(image.id);
 assert.deepEqual(readFileSync(path),png);
 assert.ok((await result).find(chunk=>chunk.type==='block-end').block.text.includes('(<'+path.replace(/\\/g,'/')+'>)'));
 const followup=collect(bridge.request('chatgpt-web','another text request',undefined,{sessionId:'image-path'}));
 const second=await next();assert.deepEqual(bridge.sessions.get('image-path').progress,[]);
 assert.deepEqual(bridge.sessions.get('image-path').images[0].progress.map(item=>item.percent),[18,68]);
 await post('/event',{id:second.id,type:'done',text:'Done'});await followup;
});
test('staged files are dispatched, bytes are job-scoped, and submission acknowledgement marks delivery',async t=>{
 const {bridge,post,next}=await fixture(t);const file=bridge.files.put('one','hello.txt',Buffer.from('hello file'));
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({sessionId:'one',model:'chatgpt-web',messages:[{role:'user',content:[{type:'text',text:'Read the attachment'}]}]}));
 const job=await next();assert.equal(job.attachments[0].name,'hello.txt');
 assert.equal((await post('/job-file',{jobId:'wrong',id:file.id,index:0})).status,400);
 const chunk=await post('/job-file',{jobId:job.id,id:file.id,index:0});assert.equal(Buffer.from(chunk.body.data,'base64').toString(),'hello file');
 await post('/event',{id:job.id,type:'submitted',eventId:randomUUID(),turnKey:'turn'});
 assert.equal(bridge.files.get(file.id,'one').status,'delivered');
 const final={id:job.id,eventId:randomUUID(),type:'done',text:'I read hello file.'};await post('/event',final);await result;
 assert.equal((await post('/event',final)).body.duplicate,true,'lost final acknowledgements cannot duplicate a turn');
});
test('native image attachments use real bytes and a textual reference, never base64 inside the model prompt',async t=>{
 const {bridge,post,next}=await fixture(t);bridge.readImage=async()=>({mediaType:'image/png',data:Buffer.from('image bytes')});
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({sessionId:'one',model:'chatgpt-web',messages:[{role:'user',content:[{type:'text',text:'Inspect screenshot'},{type:'image',attachment:{attachmentId:'image-id'}}]}]}));
 const job=await next();assert.equal(job.attachments.length,1);assert.ok(job.prompt.includes('screenshot-'));assert.ok(!job.prompt.includes(Buffer.from('image bytes').toString('base64')));
 await post('/event',{id:job.id,type:'submitted'});await post('/event',{id:job.id,type:'done',text:'Screenshot received'});await result;
});

test('native Harness document attachments use its file service and are not reuploaded in later history',async t=>{
 const {bridge,post,next}=await fixture(t);const bytes=Buffer.from('synthetic document bytes');let reads=0;
 bridge.readFile=async ref=>{reads++;assert.equal(ref.name,'notes.pdf');return bytes;};
 const messages=[{role:'user',content:[{type:'text',text:'Read the attached document'},{type:'file',attachment:{attachmentId:'sha256:synthetic-file',name:'notes.pdf',bytes:bytes.length}}]}];
 const adapter=new BrowserAdapter(bridge,{introduction:false});
 let result=collect(adapter.stream({sessionId:'native-doc',model:'chatgpt-web',messages}));let job=await next();
 assert.equal(job.attachments.length,1);assert.equal(job.attachments[0].name,'notes.pdf');
 assert.deepEqual(bridge.files.bytes(bridge.files.get(job.attachments[0].id,'native-doc')),bytes);
 assert.ok(job.prompt.includes('File attachment: notes.pdf'));assert.ok(!job.prompt.includes(bytes.toString('base64')));
 await post('/event',{id:job.id,type:'submitted'});await post('/event',{id:job.id,type:'done',text:'Read document'});await result;
 messages.push({role:'assistant',content:[{type:'text',text:'Read document'}]},{role:'user',content:[{type:'text',text:'Summarize it'}]});
 result=collect(adapter.stream({sessionId:'native-doc',model:'chatgpt-web',messages}));job=await next();
 assert.equal(job.attachments.length,0);assert.equal(reads,1);
 await post('/event',{id:job.id,type:'done',text:'Summary'});await result;
});

test('native verified file streams reject oversize, incomplete, corrupt and cancelled reads before submission',async()=>{
 const service={async *readFileStream(){yield Buffer.from('ab');yield Buffer.from('cd');}};
 assert.equal((await readNativeFile(service,{bytes:4})).toString(),'abcd');
 await assert.rejects(readNativeFile(service,{bytes:MAX_FILE_BYTES+1}),/32 MB/);
 await assert.rejects(readNativeFile(service,{bytes:5}),/incomplete/);
 await assert.rejects(readNativeFile(service,{bytes:2}),/size mismatch/);
 await assert.rejects(readNativeFile({async *readFileStream(){yield Buffer.from('ab');throw new Error('Native digest mismatch');}},{bytes:2}),/digest mismatch/);
 const abort=new AbortController();abort.abort();await assert.rejects(readNativeFile(service,{bytes:4},abort.signal),{name:'AbortError'});
});

test('actual Harness file-to-text projection is bridged only with the original admitted identity and exact host placeholder',async t=>{
 const {bridge,post,next}=await fixture(t);const bytes=Buffer.from('native fixture code 7612');
 const ref={attachmentId:'sha256:fixture',name:'fixture.txt',bytes:bytes.length};
 const original={provider:'browser-web',model:'chatgpt-web',sessionId:'native-pipeline',messages:[{id:'human-1',role:'user',content:[{type:'file',attachment:ref},{type:'text',text:'Read the native file'}]}]};
 const placeholder='[File "fixture.txt": verbatim read-only copy saved at "C:/native/fixture.txt".]';
 captureNativeFiles(bridge,original,{fileRequestText:r=>{assert.equal(r,ref);return placeholder;}});
 const projected={...original,messages:[{...original.messages[0],content:[{type:'text',text:placeholder},original.messages[0].content[1]]}]};
 assert.equal(projected.messages[0].content[0].type,'text');
 assert.equal(restoreNativeFiles(bridge,{...projected,sessionId:'other-session'}).messages[0].content[0].type,'text');
 assert.equal(restoreNativeFiles(bridge,{...projected,messages:[{...projected.messages[0],id:'forged'}]}).messages[0].content[0].type,'text');
 assert.equal(restoreNativeFiles(bridge,{...projected,messages:[{...projected.messages[0],content:[{type:'text',text:placeholder+' altered'}]}]}).messages[0].content[0].type,'text');
 bridge.readFile=async received=>{assert.equal(received,ref);return bytes;};
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream(projected));const job=await next();
 assert.equal(job.attachments.length,1);assert.equal(job.attachments[0].name,'fixture.txt');assert.ok(!job.prompt.includes('C:/native'));
 await post('/event',{id:job.id,type:'submitted'});await post('/event',{id:job.id,type:'done',text:'7612'});await result;
});
test('downloaded website files become persistent native reply links',async t=>{
 const {bridge,post,next}=await fixture(t);const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({sessionId:'one',model:'chatgpt-web',messages:[]}));const job=await next();
 const bytes=Buffer.from('%PDF-example');const input={jobId:job.id,id:randomUUID(),name:'report.pdf',size:bytes.length,sha256:digest(bytes)};
 await post('/files/begin',input);await post('/files/chunk',{...input,index:0,data:bytes.toString('base64')});const saved=await post('/files/finish',input);
 await post('/event',{id:job.id,type:'file',fileId:input.id});await post('/event',{id:job.id,type:'done',text:'Report ready'});
 const events=await result;assert.ok(events.find(e=>e.type==='block-end').block.text.includes(saved.body.url));
});

test('a lost worker is offered capture recovery with the same job id, never a fresh submission',async t=>{
 const {bridge,post,next}=await fixture(t);const result=collect(bridge.request('chatgpt-web','Original task',undefined,{sessionId:'one'}));
 const job=await next();bridge.jobs.get(job.id).lastDispatchAt=Date.now()-11000;
 const recovered=await post('/poll',{sites:['chatgpt-web'],runningIds:[]});assert.equal(recovered.body.commands[0].id,job.id);assert.equal(recovered.body.commands[0].resume,true);
 await post('/event',{id:job.id,type:'done',text:'Captured same response'});await result;
});

test('accepted final-event receipts survive a backend restart',async t=>{
 const {bridge,post,next}=await fixture(t);const result=collect(bridge.request('chatgpt-web','Task',undefined,{sessionId:'one'}));const job=await next();
 const event={id:job.id,eventId:randomUUID(),type:'done',text:'Saved response'};await post('/event',event);await result;
 const restored=new BrowserBridge({token:'another-test-token-at-least-32-characters',port:0,stateDirectory:bridge.sessions.directory});
 assert.ok(restored.eventReceipts.has(`${job.id}:${event.eventId}`));assert.equal(restored.journal.list('one').find(e=>e.type==='complete').data.text,'Saved response');
});

test('an old extension cannot silently submit a file request without its attachment',async t=>{
 const {bridge,post}=await fixture(t);const file=bridge.files.put('one','notes.txt',Buffer.from('data'));
 const result=collect(bridge.request('chatgpt-web','Read this',undefined,{sessionId:'one',attachments:[file]}));
 const rejected=assert.rejects(result,/Reload Friday/);
 const poll=await post('/poll',{version:'0.3.4',sites:['chatgpt-web']});assert.equal(poll.body.commands.length,0);await rejected;
 assert.equal(bridge.files.get(file.id,'one').status,'ready');
});

test('a website-origin tool continuation does not consume files staged for the next Harness message',async t=>{
 const {bridge,post,next}=await fixture(t);const file=bridge.files.put('one','private-notes.txt',Buffer.from('staged for later'));
 bridge.sessions.update('one',{webActiveId:'website-human'});
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({sessionId:'one',model:'chatgpt-web',messages:[
 {role:'user',source:{kind:'user',rpcId:'website-human'},content:[{type:'text',text:'A website task'}]},
 {role:'tool',content:[{type:'text',text:'Actual tool result'}]}]}));
 const job=await next();assert.equal(job.attachments.length,0);await post('/event',{id:job.id,type:'done',text:'Done'});await result;
 assert.equal(bridge.files.get(file.id,'one').status,'ready');
});
