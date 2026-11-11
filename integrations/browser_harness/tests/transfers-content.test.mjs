import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {File} from 'node:buffer';
import {webcrypto,randomUUID} from 'node:crypto';
import {FileStore} from '../file-store.mjs';

const script=readFileSync(new URL('../extension/transfers.js',import.meta.url),'utf8');
function page({picker=true,rejected=false,processing=false,confirm=true,hiddenForm=false,reportedNames=null}={}){
 const store=new FileStore();const handlers={};const saved=new Map();const events=[];const input={files:[],dispatchEvent(){this.changed=true;}};
 const runtime={async sendMessage(message){
   if(message.type==='harness-download-watch')return {ok:true,available:false};
   if(message.type==='harness-job-file')return {ok:true,result:store.readChunk(message.id,'one',message.index)};
   const data={...message.input,sessionId:'one'};return {ok:true,result:message.action==='begin'?store.public(store.begin({...data,direction:'from-website'})):message.action==='chunk'?store.chunk(data):store.finish(data)};
 }};
 const hiddenInput={files:[],dispatchEvent(){throw new Error('Hidden composer selected');},getAttribute:()=>null};
 const form={querySelector:()=>picker?input:null,querySelectorAll(selector){return selector==='input[type="file"]'?(picker?[input]:[]):document.querySelectorAll(selector);}};
 input.closest=()=>form;
 const editor={getClientRects:()=>[1],closest:()=>form};
 let observed;
 const document={addEventListener(type,handler){handlers[type]=handler;},removeEventListener(type){delete handlers[type];},querySelector(selector){return selector==='input[type="file"]'&&picker?input:null;},querySelectorAll(selector){
   if(selector==='#prompt-textarea')return hiddenForm?[{getClientRects:()=>[],closest:()=>null},editor]:[];
   if(selector==='input[type="file"]')return picker?(hiddenForm?[hiddenInput,input]:[input]):[];
   if(selector.includes('progressbar'))return processing?[{getClientRects:()=>[1]}]:[];
   return confirm&&input.changed?[{innerText:rejected?'Upload failed':(reportedNames||input.files.map(file=>file.name)).join(' '),getAttribute:()=>''}]:[];
 }};
 const context={document,setTimeout,clearTimeout,MutationObserver:class{constructor(callback){observed=callback;}observe(){}disconnect(){}},getComputedStyle:()=>({visibility:'visible'}),crypto:webcrypto,File,Blob,Uint8Array,Set,Map,URL,Event:class{},location:{origin:'https://chatgpt.com',href:'https://chatgpt.com/c/test',pathname:'/c/test'},
   sessionStorage:{getItem:key=>saved.get(key),setItem:(key,value)=>saved.set(key,value)},
   chrome:{runtime},btoa:text=>Buffer.from(text,'binary').toString('base64'),atob:text=>Buffer.from(text,'base64').toString('binary'),
   DataTransfer:class{constructor(){this.files=[];this.items={add:file=>this.files.push(file)};}},fetch:async()=>({ok:true,headers:{get:()=>null},blob:async()=>new Blob(['report bytes'],{type:'application/pdf'})})};
 vm.runInNewContext(script,context);return {api:context.HarnessFiles,store,input,events,handlers,downloadAnchor:anchor=>observed([{addedNodes:[anchor]}]),sendEvent:async event=>events.push(event),sleep:async()=>{}};
}

test('outbound attachment is reconstructed from verified chunks and sent to the website file input',async()=>{
 const f=page();const record=f.store.put('one','notes.txt',Buffer.from('original bytes'));
 await f.api.upload({id:'job',attachments:[record]},f.sendEvent,f.sleep);
 assert.equal(await f.input.files[0].text(),'original bytes');assert.equal(f.input.files[0].name,'notes.txt');assert.equal(f.events[0].state,'uploading');
});
test('upload selects the visible composer form when ChatGPT retains a hidden home composer',async()=>{
 const f=page({hiddenForm:true});const record=f.store.put('one','notes.txt',Buffer.from('visible form bytes'));
 await f.api.upload({id:'job',preset:{composer:['#prompt-textarea']},attachments:[record]},f.sendEvent,f.sleep);
 assert.equal(await f.input.files[0].text(),'visible form bytes');
});
test('website duplicate-name suffixes are accepted but every upload needs a distinct reported filename',async()=>{
 for(const name of ['notes(1).txt','notes (2).txt']){
   const f=page({reportedNames:[name]});const record=f.store.put('one','notes.txt',Buffer.from('bytes'));
   await f.api.upload({id:'job',attachments:[record]},f.sendEvent,f.sleep);
 }
 const missing=page({reportedNames:['notes(1).txt']});
 const records=['notes.txt','notes(1).txt'].map(name=>missing.store.put('one',name,Buffer.from('bytes')));
 await assert.rejects(missing.api.upload({id:'job',attachments:records},missing.sendEvent,missing.sleep),/did not confirm/);
 const distinct=page({reportedNames:['notes(1).txt','notes(2).txt']});
 const files=['notes.txt','notes.txt'].map(name=>distinct.store.put('one',name,Buffer.from('bytes')));
 await distinct.api.upload({id:'job',attachments:files},distinct.sendEvent,distinct.sleep);
 const wrong=page({reportedNames:['other-notes.txt']});
 await assert.rejects(wrong.api.upload({id:'job',attachments:[wrong.store.put('one','notes.txt',Buffer.from('bytes'))]},wrong.sendEvent,wrong.sleep),/did not confirm/);
});
test('missing picker, rejected upload and unconfirmed processing fail without sending a prompt',async()=>{
 for(const opts of [{picker:false},{rejected:true},{processing:true},{confirm:false}]){
   const f=page(opts);const record=f.store.put('one','notes.txt',Buffer.from('bytes'));
   await assert.rejects(f.api.upload({id:'job',attachments:[record]},f.sendEvent,f.sleep),/picker|rejected|confirm/);
 }
});
test('changed website-selected files retain original bytes in the local attachment store',async()=>{
 const f=page();f.api.init();f.handlers.change({isTrusted:true,target:{type:'file',files:[new File(['image bytes'],'photo.png',{type:'image/png'})]}});
 const ids=await f.api.take();assert.equal(ids.length,1);assert.equal(f.store.bytes(f.store.get(ids[0],'one')).toString(),'image bytes');assert.equal((await f.api.take()).length,0);
});
test('visible generated download is stored, while unreadable or unknown output gets manual fallback',async()=>{
 const f=page();const warnings=[];
 const links=[{href:'blob:https://chatgpt.com/output',getAttribute:()=> 'report.pdf',innerText:'report.pdf'},
 {href:'https://other.example/output',getAttribute:()=> 'other.zip',innerText:'other.zip'},
 {href:'blob:https://chatgpt.com/unknown',getAttribute:()=> '',innerText:'Download'}];
 const files=await f.api.collectDownloads({querySelectorAll:()=>links},'job',text=>warnings.push(text));
 assert.equal(files.length,1);assert.equal(files[0].name,'report.pdf');assert.equal(warnings.length,2);
});
test('a native download button can expose a transient website-provided blob anchor without extra permissions',async()=>{
 const f=page(),warnings=[];let clicked=0;
 const preview={getAttribute:()=> 'Open preview of report.pdf'};
 const button={getClientRects:()=>[1],click(){clicked++;f.downloadAnchor({href:'blob:https://chatgpt.com/report',getAttribute:()=> 'report.pdf',matches:()=>true,querySelectorAll:()=>[]});}};
 const turn={querySelectorAll:selector=>selector==='button[aria-label="Download file"]'?[button]:selector==='button[aria-label^="Open preview of "]'?[preview]:[]};button.parentElement=turn;
 const files=await f.api.collectDownloads(turn,'job',message=>warnings.push(message));
 assert.equal(clicked,1);assert.equal(files[0].name,'report.pdf');assert.equal(warnings.length,0);assert.equal(f.handlers.click,undefined);
});
