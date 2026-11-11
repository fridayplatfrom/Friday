import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {BrowserBridge} from '../bridge.mjs';
import {DesktopState} from '../desktop/state.mjs';
import {submitOnce} from '../desktop/submission.mjs';
import {providerURL,siteForURL} from '../desktop/policy.mjs';
import {chatURL,navigationAllowed,localHarness,pageMessageTypes} from '../desktop/policy.mjs';
const token='desktop-test-token-012345678901234567890';
const owner='aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa',other='bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb';
test('desktop owns dispatch exclusively; extension parks; only owner can release',async t=>{
 const b=await new BrowserBridge({token,port:0}).start();t.after(()=>b.close());
 const post=async(path,body)=>{const r=await fetch(`http://127.0.0.1:${b.port}${path}`,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(body)});return {status:r.status,body:await r.json()};};
 assert.equal((await post('/desktop/claim',{clientId:owner})).status,200);
 const parked=await post('/poll',{sites:['chatgpt-web'],version:'0.10.3'});
 assert.equal(parked.body.parked,true);assert.deepEqual(parked.body.commands,[]);assert.equal(b.lastSeen,0);
 assert.equal((await post('/desktop/claim',{clientId:other})).status,409);
 assert.equal((await post('/poll',{transport:'desktop',clientId:other,sites:['chatgpt-web']})).status,409);
 assert.equal((await post('/poll',{transport:'desktop',clientId:owner,sites:['chatgpt-web'],version:'0.10.3'})).status,200);
 assert.equal(b.enabledSites[0],'chatgpt-web');
 b.jobs.set('uncertain',{terminal:false});
 assert.equal((await post('/desktop/claim',{clientId:owner})).status,200);
 assert.equal((await post('/desktop/release',{clientId:owner})).status,409);
 b.jobs.clear();
 assert.equal((await post('/desktop/release',{clientId:other})).status,409);
 assert.equal((await post('/desktop/release',{clientId:owner})).status,200);
 assert.equal((await post('/poll',{sites:['chatgpt-web']})).status,200);
});
test('cannot take desktop ownership from active extension work or builtin controller',async t=>{
 const b=await new BrowserBridge({token,port:0}).start();t.after(()=>b.close());b.jobs.set('active',{terminal:false});
 const r=await fetch(`http://127.0.0.1:${b.port}/desktop/claim`,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({clientId:owner})});assert.equal(r.status,409);assert.equal(b.desktopOwner,undefined);b.jobs.clear();
});
test('desktop submission receipts survive restart and are scoped to tab and origin',()=>{
 const dir=fs.mkdtempSync(join(tmpdir(),'friday-desktop-'));try{
 const path=join(dir,'state.json'),first=new DesktopState(path);
 first.receipt(1,'https://chatgpt.com','harness-job:one',JSON.stringify({state:'submitting'}));
 const second=new DesktopState(path);assert.equal(JSON.parse(second.receipts(1,'https://chatgpt.com')['harness-job:one']).state,'submitting');
 assert.deepEqual(second.receipts(2,'https://chatgpt.com'),{});assert.deepEqual(second.receipts(1,'https://accounts.google.com'),{});
 assert.throws(()=>second.receipt(1,'https://chatgpt.com','arbitrary','x'));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('remote IPC and navigation policies do not expose arbitrary local or external access',()=>{
 for(const url of ['file:///C:/Windows/win.ini','http://chatgpt.com/','https://chatgpt.com.evil.test/','https://user@chatgpt.com/','javascript:alert(1)']){assert.equal(chatURL(url),null);assert.equal(navigationAllowed(url),false);}
 assert.ok(chatURL('https://chatgpt.com/c/test'));assert.ok(navigationAllowed('https://accounts.google.com/'));
 assert.ok(localHarness('http://127.0.0.1:3030/'));assert.equal(localHarness('http://127.0.0.1:3031/'),false);
 assert.equal(pageMessageTypes.has('shell-exec'),false);assert.equal(pageMessageTypes.has('harness-event'),true);
});
test('native submission admits one click and refuses replay after success, crash or uncertain input failure',()=>{
 const dir=fs.mkdtempSync(join(tmpdir(),'friday-submit-'));try{
 const path=join(dir,'state.json'),state=new DesktopState(path),args={tabId:1,origin:'https://chatgpt.com',jobId:'test',x:10,y:10,width:100,height:100};let clicks=0;
 assert.throws(()=>submitOnce(state,args,()=>clicks++),/receipt/);
 state.receipt(1,args.origin,'harness-job:test',JSON.stringify({state:'submitting'}));
 submitOnce(state,args,()=>clicks++);assert.equal(clicks,1);
 assert.throws(()=>submitOnce(new DesktopState(path),args,()=>clicks++),/already attempted/);assert.equal(clicks,1);
 state.receipt(1,args.origin,'harness-job:uncertain',JSON.stringify({state:'submitting'}));
 assert.throws(()=>submitOnce(state,{...args,jobId:'uncertain'},()=>{throw Error('renderer lost');}),/renderer lost/);
 assert.throws(()=>submitOnce(new DesktopState(path),{...args,jobId:'uncertain'},()=>clicks++),/already attempted/);assert.equal(clicks,1);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('provider tabs retain exact origins and do not adopt lookalikes or credential URLs',()=>{
 for(const [url,site]of [['https://chatgpt.com/c/one','chatgpt-web'],['https://gemini.google.com/app/test','gemini-web'],['https://chat.deepseek.com/a/chat/s/test','deepseek-web'],['https://www.kimi.ai/chat/test','kimi-web']]){assert.equal(siteForURL(url),site);assert.equal(providerURL(url+'?token=private',site),url);assert.equal(providerURL(url,'other-provider'),null);}
 assert.equal(siteForURL('https://gemini.google.com.evil.test/'),undefined);assert.equal(providerURL('https://password@chatgpt.com/'),null);
});
