import test from 'node:test';
import assert from 'node:assert/strict';
import { ExpertBridgeClient } from '../plugin/transport.mjs';
import { registerExpertTools } from '../plugin/tools.mjs';
import { assertAllowedUrl, runBrowserWorkflow } from '../plugin/browser.mjs';

const token = 'x'.repeat(40);
const client = {request: async (path, payload) => {
  if (path === '/v1/plan') return {status:'planned',actions:[{type:'navigate'}]};
  if (path === '/v1/form/map') return {status:'mapped',matches:[{index:0,key:'email'}],unmatched:[]};
  if (path === '/v1/form/verify') return {status:'verified',verified:payload.expected.email === payload.actual.email};
  return {status:'ok'};
}};

test('transport enforces loopback and auth token', async () => {
  assert.throws(() => new ExpertBridgeClient({baseUrl:'https://evil.example',token}),/127.0.0.1/);
  assert.throws(() => new ExpertBridgeClient({token:'bad'}),/32/);
  const transport = new ExpertBridgeClient({token,fetchImpl:async(url,args)=>({ok:true,text:async()=>'{"status":"ok"}'})});
  assert.deepEqual(await transport.request('/health'),{status:'ok'});
  await assert.rejects(() => transport.request('/v1/run/shell',{}),/Unknown/);
});

test('registered tools expose actual handler functions', async () => {
  const registered=[];
  registerExpertTools({tools:{register(x){registered.push(x)}}}, x=>x,client);
  assert.equal(registered.length,9);
  const tool = registered.find(x=>x.name==='expertos_route');
  assert.ok(tool);
  assert.equal(JSON.parse(await tool.execute({task:'fill form'})).status,'ok');
});

test('browser URL security', () => {
  assert.equal(assertAllowedUrl('https://example.com/form',['example.com']).hostname,'example.com');
  for (const url of ['http://example.com','file:///etc/passwd','https://localhost','https://127.0.0.1','https://example.com:444']) {
    assert.throws(()=>assertAllowedUrl(url,['example.com']),/Only HTTPS|Blocked|Invalid|forbidden/);
  }
});

function fakePlaywright(state) {
  class Input {
    async fill(value){state.value=value;}
    async selectOption({value}){state.value=value;}
    async inputValue(){return state.value;}
  }
  class Locator {
    constructor(key){this.key=key;}
    async evaluateAll(){return [{index:0,label:'Email',id:'email',name:'email',type:'email',tag:'input',disabled:false,visible:true}];}
    nth(i){assert.equal(i,0);return new Input();}
    async innerText(){return 'Example page visible text';}
  }
  const page={url(){return 'http://127.0.0.1:8000/form';},
    async goto(url){state.goto=url;},locator(s){return new Locator(s);}};
  const context={async route(glob,handler){state.route=true;},async newPage(){return page;}};
  return {chromium:{async launch(){return {async newContext(){return context;},async close(){state.closed=true;}};}}};
}

test('form fill verifies saved value and never submits', async () => {
  const state={value:'',closed:false};
  const result=await runBrowserWorkflow({url:'http://127.0.0.1:8000/form',kind:'fill_form',values:{email:'me@example.com'},
    client,allowTestLoopback:true,playwrightLoader:async()=>fakePlaywright(state)});
  assert.equal(result.status,'verified');
  assert.equal(result.form_submitted,false);
  assert.deepEqual(result.filled_keys,['email']);
  assert.equal(state.value,'me@example.com');
  assert.equal(state.closed,true);
});

test('extract keeps page text untrusted and cleanup', async () => {
  const state={closed:false};
  const result=await runBrowserWorkflow({url:'http://127.0.0.1:8000/form',kind:'extract',client,
    allowTestLoopback:true,playwrightLoader:async()=>fakePlaywright(state)});
  assert.equal(result.status,'extracted');
  assert.equal(result.verified,false);
  assert.equal(state.closed,true);
});
