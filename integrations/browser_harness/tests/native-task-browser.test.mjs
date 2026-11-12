import test from 'node:test';import assert from 'node:assert/strict';import {EventEmitter} from 'node:events';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {TaskBrowserConnection,startTaskBrowserRelay} from '../desktop/task-browser-relay.mjs';
import {nativeTaskContext} from '../native-task-context.mjs';
function fixture(){
 const events=[],calls=[],debuggerAPI=new EventEmitter();let attached=false;
 Object.assign(debuggerAPI,{isAttached:()=>attached,attach:()=>{attached=true;},detach:()=>{attached=false;},sendCommand:async(method,params,child)=>{calls.push({method,params,child});return method==='Target.getTargetInfo'?{targetInfo:{targetId:'native-one',browserContextId:'private',type:'webview',url:'https://example.com'}}:{};}});
 const guest={id:12,debugger:debuggerAPI,isDestroyed:()=>false};const lease={workspace:'cwd:C:/work',sessionId:'session-one',guest};
 const guests={leases:new Map([['one',lease],['provider',{workspace:'provider',sessionId:'session-one',guest:{id:99}}]]),allowedNavigation:url=>url.startsWith('https://')};
 const opened=[];const connection=new TaskBrowserConnection({guests,workspace:lease.workspace,sessionId:lease.sessionId,send:value=>events.push(value),open:async input=>{opened.push(input);return lease;}});
 return {connection,events,calls,lease,guests,guest,opened};
}
test('native relay attaches only the exact task workspace and conversation, without a new window',async()=>{
 const f=fixture();await f.connection.command('Target.setAutoAttach');assert.equal(f.events.length,1);assert.equal(f.events[0].params.targetInfo.type,'page');assert.equal(f.events[0].params.targetInfo.browserContextId,'friday-task-context');
 await f.connection.command('Page.navigate',{url:'https://www.amazon.in/s?k=school+bag'},'12');assert.equal(f.calls.filter(c=>c.method==='Page.navigate').length,1);assert.equal(f.opened.length,0);
 f.connection.dispose();assert.equal(f.guest.debugger.isAttached(),false);assert.equal(f.guest.debugger.listenerCount('message'),0);
});
test('native relay blocks app-wide debug access, cross-profile targets and unsafe navigation',async()=>{
 const f=fixture();await f.connection.command('Target.setAutoAttach');
 for(const [method,params,id]of [['Page.navigate',{url:'file:///secret'},'12'],['Target.attachToTarget',{targetId:'provider'},'12'],['Storage.getCookies',{},'12'],['Browser.getBrowserCommandLine',{}],['Target.createTarget',{url:'javascript:alert(1)'}]])await assert.rejects(f.connection.command(method,params,id));
 f.lease.sessionId='another';await assert.rejects(f.connection.command('Page.navigate',{url:'https://example.com'},'12'),/owned/);f.connection.dispose();
});
test('native tab activation and close go through the original Harness tab controller',async()=>{
 const f=fixture();await f.connection.command('Target.setAutoAttach');await f.connection.command('Target.activateTarget',{targetId:'native-one'});await f.connection.command('Target.closeTarget',{targetId:'native-one'});assert.deepEqual(f.opened,[{focusGuestId:12},{closeGuestId:12}]);f.connection.dispose();
});
test('page activation and text input select the owning native tab and focus its guest first',async()=>{
 const f=fixture(),order=[];f.guest.focus=()=>order.push('guest-focus');f.connection.open=async options=>{order.push('native-tab-'+options.focusGuestId);};
 await f.connection.command('Target.setAutoAttach');await f.connection.command('Page.bringToFront',{},'12');await f.connection.command('Input.insertText',{text:'synthetic test'},'12');
 assert.deepEqual(order,['native-tab-12','guest-focus','native-tab-12','guest-focus']);assert.equal(f.calls.some(c=>c.method==='Page.bringToFront'),false);assert.equal(f.calls.filter(c=>c.method==='Input.insertText').length,1);f.connection.dispose();
});
test('input to an already focused native guest does not repeat UI selection round trips',async()=>{
 const f=fixture();f.guest.isFocused=()=>true;await f.connection.command('Target.setAutoAttach');await f.connection.command('Input.insertText',{text:'synthetic'},'12');assert.equal(f.opened.length,0);assert.equal(f.calls.filter(c=>c.method==='Input.insertText').length,1);f.connection.dispose();
});
test('a changed active conversation stops an existing connection before an action',async()=>{
 const f=fixture();await f.connection.command('Target.setAutoAttach');f.connection.validate=()=>{throw Error('conversation changed');};await assert.rejects(f.connection.command('Page.navigate',{url:'https://example.com'},'12'),/conversation changed/);assert.equal(f.calls.some(c=>c.method==='Page.navigate'),false);f.connection.dispose();
});
test('new native link tabs attach once and subscriptions stop when the connection closes',async()=>{
 const f=fixture(),observers=new Set();f.guests.subscribe=fn=>{observers.add(fn);return()=>observers.delete(fn);};f.connection.dispose();
 const connection=new TaskBrowserConnection({guests:f.guests,workspace:f.lease.workspace,sessionId:f.lease.sessionId,open:async()=>{},send:value=>f.events.push(value)});
 await connection.command('Target.setAutoAttach',{autoAttach:true});
 const second=fixture();second.guest.id=13;f.guests.leases.set('second',{...f.lease,guest:second.guest});for(const callback of observers)callback();for(const callback of observers)callback();await new Promise(setImmediate);
 assert.equal(connection.sessions.size,2);assert.equal(f.events.filter(e=>e.method==='Target.attachedToTarget'&&e.params.sessionId==='13').length,1);connection.dispose();assert.equal(observers.size,0);assert.equal(second.guest.debugger.isAttached(),false);
});
test('desktop relay requires a private token and does not expose a browser debugging port',async t=>{
 const directory=mkdtempSync(join(tmpdir(),'friday-native-relay-')),file=join(directory,'connection.json');const f=fixture();
 const relay=await startTaskBrowserRelay({guests:f.guests,file,connect:async()=>({workspace:f.lease.workspace,sessionId:f.lease.sessionId,open:async()=>f.lease})});t.after(()=>{relay.close();rmSync(directory,{recursive:true,force:true});});
 const config=JSON.parse(readFileSync(file)),url=`http://127.0.0.1:${config.port}/connect`;
 assert.equal((await fetch(url,{method:'POST',body:'{}'})).status,403);
 assert.equal((await fetch(url,{method:'POST',headers:{Authorization:'Bearer '+config.token,Origin:'https://evil.example'},body:'{}'})).status,403);
 const accepted=await fetch(url,{method:'POST',headers:{Authorization:'Bearer '+config.token},body:'{}'});assert.equal(accepted.status,200);assert.match((await accepted.json()).endpoint,/^ws:\/\/127\.0\.0\.1:/);
});
test('missing desktop connection fails closed without falling back to a browser launcher',async()=>{
 await assert.rejects(nativeTaskContext({connectOverCDP(){throw Error('must not run');}},{directory:'C:/work',sessionId:'one'},join(tmpdir(),'friday-nonexistent-'+Date.now())),/No separate browser was launched/);
 const worker=readFileSync(new URL('../workspace-browser-mcp.mjs',import.meta.url),'utf8');assert.doesNotMatch(worker,/launchPersistentContext/);assert.match(worker,/nativeTaskContext/);
});
