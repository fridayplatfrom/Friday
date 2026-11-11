import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {protectedTaskContext,createOwnedPage} from '../protected-browser.mjs';
import {SharedBrowserWorker} from '../shared-browser-worker.mjs';
import {sharedBrowserProfile} from '../shared-browser-config.mjs';
import {BrowserBridge} from '../bridge.mjs';

class Page extends EventEmitter{
 constructor(context,url='about:blank'){super();this.owner=context;this.address=url;this.closed=false;this.scripts=[];this.front=0;}
 url(){return this.address;}context(){return this.owner;}isClosed(){return this.closed;}mainFrame(){return this;}
 async goto(url){this.address=url;this.emit('framenavigated',this);}
 async close(){this.closed=true;this.emit('close');}async addInitScript(script){this.scripts.push(script);}
 async exposeBinding(name,callback){this.binding=callback;}async evaluate(){return {ok:true,hasEditor:true};}async bringToFront(){this.front++;}
}
class Context extends EventEmitter{
 constructor(){super();this.all=[];this.routes=[];this.browserHandle=new EventEmitter();this.browserHandle.contexts=()=>[this];this.browserHandle.close=()=>{this.browserClosed=true;};}
 pages(){return this.all.filter(page=>!page.closed);}browser(){return this.browserHandle;}
 async newPage(){const page=new Page(this);this.all.push(page);this.emit('page',page);return page;}
 async route(pattern,handler){this.routes.push({pattern,handler});}async unroute(pattern,handler){this.routes=this.routes.filter(route=>route.handler!==handler);}
 async close(){this.closed=true;for(const page of this.all)await page.close();}async cookies(){return [{name:'login',value:'PRIVATE'}];}
}
test('native MCP task view excludes model page and cannot export login or close shared browser',async()=>{
 const context=new Context(),protectedPages=new Set(),model=await context.newPage();model.address='https://chatgpt.com/c/protected';protectedPages.add(model);
 const task=await context.newPage(),guard=protectedTaskContext(context,protectedPages);
 assert.equal(guard.pages().length,1);assert.equal(guard.pages()[0].context(),guard);
 assert.throws(()=>guard.cookies(),/protected/);assert.throws(()=>guard.storageState(),/protected/);assert.throws(()=>guard.browser().close(),/lifecycle/);
 assert.deepEqual(guard.browser().contexts(),[guard]);await guard.close();assert.equal(task.closed,true);assert.equal(model.closed,false);assert.equal(context.closed,undefined);
});
test('protected model page creation never leaks through page events, while task pages still do',async()=>{
 const context=new Context(),protectedPages=new Set(),guard=protectedTaskContext(context,protectedPages),seen=[];
 guard.on('page',page=>seen.push(page));
 const [model,task]=await Promise.all([createOwnedPage(context,protectedPages,true),guard.newPage()]);
 assert.ok(protectedPages.has(model));assert.equal(seen.length,1);assert.equal(seen[0],task);assert.deepEqual(guard.pages(),[task]);
});
test('native origin routes skip the model page but still enforce task traffic, and can be removed',async()=>{
 const context=new Context(),protectedPages=new Set(),model=await context.newPage(),task=await context.newPage();protectedPages.add(model);
 const guard=protectedTaskContext(context,protectedPages);let blocked=0,fallback=0;const handler=()=>blocked++;
 await guard.route('**',handler);const route={fallback(){fallback++;}};
 await context.routes[0].handler(route,{frame:()=>({page:()=>model})});await context.routes[0].handler(route,{frame:()=>({page:()=>task})});assert.equal(fallback,1);assert.equal(blocked,1);
 await guard.unroute('**',handler);assert.equal(context.routes.length,0);
});
test('native page scripts affect only task pages and inherit into future task pages',async()=>{
 const context=new Context(),protectedPages=new Set(),model=await context.newPage();protectedPages.add(model);const guard=protectedTaskContext(context,protectedPages),task=await guard.newPage();
 await guard.addInitScript('taskOnly');const next=await guard.newPage();assert.equal(model.scripts.length,0);assert.deepEqual(task.scripts,['taskOnly']);assert.deepEqual(next.scripts,['taskOnly']);
});
test('shared profile migration preserves plugin identities, Chrome executable, origins and unrelated settings',()=>{
 const profile='- insert:\n    - id: harness-browser-provider\n      config:\n        browserMode: extension\n    - id: harness-playwright\n      name: native-mcp\n      config:\n        serverName: browser\n        args: ["C:/node_modules/@playwright/mcp/cli.js", "--executable-path", "C:/Chrome/chrome.exe", "--isolated", "--allowed-origins", "http://127.0.0.1:8010", "--image-responses", "omit"]\n- id: unchanged\n  value: keep\n';
 const result=sharedBrowserProfile(profile,'C:/shared-browser-mcp.mjs','C:/friday-profile');
 assert.ok(result.includes('browserMode: shared'));assert.ok(!result.includes('--isolated'));assert.ok(result.includes('C:/Chrome/chrome.exe'));assert.ok(result.includes('http://127.0.0.1:8010'));assert.ok(result.endsWith('- id: unchanged\n  value: keep\n'));
 assert.equal(sharedBrowserProfile(result,'C:/shared-browser-mcp.mjs','C:/friday-profile'),result);
 assert.throws(()=>sharedBrowserProfile(profile.replace('--isolated','--unknown'),'x','y'),/Unsupported/);assert.throws(()=>sharedBrowserProfile(profile.replace('harness-playwright','other'),'x','y'),/no browser added/);
});
test('shared worker persists pairing/settings and reuses model tab across jobs without launching browsers',async t=>{
 const directory=await mkdtemp(join(tmpdir(),'friday-shared-test-'));t.after(()=>rm(directory,{recursive:true,force:true}));
 const context=new Context(),protectedPages=new Set(),requests=[];
 const worker=new SharedBrowserWorker(context,{directory,protectedPages,connection:{token:'test',port:1},fetchImpl:async(url,options)=>{requests.push({url,input:options.body&&JSON.parse(options.body)});return {ok:true,json:async()=>({commands:[],actions:[],activeIds:[],listeners:[]})};}});
 await worker.start();t.after(()=>worker.stop());
 const pair={sessionId:'session1',site:'chatgpt-web',url:'https://chatgpt.com/',tabId:1000000};worker.bindings.set('session1:chatgpt-web',pair);
 const first=await worker.providerPage(pair.site,pair),again=await worker.providerPage(pair.site,pair);assert.equal(first,again);assert.equal(context.pages().length,1);assert.ok(protectedPages.has(first));
 await first.goto('https://chatgpt.com/c/test?secret=never-save');await worker.updateBinding(first);await worker.save();const saved=JSON.parse(await readFile(join(directory,'shared-browser.json'),'utf8'));assert.equal(saved.bindings[0].url,'https://chatgpt.com/c/test');assert.ok(!JSON.stringify(saved).includes('secret'));
 const task=await context.newPage();assert.equal((await worker.message(task,{type:'harness-event',event:{id:'x'}}).catch(error=>error)).message,'Model page origin not allowed');
 assert.match((await worker.message(first,{type:'harness-event',event:{id:'foreign'}}).catch(error=>error)).message,/Unowned/);
 assert.ok(requests.some(item=>item.input?.transport==='shared-browser'));
});
test('shared migration handles native YAML formatter multiline arrays and continued Windows paths',()=>{
 const original='- insert:\n    - id: harness-browser-provider\n      config:\n        browserMode: extension\n    - id: harness-playwright\n      config:\n        args:\n          [\n            "C:/long/pa\\\n              th/node_modules/@playwright/mcp/cli.js",\n            "--executable-path", "C:/Chrome/chrome.exe",\n            "--isolated", "--allowed-origins", "http://127.0.0.1:8010"\n          ]\n- id: custom\n  value: !!js anything()\n';
 const result=sharedBrowserProfile(original,'C:/shared-browser-mcp.mjs','C:/friday-profile');assert.ok(result.includes('"C:/shared-browser-mcp.mjs"'));assert.ok(result.endsWith('- id: custom\n  value: !!js anything()\n'));
});
test('shared transport rejects old extension polling before it can claim requests or change heartbeat',async t=>{
 const token='shared-transport-test-token-0123456789',bridge=await new BrowserBridge({token,port:0,transportMode:'shared-browser'}).start();t.after(()=>bridge.close());
 const request=async body=>fetch(`http://127.0.0.1:${bridge.port}/poll`,{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(body)});
 assert.equal((await request({sites:['chatgpt-web'],version:'99'})).status,409);assert.equal(bridge.lastSeen,0);
 assert.equal((await request({transport:'shared-browser',sites:['chatgpt-web'],version:'0.5.0',bindings:[],runningIds:[]})).status,200);assert.ok(bridge.lastSeen>0);assert.equal(bridge.uiStatus().transport,'shared-browser');
 await bridge.uiAction('open',{site:'chatgpt-web'});assert.equal(bridge.actions[0].type,'open-site');
});
