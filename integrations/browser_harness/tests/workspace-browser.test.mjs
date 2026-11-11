import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,rmSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {EventEmitter} from 'node:events';
import {WorkspaceBrowserState,workspaceIdentity,argumentDigest,restorableTab} from '../workspace-browser-state.mjs';
import {WorkspaceBrowserManager} from '../workspace-browser-manager.mjs';
import {installWorkspaceBrowser} from '../workspace-browser-control.mjs';
import {upstreamConnection} from '../workspace-browser-upstream.mjs';
import {workspaceBrowserProfile} from '../workspace-browser-config.mjs';
function fixture(t){const root=mkdtempSync(join(tmpdir(),'friday-workspace-'));t.after(()=>rmSync(root,{recursive:true,force:true}));const a=join(root,'a'),b=join(root,'b');mkdirSync(a);mkdirSync(b);return {root,a,b};}
const call=(directory,id='native-1',tool='browser_click',args={ref:'x'})=>({directory,id,sessionId:'native-session',tool,digest:argumentDigest(args)});
test('encoded sign-out and callback routes are never automatically restored',()=>{
 const origins=['https://example.com'];
 for(const route of ['/%6cogout','/%256cogout','/%5clogout','/logout.php','/signout;session=abc','/oauth2/callback','/logout%00'])assert.equal(restorableTab('https://example.com'+route,origins),null,route);
 assert.equal(restorableTab('https://example.com/feed',origins),'https://example.com/feed');
});
test('valid JSON containing malformed or duplicate receipts fails closed without replacing the saved file',t=>{
 const {root,a}=fixture(t),identity=workspaceIdentity(a),state=new WorkspaceBrowserState(root,identity);state.begin(call(a));state.settle('native-1',true);state.acknowledge('native-1','native-session');
 const valid=structuredClone(state.state);
 for(const mutate of [s=>{s.actions[0].status='unknown';},s=>s.actions.push({...s.actions[0]}),s=>{s.revision=-1;},s=>{s.actions[0].digest='broken';}]){
  const damaged=structuredClone(valid);mutate(damaged);const bytes=JSON.stringify(damaged);writeFileSync(state.file,bytes);
  assert.throws(()=>new WorkspaceBrowserState(root,identity),/invalid/);assert.equal(readFileSync(state.file,'utf8'),bytes);
 }
});
test('workspace identity isolates profiles and persists only safe tab locations',t=>{
 const {root,a,b}=fixture(t),one=new WorkspaceBrowserState(root,workspaceIdentity(a)),two=new WorkspaceBrowserState(root,workspaceIdentity(b));assert.notEqual(one.profile,two.profile);
 const origins=['https://example.com'];assert.equal(restorableTab('https://example.com/feed?token=PRIVATE#draft',origins),'https://example.com/feed');
 for(const url of ['https://example.com/logout','https://example.com/oauth/callback','https://evil.test/feed','javascript:alert(1)'])assert.equal(restorableTab(url,origins),null);
 one.tabs(['https://example.com/feed'],0);assert.deepEqual(new WorkspaceBrowserState(root,workspaceIdentity(a)).state.tabs,['https://example.com/feed']);
});
test('crash after website commits blocks replay and other writes until explicit outcome review',t=>{
 const {root,a}=fixture(t);let state=new WorkspaceBrowserState(root,workspaceIdentity(a)),posts=0;
 state.begin(call(a));posts++; // The site committed, then the transport died before acknowledging.
 state=new WorkspaceBrowserState(root,workspaceIdentity(a));assert.equal(state.pending()[0].status,'uncertain');
 assert.throws(()=>state.begin(call(a)),/receipt/);assert.throws(()=>state.begin(call(a,'native-2')),/interrupted/);assert.equal(posts,1);
 assert.throws(()=>state.review('native-1','confirmed-applied',state.state.revision-1),/changed/);
 state.review('native-1','confirmed-applied',state.state.revision);assert.equal(posts,1);assert.throws(()=>state.begin(call(a)),/receipt/);
 assert.ok(!readFileSync(state.file,'utf8').includes('password'));assert.ok(!readFileSync(state.file,'utf8').includes('"ref"'));
});
test('a duplicate dispatch cannot corrupt a successful receipt; read-only inspection remains available',async t=>{
 const {root,a}=fixture(t);let writes=0;const manager=new WorkspaceBrowserManager({root,origins:['https://example.com'],launch:()=>{throw Error('unused');},upstream:async()=>({callTool:async()=>{writes++;return {content:[]};},close:async()=>{}})});
 manager.select(call(a));await manager.call('browser_click',{ref:'x'});manager.release('native-1');
 manager.select(call(a));await assert.rejects(manager.call('browser_click',{ref:'x'}),/receipt/);manager.release('native-1');assert.equal(writes,1);assert.equal(manager.workspace(a).state.state.actions[0].status,'completed');
 manager.workspace(a).state.acknowledge('native-1','native-session');manager.workspace(a).state.begin(call(a,'crashed'));manager.workspace(a).state.settle('crashed',false);
 manager.select(call(a,'read','browser_snapshot',{}));await manager.call('browser_snapshot',{});manager.release('read');assert.equal(writes,2);
 manager.select(call(a,'blocked'));await assert.rejects(manager.call('browser_click',{ref:'x'}),/interrupted/);assert.equal(writes,2);manager.release('blocked');await manager.close();
});
test('native hook uses original workspace and original permission-controlled implementation',async()=>{
 let hook;const calls=[];installWorkspaceBrowser({on:(name,fn)=>{assert.equal(name,'tools/execute');hook=fn;}},async(action,input)=>calls.push({action,input}));
 const exec={name:'mcp__browser__browser_click',arguments:{ref:'x'},callId:'native-1',agent:{session:{id:'session',header:{cwd:'C:/workspace'}}}};
 assert.equal(await hook(exec,async()=>{calls.push({action:'native-tool'});return 'result';}),'result');
 assert.deepEqual(calls.map(c=>c.action),['select','native-tool','release']);assert.equal(calls[0].input.directory,'C:/workspace');assert.equal(calls[0].input.tool,'browser_click');
 assert.equal(await hook({name:'pwsh'},async()=>42),42);await assert.rejects(hook({...exec,agent:null},async()=>{}),/identity/);
});
test('public upstream discovery retains native schemas without launching a browser',async()=>{
 const client=await upstreamConnection(()=>{throw Error('Discovery launched a browser');},{browser:{isolated:false}});
 try{const {tools}=await client.listTools();assert.equal(tools.length,24);assert.ok(tools.some(t=>t.name==='browser_take_screenshot'));assert.ok(tools.find(t=>t.name==='browser_click').inputSchema.properties.target);}finally{await client.close();}
});
test('migration retains extension transport, origin policy, model choice and permissions',()=>{
 const source=`- insert:\n    - id: harness-browser-provider\n      config:\n        browserMode: extension\n    - id: harness-playwright\n      config:\n        args: ["C:/node_modules/@playwright/mcp/cli.js", "--isolated", "--executable-path", "C:/chrome.exe", "--allowed-origins", "https://example.com", "--image-responses", "allow"]\n- id: model\n  model: gemini-web\n  permissions: native\n`;
 const result=workspaceBrowserProfile(source,'C:/workspace-browser-mcp.mjs');assert.match(result,/workspaceBrowser: true/);assert.match(result,/browserMode: extension/);assert.match(result,/gemini-web/);assert.match(result,/permissions: native/);assert.match(result,/https:\/\/example.com/);assert.ok(!result.includes('--isolated'));assert.equal(workspaceBrowserProfile(result,'C:/workspace-browser-mcp.mjs'),result);
});
test('successful browser action without committed native result needs review after restart',t=>{
 const {root,a}=fixture(t);let state=new WorkspaceBrowserState(root,workspaceIdentity(a));state.begin(call(a));state.settle('native-1',true);
 state=new WorkspaceBrowserState(root,workspaceIdentity(a));assert.equal(state.pending().length,1);
 state.review('native-1','confirmed-applied',state.state.revision);state.begin(call(a,'native-2'));state.settle('native-2',true);state.acknowledge('native-2','wrong-session');
 assert.equal(state.state.actions.at(-1).delivered,undefined);state.acknowledge('native-2','native-session');
 state=new WorkspaceBrowserState(root,workspaceIdentity(a));assert.equal(state.pending().length,0);assert.equal(state.state.actions.at(-1).delivered,true);
});
test('receipt save failure prevents dispatch rather than posting without a record',async t=>{
 const {root,a}=fixture(t);let dispatched=0;const manager=new WorkspaceBrowserManager({root,origins:[],upstream:async()=>{dispatched++;},launch:()=>{}});
 const state=manager.workspace(a).state;state.save=()=>{throw Error('disk full');};manager.select(call(a));await assert.rejects(manager.call('browser_click',{ref:'x'}),/disk full/);assert.equal(dispatched,0);manager.release('native-1');
});
test('native queue preserves workspace across concurrent sessions and releases on a tool failure',async()=>{
 let hook;const events=[];let finish;const wait=new Promise(r=>{finish=r;});
 installWorkspaceBrowser({on:(_name,fn)=>{hook=fn;}},async(action,input)=>events.push(action+':'+input.id));
 const exec=id=>({name:'mcp__browser__browser_snapshot',arguments:{},callId:id,agent:{session:{id,header:{cwd:id}}}});
 const first=hook(exec('a'),async()=>{events.push('tool:a');await wait;throw Error('native error');});const failed=assert.rejects(first,/native error/);
 const second=hook(exec('b'),async()=>events.push('tool:b'));await new Promise(r=>setImmediate(r));assert.deepEqual(events,['select:a','tool:a']);finish();await failed;await second;
 assert.deepEqual(events,['select:a','tool:a','release:a','select:b','tool:b','release:b']);
});
test('lost scope acknowledgement releases only that native execution and never dispatches the action',async()=>{
 let hook;const events=[];installWorkspaceBrowser({on:(_name,fn)=>{hook=fn;}},async(action,input)=>{events.push(action+':'+input.id);if(action==='select')throw Error('connection lost');});
 await assert.rejects(hook({name:'mcp__browser__browser_click',arguments:{target:'button'},callId:'uncertain-select',agent:{session:{id:'session',header:{cwd:'C:/workspace'}}}},async()=>{throw Error('must not dispatch');}),/connection lost/);
 assert.deepEqual(events,['select:uncertain-select','release:uncertain-select']);
});
class FakePage extends EventEmitter{
 constructor(context,url='about:blank'){super();this.owner=context;this.address=url;this.closed=false;}
 url(){return this.address;}async goto(url){this.address=url;this.emit('framenavigated',this);}
 async close(){this.closed=true;this.emit('close');}async bringToFront(){this.owner.active=this;}
 async title(){return 'Existing tab';}async screenshot(){return Buffer.from('fixture-jpeg');}
}
class FakeContext extends EventEmitter{
 constructor(){super();this.all=[new FakePage(this)];}pages(){return this.all.filter(p=>!p.closed);}
 async newPage(){const page=new FakePage(this);this.all.push(page);this.emit('page',page);return page;}
 async close(){for(const page of this.pages())await page.close();this.emit('close');}
}
test('browser lifecycle restores saved pages, limits open profiles and does not save credential queries',async t=>{
 const {root,a,b}=fixture(t),profiles=[];const manager=new WorkspaceBrowserManager({root,origins:['https://example.com'],maxOpen:1,launch:async profile=>{profiles.push(profile);return new FakeContext();}});
 const one=manager.workspace(a),two=manager.workspace(b);let context=await manager.context(one);await context.pages()[0].goto('https://example.com/feed?token=SECRET');await context.newPage().then(p=>p.goto('https://example.com/account'));
 await manager.context(two);assert.equal(one.context,null);assert.deepEqual(one.state.state.tabs,['https://example.com/feed','https://example.com/account']);
 context=await manager.context(one);assert.equal(two.context,null);assert.deepEqual(context.pages().map(p=>p.url()),one.state.state.tabs);assert.equal(profiles[0],profiles[2]);assert.notEqual(profiles[0],profiles[1]);
 await context.close();assert.equal(one.context,null);assert.equal(one.state.state.tabs.length,2);await manager.close();
});
test('workspace preview uses existing pages, excludes login routes and never creates replacement tabs',async t=>{
 const {root,a}=fixture(t);let launches=0;const manager=new WorkspaceBrowserManager({root,origins:['https://example.com'],launch:async()=>{launches++;return new FakeContext();}});const workspace=manager.workspace(a);
 const closed=await manager.inspect(workspace);assert.equal(closed.live,false);assert.equal(launches,0);
 const context=await manager.context(workspace);await context.pages()[0].goto('https://example.com/feed?token=SECRET');const second=await context.newPage();await second.goto('https://example.com/account');await context.newPage().then(p=>p.goto('https://example.com/login'));
 const preview=await manager.inspect(workspace);assert.equal(preview.tabDetails.length,2);assert.ok(preview.image.startsWith('data:image/jpeg;base64,'));assert.ok(preview.tabDetails.every(p=>!p.url.includes('?')));const ids=preview.tabDetails.map(p=>p.id);
 await manager.inspect(workspace,{tabId:ids[1],focus:true});assert.equal(context.active,second);assert.equal(context.pages().length,3);assert.equal(launches,1);
 assert.deepEqual((await manager.inspect(workspace)).tabDetails.map(p=>p.id),ids);
 await assert.rejects(manager.inspect(workspace,{tabId:'stale-id',focus:true}),/changed/);manager.select(call(a));assert.equal((await manager.inspect(workspace)).busy,true);await assert.rejects(manager.inspect(workspace,{tabId:ids[0],focus:true}),/active/);manager.release('native-1');await manager.close();
});
