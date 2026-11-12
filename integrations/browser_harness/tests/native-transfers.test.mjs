import test from 'node:test';import assert from 'node:assert/strict';import {EventEmitter} from 'node:events';
import {mkdtempSync,rmSync,mkdirSync,symlinkSync,readFileSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {createHash} from 'node:crypto';
import {taskArtifacts,acceptDownloadBehavior,taskDownload} from '../native-task-downloads.mjs';
import {DemoFormServer} from '../demo-form.mjs';import {fixtureBytes} from '../native-browser-fixture.mjs';
test('native download paths are workspace scoped and redirected artifact directories are rejected',t=>{
 const root=mkdtempSync(join(tmpdir(),'friday-download-test-'));t.after(()=>rmSync(root,{recursive:true,force:true}));const workspace=join(root,'workspace'),outside=join(root,'outside');mkdirSync(workspace);mkdirSync(outside);
 assert.equal(acceptDownloadBehavior({behavior:'allowAndName',downloadPath:taskArtifacts(workspace)},workspace),true);
 assert.equal(acceptDownloadBehavior({behavior:'deny'},workspace),false);
 assert.throws(()=>acceptDownloadBehavior({behavior:'allowAndName',downloadPath:outside},workspace),/workspace/);
 rmSync(join(workspace,'.friday-browser-artifacts'),{recursive:true});symlinkSync(outside,join(workspace,'.friday-browser-artifacts'),process.platform==='win32'?'junction':'dir');assert.throws(()=>taskArtifacts(workspace),/redirect/);
});
test('native download events preserve bytes, filename and completion order without accepting browser-wide paths',async t=>{
 const root=mkdtempSync(join(tmpdir(),'friday-download-event-'));t.after(()=>rmSync(root,{recursive:true,force:true}));const item=new EventEmitter(),events=[];
 Object.assign(item,{getFilename:()=> '../test.txt',getURL:()=> 'http://127.0.0.1/download',setSavePath:path=>item.path=path,getTotalBytes:()=>59,getReceivedBytes:()=>59,cancel(){this.cancelled=true;}});
 const record=taskDownload(item,{directory:root,guest:{debugger:{sendCommand:async()=>({frameTree:{frame:{id:'fixture-frame'}}})}},send:event=>events.push(event)});
 item.emit('done',{},'completed');await new Promise(setImmediate);
 assert.equal(record.suggestedFilename,'.._test.txt');assert.equal(item.path,join(taskArtifacts(root),record.guid));assert.deepEqual(events.map(e=>e.method),['Browser.downloadWillBegin','Browser.downloadProgress']);assert.equal(events[1].params.state,'completed');assert.equal(events[1].params.guid,record.guid);assert.equal(events[0].params.frameId,'fixture-frame');
});
test('fictional fixture persists login evidence and raw action counts across a server restart',async t=>{
 const root=mkdtempSync(join(tmpdir(),'friday-browser-fixture-'));let server=await new DemoFormServer({port:0,testRoot:root}).start();t.after(async()=>{await server.close();rmSync(root,{recursive:true,force:true});});
 let base=`http://127.0.0.1:${server.port}/_browser-test/unit-run`;
 const signin=await fetch(base+'/sign-in',{method:'POST',redirect:'manual'}),cookie=signin.headers.get('set-cookie').split(';')[0];assert.match(signin.headers.get('set-cookie'),/Max-Age=604800/);
 const headers={Cookie:cookie};const fields=new URLSearchParams({name:'Friday Test User',email:'friday@example.invalid',confirm:'yes',topic:'Uploads and downloads'});
 for(let i=0;i<2;i++)assert.equal((await fetch(base+'/submit',{method:'POST',headers,body:fields,redirect:'manual'})).status,303);
 const data=new FormData();data.append('file',new Blob([fixtureBytes]),'upload.txt');assert.equal((await fetch(base+'/upload',{method:'POST',headers,body:data,redirect:'manual'})).status,303);
 assert.deepEqual(Buffer.from(await (await fetch(base+'/download')).arrayBuffer()),fixtureBytes);
 await server.close();server=await new DemoFormServer({port:0,testRoot:root}).start();base=`http://127.0.0.1:${server.port}/_browser-test/unit-run`;
 const state=await (await fetch(base+'/state',{headers})).json();assert.equal(state.signedIn,true);assert.equal(state.signIns,1);assert.equal(state.formSubmissions,2);assert.equal(state.downloads,1);assert.equal(state.uploads.length,1);assert.equal(state.uploads[0].sha256,createHash('sha256').update(fixtureBytes).digest('hex'));assert.equal(JSON.parse(readFileSync(join(root,'unit-run.json'))).formSubmissions,2);
 assert.match(await(await fetch(base)).text(),/Open second tab/);
});
