import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {DesktopState} from '../desktop/state.mjs';
import {FirstRunSetup} from '../desktop/onboarding.mjs';
import {startSetupTest} from '../setup-test.mjs';
import {BrowserBridge} from '../bridge.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(t,existing=false){
 const directory=mkdtempSync(join(tmpdir(),'friday-setup-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));
 const state=new DesktopState(join(directory,'state.json')),calls=[];
 state.data.tabs=[{id:1,url:'https://chatgpt.com/c/saved'}];state.data.receipts={saved:{value:'preserve'}};
 const options={state,existing,open:async site=>calls.push(['open',site]),test:async()=>({ok:true,message:'Message sent and reply received.'}),complete:async(site,id)=>calls.push(['complete',site,id])};
 return {state,calls,options,flow:new FirstRunSetup(options),directory};
}
test('fresh installation asks once; existing installation migrates without touching tabs or receipts',async t=>{
 const fresh=fixture(t);assert.equal(fresh.flow.snapshot().visible,true);await fresh.flow.action({action:'skip'});
 assert.equal(new FirstRunSetup(fresh.options).snapshot().visible,false);
 const old=fixture(t,true);assert.equal(old.flow.snapshot().visible,false);assert.equal(old.flow.snapshot().status,'existing');
 assert.equal(old.state.data.tabs[0].url,'https://chatgpt.com/c/saved');assert.equal(old.state.data.receipts.saved.value,'preserve');assert.deepEqual(old.calls,[]);
});
test('only a passed reply test can finish and select the default; other providers are optional',async t=>{
 const f=fixture(t);await assert.rejects(f.flow.action({action:'finish'}),/Verify/);
 await assert.rejects(f.flow.action({action:'select',site:'unknown'}),/Unknown/);
 await f.flow.action({action:'select',site:'gemini-web'});await f.flow.action({action:'test'});await tick();
 assert.equal(f.flow.snapshot().test.status,'passed');await f.flow.action({action:'finish'});
 assert.equal(f.flow.snapshot().defaultProvider,'gemini-web');assert.equal(f.flow.snapshot().visible,false);
 assert.equal(new FirstRunSetup(f.options).snapshot().visible,false);assert.equal(f.calls.filter(c=>c[0]==='open').length,1);
});
test('selecting the already verified provider does not invalidate or resend its test',async t=>{
 const f=fixture(t);await f.flow.action({action:'select',site:'gemini-web'});await f.flow.action({action:'test'});await tick();
 const id=f.flow.snapshot().test.id;await f.flow.action({action:'select',site:'gemini-web'});
 assert.equal(f.flow.snapshot().test.id,id);assert.equal(f.flow.snapshot().test.status,'passed');assert.equal(f.calls.length,1);
});
test('double-click and competing setup changes cannot send a second test while one is running',async t=>{
 const f=fixture(t);let complete,calls=0;f.flow.test=()=>{calls++;return new Promise(resolve=>complete=resolve);};
 await f.flow.action({action:'select',site:'chatgpt-web'});await f.flow.action({action:'test'});await tick();
 for(const action of ['test','skip','finish','select'])await assert.rejects(f.flow.action({action,site:'kimi-web'}),/Finish/);
 assert.equal(calls,1);assert.equal((await f.flow.action({action:'status'})).test.status,'running');complete({ok:true});await tick();
});
test('refresh and restart preserve selection and mark an in-flight test interrupted without replay',async t=>{
 const f=fixture(t);let sends=0;f.state.data.onboarding.site='deepseek-web';f.state.data.onboarding.test={id:randomUUID(),status:'running'};f.state.save();
 const state=new DesktopState(f.state.path);const resumed=new FirstRunSetup({...f.options,state,test:async()=>{sends++;}});
 assert.equal(resumed.snapshot().site,'deepseek-web');assert.equal(resumed.snapshot().test.status,'interrupted');assert.equal(sends,0);assert.equal(resumed.snapshot().visible,true);
});
test('failed test never becomes ready; failed default save retains the successful verification for retry',async t=>{
 const f=fixture(t);await f.flow.action({action:'select',site:'kimi-web'});f.flow.test=async()=>{throw Error('Sign-in required');};
 await f.flow.action({action:'test'});await tick();assert.equal(f.flow.snapshot().test.status,'failed');await assert.rejects(f.flow.action({action:'finish'}),/Verify/);
 f.flow.test=async()=>({ok:true});await f.flow.action({action:'test'});await tick();f.flow.complete=async()=>{throw Error('Settings unavailable');};
 await assert.rejects(f.flow.action({action:'finish'}),/Settings/);assert.equal(f.flow.snapshot().test.status,'passed');assert.equal(f.flow.snapshot().visible,true);
});
test('setup transport uses a fixed tool-free prompt and persists an idempotent receipt across backend restart',async t=>{
 const f=fixture(t);const bridge=new BrowserBridge({token:'test-only-setup-token-01234567890123456789',stateDirectory:join(f.directory,'bridge')});bridge.desktopOwner='owner';let calls=0;
 bridge.request=async function*(site,prompt,_signal,options){calls++;assert.equal(site,'chatgpt-web');assert.match(prompt,/Do not use tools/);assert.match(options.sessionId,/^friday-setup-/);yield {type:'done',text:'FRIDAY_SETUP_READY'};};
 const input={clientId:'owner',site:'chatgpt-web',id:randomUUID()};const first=startSetupTest(bridge,input);assert.equal(startSetupTest(bridge,input),first);await tick();
 assert.equal(first.status,'passed');assert.equal(calls,1);
 const restarted=new BrowserBridge({token:bridge.token,stateDirectory:join(f.directory,'bridge')});restarted.desktopOwner='owner';restarted.request=()=>{throw Error('Must not replay');};
 assert.equal(startSetupTest(restarted,input).status,'passed');assert.throws(()=>startSetupTest(restarted,{...input,clientId:'other'}),/ownership/);
});
test('setup HTTP routes require desktop ownership and verified matching provider before changing native defaults',async t=>{
 const bridge=await new BrowserBridge({token:'test-only-setup-token-01234567890123456789',port:0}).start();t.after(()=>bridge.close());bridge.desktopOwner='owner';
 const post=(path,body)=>fetch(`http://127.0.0.1:${bridge.port}${path}`,{method:'POST',headers:{Authorization:'Bearer '+bridge.token,'Content-Type':'application/json'},body:JSON.stringify(body)});
 const id=randomUUID();assert.equal((await post('/desktop/setup-test',{id,site:'chatgpt-web',clientId:'other'})).status,400);
 bridge.setupTests=new Map([[id,{status:'passed',site:'chatgpt-web'}]]);let settings;
 bridge.configureSetupDefault=async site=>{settings=site;};
 assert.equal((await post('/desktop/setup-default',{id,site:'gemini-web',clientId:'owner'})).status,400);assert.equal(settings,undefined);
 assert.equal((await post('/desktop/setup-default',{id,site:'chatgpt-web',clientId:'owner'})).status,200);assert.equal(settings,'chatgpt-web');
 const response=await fetch(`http://127.0.0.1:${bridge.port}/desktop/setup-test/${id}`,{headers:{Authorization:'Bearer '+bridge.token,'X-Friday-Client':'other'}});assert.equal(response.status,403);
});
test('Models management retains each provider test and changes defaults without closing the page',async t=>{
 const f=fixture(t,true);await f.flow.action({action:'show'});assert.equal(f.flow.snapshot().mode,'manage');
 await f.flow.action({action:'select',site:'chatgpt-web'});await f.flow.action({action:'test'});await tick();const id=f.flow.snapshot().test.id;
 await f.flow.action({action:'select',site:'gemini-web'});assert.equal(f.flow.snapshot().test,null);
 await f.flow.action({action:'select',site:'chatgpt-web'});assert.equal(f.flow.snapshot().test.id,id);
 await f.flow.action({action:'default'});assert.equal(f.flow.snapshot().visible,true);assert.equal(f.flow.snapshot().defaultProvider,'chatgpt-web');
 await f.flow.action({action:'skip'});assert.equal(f.flow.snapshot().visible,false);assert.equal(new FirstRunSetup(f.options).snapshot().visible,false);
});
test('disabling a provider preserves verification, tabs and receipts; a new successful test re-enables it',async t=>{
 const f=fixture(t,true);let disabled;f.flow.disable=async site=>{disabled=site;};
 await f.flow.action({action:'show'});await f.flow.action({action:'select',site:'chatgpt-web'});await f.flow.action({action:'test'});await tick();
 await f.flow.action({action:'disable'});assert.equal(disabled,'chatgpt-web');assert.equal(f.flow.snapshot().providers['chatgpt-web'].disabled,true);
 assert.equal(f.state.data.tabs[0].id,1);assert.equal(f.state.data.receipts.saved.value,'preserve');await assert.rejects(f.flow.action({action:'default'}),/enable/);
 await f.flow.action({action:'test'});await tick();assert.equal(f.flow.snapshot().providers['chatgpt-web'].disabled,false);
});
