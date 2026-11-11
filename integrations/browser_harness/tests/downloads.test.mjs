import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,mkdirSync,rmSync,realpathSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname,basename} from 'node:path';
import {FileStore} from '../file-store.mjs';
import {importBrowserDownload} from '../download-import.mjs';
import {BrowserDownloadWatch} from '../extension/download-watch.js';
import {BrowserBridge} from '../bridge.mjs';

function disk(t){const parent=realpathSync(tmpdir()),dir=realpathSync(mkdtempSync(join(parent,'harness-download-')));
 assert.equal(dirname(dir),parent);assert.ok(basename(dir).startsWith('harness-download-'));
 t.after(()=>rmSync(dir,{recursive:true,force:true}));return dir;}
const pair={url:'https://chatgpt.com/c/test'};
test('only a new completed file inside Downloads can be imported; original bytes and receipts are retained',t=>{
 const root=disk(t),files=new FileStore(),job={id:'job',sessionId:'one',createdAt:Date.now()-1000,claimed:true};
 const filename=join(root,'report.csv');writeFileSync(filename,'item,quantity\nAmber,3\n');
 const input={downloadId:7,filename,size:22,startTime:new Date().toISOString(),referrer:pair.url};input.size=Buffer.byteLength('item,quantity\nAmber,3\n');
 const result=importBrowserDownload(files,job,input,{directory:root,pair});
 assert.equal(result.direction,'from-website');assert.equal(files.bytes(files.get(result.id,'one')).toString(),'item,quantity\nAmber,3\n');
 assert.equal(importBrowserDownload(files,job,input,{directory:root,pair}).id,result.id);
 assert.throws(()=>importBrowserDownload(files,{...job,terminal:true},input,{directory:root,pair}),/active/);
});
test('download import rejects foreign origins, old files, outside-root paths, executables and incorrect sizes',t=>{
 const root=disk(t),downloads=join(root,'Downloads');mkdirSync(downloads);const files=new FileStore();
 const filename=join(downloads,'report.csv');writeFileSync(filename,'abc');const outside=join(root,'secret.txt');writeFileSync(outside,'secret');
 const exe=join(downloads,'unsafe.exe');writeFileSync(exe,'abc');const job={sessionId:'one',createdAt:Date.now()-100,claimed:true};
 const input={downloadId:1,filename,size:3,startTime:new Date().toISOString(),referrer:pair.url};
 for(const change of [{referrer:'https://other.example/c/test'},{startTime:new Date(Date.now()-60000).toISOString()},{filename:outside,size:6},{filename:exe},{size:2}]){
   assert.throws(()=>importBrowserDownload(files,job,{...input,...change},{directory:downloads,pair}));
 }
 const future={...job,createdAt:Date.now()+2500};
 assert.throws(()=>importBrowserDownload(files,future,{...input,startTime:new Date(future.createdAt).toISOString()},{directory:downloads,pair}),/creation time/);
 assert.equal(files.list('one').length,0);
});
function browser(){
 const created=new Set(),changed=new Set(),imports=[],searches=[];const items=new Map();let permitted=true,active=true;
 const chrome={permissions:{contains:async()=>permitted},downloads:{onCreated:{addListener:fn=>created.add(fn),removeListener:fn=>created.delete(fn)},
 onChanged:{addListener:fn=>changed.add(fn),removeListener:fn=>changed.delete(fn)},async search(query){searches.push(query);return [items.get(query.id)];}}};
 const watcher=new BrowserDownloadWatch(chrome,{id:()=> 'watch',timeoutMs:1000,isActive:()=>active,importFile:async(job,input)=>{imports.push(input);return {id:'file',name:'report.csv'};}});
 return {watcher,created,changed,imports,searches,items,setPermission:value=>permitted=value,setActive:value=>active=value,
 emit(item){items.set(item.id,item);for(const fn of created)fn(item);},done(id){for(const fn of changed)fn({id,state:{current:'complete'}});}};
}
test('download permission is optional and only the matching newly created download ID is inspected',async()=>{
 const b=browser();b.setPermission(false);assert.equal((await b.watcher.arm({id:'job'},{url:pair.url},'report.csv')).available,false);assert.equal(b.created.size,0);
 b.setPermission(true);const ticket=await b.watcher.arm({id:'job'},{url:pair.url},'report.csv');
 const waiting=b.watcher.wait(ticket.watchId,'job');const base={startTime:new Date().toISOString(),filename:'C:/Downloads/report(1).csv',fileSize:3,state:'complete',url:'blob:https://chatgpt.com/file'};
 b.emit({...base,id:6,referrer:'https://other.example/'});b.emit({...base,id:7,referrer:pair.url});
 assert.equal((await waiting).id,'file');assert.deepEqual(b.searches,[{id:7}]);assert.equal(b.imports.length,1);assert.equal(b.created.size,0);assert.equal(b.changed.size,0);
});
test('download watches are job-scoped, ignore old downloads, and cancel without reading any file',async()=>{
 const b=browser(),ticket=await b.watcher.arm({id:'job'},{url:pair.url},'report.csv');
 await assert.rejects(b.watcher.wait(ticket.watchId,'other'),/Unowned/);
 const waiting=assert.rejects(b.watcher.wait(ticket.watchId,'job'),/cancelled/);
 b.emit({id:4,referrer:pair.url,startTime:new Date(Date.now()-60000).toISOString(),state:'complete'});
 b.watcher.cancel('job');await waiting;assert.equal(b.imports.length,0);assert.equal(b.searches.length,0);assert.equal(b.created.size,0);
});

test('parallel same-origin downloads take turns before clicking; different origins remain independent',async()=>{
 const b=browser();let sequence=0;b.watcher.id=()=>`watch-${++sequence}`;
 const first=await b.watcher.arm({id:'a'},{url:'https://chatgpt.com/c/a'},'report.csv');
 assert.deepEqual(await b.watcher.arm({id:'b'},{url:'https://chatgpt.com/c/b'},'report.csv'),{available:false,busy:true});
 const other=await b.watcher.arm({id:'g'},{url:'https://gemini.google.com/app/g'},'report.csv');assert.equal(other.available,true);
 const a=b.watcher.wait(first.watchId,'a');
 b.emit({id:101,referrer:'https://chatgpt.com/c/a',startTime:new Date().toISOString(),filename:'C:/Downloads/report.csv',fileSize:3,state:'complete'});
 await a;assert.equal(b.imports.length,1);
 const second=await b.watcher.arm({id:'b'},{url:'https://chatgpt.com/c/b'},'report.csv');assert.equal(second.available,true);
 const result=b.watcher.wait(second.watchId,'b');
 b.emit({id:102,referrer:'https://chatgpt.com/c/b',startTime:new Date().toISOString(),filename:'C:/Downloads/report(1).csv',fileSize:3,state:'complete'});
 await result;assert.deepEqual(b.imports.map(i=>i.downloadId),[101,102]);
 const cancelled=assert.rejects(b.watcher.wait(other.watchId,'g'),/cancelled/);b.watcher.cancel('g');await cancelled;
 assert.equal(b.watcher.origins.size,0);
});
test('the HTTP download import requires authentication, an active claimed job and exact session ownership',async t=>{
 const root=disk(t),token='browser-download-test-token-01234567890123456789';
 const bridge=await new BrowserBridge({token,port:0,downloadDirectory:root}).start();t.after(()=>bridge.close());
 const post=async(path,input,auth=true)=>fetch(`http://127.0.0.1:${bridge.port}${path}`,{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(input)});
 const pending=(async()=>{const events=[];for await(const event of bridge.request('chatgpt-web','synthetic download',undefined,{sessionId:'one'}))events.push(event);return events;})();
 const {commands:[job]}=await (await post('/poll',{sites:['chatgpt-web']})).json();
 await post('/event',{id:job.id,type:'binding',url:pair.url,tabId:7});
 const filename=join(root,'new.csv');writeFileSync(filename,'a,b\n1,2\n');
 const input={jobId:job.id,downloadId:9,filename,size:8,startTime:new Date().toISOString(),referrer:pair.url};
 assert.equal((await post('/download-file',input,false)).status,401);
 assert.equal((await post('/download-file',{...input,jobId:'other'})).status,400);
 const response=await post('/download-file',input);assert.equal(response.status,200);const file=await response.json();
 assert.equal(file.direction,'from-website');assert.equal(bridge.files.list('other').length,0);
 await post('/event',{id:job.id,type:'file',fileId:file.id});await post('/event',{id:job.id,type:'done',text:'Done'});
 assert.equal((await pending)[0].file.id,file.id);
 assert.equal((await post('/download-file',input)).status,400);
});
