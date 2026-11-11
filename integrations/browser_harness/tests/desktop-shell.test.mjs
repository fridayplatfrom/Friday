import test from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import{readFileSync}from'node:fs';
import {dockBounds} from '../desktop/dock.mjs';
const sessionId='session-aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa';
function plugin(){
 const registrations=[],types=[],closers=new Map(),tabs=[],calls=[];
 const React={createElement:(type,props,...children)=>({type,props:props||{},children}),useState:()=>[false,()=>{}],useEffect:()=>{}};
 let exported;
 vm.runInNewContext(readFileSync(new URL('../client.js',import.meta.url),'utf8'),{window:{__ModuleLoader__:{load:module=>{exported=module.factory(name=>name==='react'?React:{Button:'button'});}}}});
 const slots={inject:(_name,fn)=>fn(),register:(definition,Body)=>{registrations.push({definition,Body});return()=>{};}};
 const sidebarRight={openTabs:{getSnapshot:()=>tabs},focus:id=>calls.push(['focus',id]),openTab:kind=>{calls.push(['open',kind]);tabs.push({sessionId,kind,tabId:'native-one'});},registerCloseHandler:(kind,fn)=>{closers.set(kind,fn);return()=>{};}};
 exported.apply({slots,effect:()=>{},inject:(names,fn)=>{if(names.includes('sidebarRight'))fn({slots,sidebarRight,sidebarRightTabs:{register:type=>{types.push(type);return()=>{};}},effect:fn=>fn()});}});
 const Header=registrations.find(r=>r.definition.id==='friday-provider-shortcuts').Body;
 const tree=Header({sessionId});const shortcuts=tree.children[0].type({sessionId});
 return {registrations,types,closers,tabs,calls,shortcuts};
}
test('provider icons reuse the native tab and preserve existing file tabs',()=>{
 const f=plugin();f.tabs.push({sessionId,kind:'documentpreview',tabId:'file-original'});
 assert.equal(f.shortcuts.children.length,4);
 const button=f.shortcuts.children.find(node=>node.props.title==='ChatGPT');button.props.onClick();button.props.onClick();
 assert.deepEqual(f.calls,[['open','friday-provider-chatgpt-web'],['focus','native-one']]);assert.equal(f.tabs[0].tabId,'file-original');
 assert.equal(f.registrations.some(r=>r.definition.name==='conversation.composer.dock'),false);
});
test('provider close protection leaves native Browser and file handlers alone',()=>{
 const f=plugin();assert.equal(f.types.length,4);
 for(const type of f.types){assert.equal(type.keepMounted,true);assert.throws(()=>f.closers.get(type.kind)(),/protected/);}
 assert.equal(f.closers.has('browser'),false);assert.equal(f.closers.has('documentpreview'),false);
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
