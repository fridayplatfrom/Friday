import test from 'node:test';
import assert from 'node:assert/strict';
import {PROVIDERS,SITES,publicProvider,providerProbe} from '../providers.mjs';
import {recoveryDiagnostic} from '../diagnostics.mjs';
import {BrowserBridge} from '../bridge.mjs';
import {websiteURL} from '../session-store.mjs';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';

test('authenticated update status reads newly installed versions without restarting or trusting cached Chrome resources',async t=>{
 const directory=mkdtempSync(join(tmpdir(),'friday-update-'));t.after(()=>{assert.equal(dirname(directory),tmpdir());rmSync(directory,{recursive:true,force:true});});
 const path=join(directory,'manifest.json'),token='synthetic-update-token-long-enough-0123456789';writeFileSync(path,JSON.stringify({version:'0.9.2'}));
 const bridge=await new BrowserBridge({token,port:0,extensionManifestPath:path}).start();t.after(()=>bridge.close());
 const url=`http://127.0.0.1:${bridge.port}/status`;assert.equal((await fetch(url)).status,401);
 const read=async()=>(await fetch(url,{headers:{Authorization:'Bearer '+token}})).json();assert.equal((await read()).availableExtensionVersion,'0.9.2');
 writeFileSync(path,JSON.stringify({version:'0.9.3'}));assert.equal((await read()).availableExtensionVersion,'0.9.3');
 writeFileSync(path,'invalid');assert.equal((await read()).availableExtensionVersion,null);
});

test('Kimi URL aliases preserve existing conversations while rejecting credentials, foreign hosts and ports',()=>{
 for(const host of ['www.kimi.ai','www.kimi.com','kimi.com'])assert.equal(websiteURL('kimi-web',`https://${host}/chat/saved?secret=discard`),`https://${host}/chat/saved`);
 for(const url of ['http://www.kimi.ai/chat/saved','https://www.kimi.ai.evil.test/chat/saved','https://www.kimi.ai:444/chat/saved','https://user:password@www.kimi.ai/chat/saved'])assert.equal(websiteURL('kimi-web',url),null);
});

test('shared provider contract exposes DeepSeek backup with honest capability limits',()=>{
 assert.equal(SITES['deepseek-web'].url,'https://chat.deepseek.com/');
 const p=publicProvider('deepseek-web');assert.equal(p.backup,true);assert.equal(p.experimental,true);assert.equal(p.capabilities.fileTransfer,false);assert.equal(p.capabilities.twoWay,false);assert.equal(p.health.state,'unchecked');
 for(const p of Object.values(PROVIDERS)){assert.equal(new URL(p.url).hostname,p.selectors.hosts[0]);assert.ok(p.selectors.composer.length&&p.selectors.send.length&&p.selectors.responses.length&&p.selectors.complete.length);assert.equal(Object.isFrozen(p.selectors.composer),true);}
});
test('DeepSeek introduction follows initial conversation creation but resets on an explicitly different chat',()=>{
 const bridge=new BrowserBridge({token:'test-provider-token-long-enough-0123456789'}),s=bridge.sessions;
 s.bind({sessionId:'deep',site:'deepseek-web',tabId:7,url:'https://chat.deepseek.com/'});s.acknowledgeIntroduction('deep','deepseek-web',2);
 s.bind({sessionId:'deep',site:'deepseek-web',tabId:7,url:'https://chat.deepseek.com/a/chat/s/one'});assert.equal(s.introductionReady('deep','deepseek-web',2),true);
 s.bind({sessionId:'deep',site:'deepseek-web',tabId:9,url:'https://chat.deepseek.com/a/chat/s/two'});assert.equal(s.introductionReady('deep','deepseek-web',2),false);
});
test('provider health reports only bounded facts and never confuses an idle editor with successful execution',()=>{
 const health=providerProbe({site:'deepseek-web',page:{provider:'deepseek-web',hasEditor:true,isGenerating:false,url:'SECRET_URL',text:'PRIVATE_PROMPT'}});
 assert.equal(health.state,'ready');assert.equal(/SECRET|PRIVATE/.test(JSON.stringify(health)),false);
 assert.equal(providerProbe({site:'deepseek-web',page:{provider:'chatgpt-web',hasEditor:true}}).state,'unavailable');
 assert.equal(providerProbe({site:'deepseek-web',notOpen:true}).state,'not-open');
 assert.equal(providerProbe({site:'deepseek-web',page:{provider:'deepseek-web',hasEditor:true,isGenerating:true}}).state,'busy');
 assert.throws(()=>providerProbe({site:'unknown'}),/Unknown/);
 assert.throws(()=>providerProbe({site:'__proto__'}),/Unknown/);assert.throws(()=>publicProvider('constructor'),/Unknown/);
});

test('a missing saved tab ID does not claim that its provider website is closed',()=>{
 for(const site of Object.keys(PROVIDERS)){
  const result=providerProbe({site,notOpen:true,probeStatus:'missing-tab'});
  assert.equal(result.state,'needs-reconnect');assert.equal(result.listenerResponded,false);assert.equal(result.hasEditor,false);
  assert.match(result.scope,/may still be open under another ID/);
 }
});
test('recovery diagnostics preserve submission uncertainty and never enable automated retry or provider switching',()=>{
 const notSent=recoveryDiagnostic('Website is already generating. Nothing was sent.',{id:'r',site:'chatgpt-web',claimed:true});assert.equal(notSent.submission,'not-submitted');assert.equal(notSent.category,'website-busy');
 const sent=recoveryDiagnostic('No prompt was sent.',{submitted:true});assert.equal(sent.submission,'submitted');assert.equal(sent.canRetryWithoutDuplicateSubmission,false);
 const unknown=recoveryDiagnostic('Send control disappeared SECRET_PROMPT',{claimed:true});assert.equal(unknown.submission,'unknown');assert.equal(unknown.category,'website-layout');assert.equal(JSON.stringify(unknown).includes('SECRET_PROMPT'),false);assert.equal(unknown.automaticResubmit,false);assert.equal(unknown.automaticProviderSwitch,false);
 assert.equal(recoveryDiagnostic('Browser extension not connected; log in in Chrome.',{claimed:false}).category,'connection');
});
test('provider probes use existing authenticated extension transport; recovery survives in the native session without replay',async t=>{
 const token='test-provider-token-long-enough-0123456789';
 const bridge=await new BrowserBridge({token,port:0,timeoutMs:30,connectionGraceMs:1}).start();t.after(()=>bridge.close());
 const url=`http://127.0.0.1:${bridge.port}/provider-health`,body=JSON.stringify({site:'deepseek-web',page:{provider:'deepseek-web',hasEditor:true}});
 assert.equal((await fetch(url,{method:'POST',body})).status,401);
 assert.equal((await fetch(url,{method:'POST',body,headers:{Authorization:'Bearer '+token,Origin:'https://unrelated.test'}})).status,403);
 assert.equal((await fetch(url,{method:'POST',body,headers:{Authorization:'Bearer '+token}})).status,200);
 assert.equal(bridge.uiStatus().providers.find(p=>p.id==='deepseek-web').health.state,'ready');
 await bridge.uiAction('health',{site:'deepseek-web'});assert.equal(bridge.actions[0].type,'probe-site');assert.equal(bridge.jobs.size,0);
 await assert.rejects(async()=>{for await(const _ of bridge.request('chatgpt-web','SECRET_PROMPT',undefined,{sessionId:'test'})){}},/not connected|timed out/);
 const diagnostic=bridge.sessions.get('test').recovery.at(-1);assert.equal(diagnostic.submission,'not-submitted');assert.equal(JSON.stringify(diagnostic).includes('SECRET_PROMPT'),false);assert.equal(bridge.jobs.size,0);
});
