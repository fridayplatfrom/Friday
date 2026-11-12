import test from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import{readFileSync}from'node:fs';
import {dockBounds} from '../desktop/dock.mjs';
const sessionId='session-aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa';
function plugin(){
 const registrations=[],types=[],closers=new Map(),tabs=[],calls=[],events=[];let taskHandler;const taskResults=[];
 const React={createElement:(type,props,...children)=>({type,props:props||{},children}),useState:()=>[false,()=>{}],useEffect:()=>{}};
 let exported;
 vm.runInNewContext(readFileSync(new URL('../client.js',import.meta.url),'utf8'),{Event:class{constructor(type){this.type=type;}},document:{querySelectorAll:()=>[{dataset:{sidebarRightTab:'task-selected'},querySelector:()=>({}),querySelectorAll:()=>[]}]},window:{dispatchEvent:event=>events.push(event.type),fridayDesktopWorkspace:{setup:()=>{},onTaskBrowser:fn=>{taskHandler=fn;return()=>{};},taskBrowserResult:(nonce,result)=>taskResults.push({nonce,...result})},__ModuleLoader__:{load:module=>{exported=module.factory(name=>name==='react'?React:{Button:'button'});}}}});
 const slots={inject:(_name,fn)=>fn(),register:(definition,Body)=>{registrations.push({definition,Body});return()=>{};}};
 const sidebarRight={commandTarget:()=>({tabId:'task-selected'}),openTabs:{getSnapshot:()=>tabs},focus:id=>calls.push(['focus',id]),openTab:kind=>{calls.push(['open',kind]);tabs.push({sessionId,kind,tabId:'native-one'});},registerCloseHandler:(kind,fn)=>{closers.set(kind,fn);return()=>{};}};
 exported.apply({slots,effect:()=>{},inject:(names,fn)=>{if(names.includes('sidebarRight'))fn({slots,sidebarRight,sidebarRightTabs:{register:type=>{types.push(type);return()=>{};}},effect:fn=>fn()});}});
 const Header=registrations.find(r=>r.definition.id==='friday-connection-activity').Body;
 const tree=Header({sessionId});const launcher=registrations.find(r=>r.definition.id==='friday-models').Body({wide:false});
 return {registrations,types,closers,tabs,calls,header:tree,launcher,events,taskHandler,taskResults};
}
test('agent reconnect resumes the native selected task tab rather than an older browser tab',async()=>{
 const f=plugin();f.tabs.push({sessionId,kind:'browser',tabId:'older-task'},{sessionId,kind:'browser',tabId:'task-selected'});
 await f.taskHandler({sessionId,nonce:'reconnect',action:'open',fresh:false});assert.deepEqual(f.calls,[['focus','task-selected']]);assert.equal(f.taskResults[0].ok,true);assert.equal(f.tabs.length,2);
});
test('Models moves to the native sidebar footer without duplicate settings or header provider icons',()=>{
 const f=plugin();f.tabs.push({sessionId,kind:'documentpreview',tabId:'file-original'});
 assert.equal(f.header.children.length,1);assert.equal(f.header.children[0].type,'details');
 assert.equal(f.launcher.props['aria-label'],'Models');f.launcher.props.onClick();
 assert.deepEqual(f.events,['friday-show-setup']);assert.deepEqual(f.calls,[]);assert.equal(f.tabs[0].tabId,'file-original');
 assert.equal(f.registrations.some(r=>r.definition.name==='settings.models.footer'),false);
 assert.equal(f.registrations.some(r=>r.definition.name==='conversation.composer.dock'),false);
});
test('provider close protection leaves native Browser and file handlers alone',()=>{
 const f=plugin();assert.equal(f.types.length,4);
 for(const type of f.types){assert.equal(type.keepMounted,true);assert.throws(()=>f.closers.get(type.kind)(),/protected/);}
 assert.equal(f.closers.has('browser'),false);assert.equal(f.closers.has('documentpreview'),false);
});
test('the native Settings launcher stays visible and keeps its original open callback',()=>{
 const f=plugin();const bridge=f.registrations.find(r=>r.definition.name==='settings.launcher').Body;let opened=0;
 const button=bridge({wide:true,openSettings:()=>opened++});assert.equal(button.props['aria-label'],'Settings');assert.equal(button.children.at(-1).children[0],'Settings');
 button.props.onClick();assert.equal(opened,1);
});
test('dock IPC rejects foreign sessions, unsupported providers and out-of-window geometry',()=>{
 const input={sessionId,tabId:'one',site:'chatgpt-web',visible:true,x:600,y:50,width:800,height:800};
 assert.deepEqual(dockBounds(input,sessionId,1450,930),{visible:true,x:600,y:50,width:799,height:799});
 for(const patch of [{sessionId:'other'},{site:'arbitrary'},{x:-1},{width:900},{y:NaN},{tabId:null}])assert.equal(dockBounds({...input,...patch},sessionId,1450,930),null);
 assert.deepEqual(dockBounds({...input,visible:false},sessionId,1450,930),{visible:false});
});
test('desktop shell has no alternate tab strip or screenshot browser',()=>{
 const html=readFileSync(new URL('../desktop/shell.html',import.meta.url),'utf8');assert.doesNotMatch(html,/Your task tabs|browser-preview|id="tabs"|id="providers"|id="divider"/);
});
