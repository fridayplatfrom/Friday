import test from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import fs from 'node:fs';
import {arrangeBackgroundViews,presentedDock} from '../desktop/background.mjs';
import {WebsiteTabManager} from '../extension/tab-manager.js';
function view(name){return {name,shown:false,setVisible(value){this.shown=value;},setBounds(value){this.bounds=value;}};}
test('restored provider tabs remain concealed until explicit reveal in the same session and site',()=>{
 const dock={site:'chatgpt-web',sessionId:'one',visible:true};
 assert.equal(presentedDock(dock,null).visible,false);
 assert.equal(presentedDock(dock,{site:'gemini-web',sessionId:'one'}).visible,false);
 assert.equal(presentedDock(dock,{site:'chatgpt-web',sessionId:'two'}).visible,false);
 assert.equal(presentedDock(dock,{site:'chatgpt-web',sessionId:'one'}).visible,true);
 assert.equal(presentedDock({...dock,visible:false},{site:'chatgpt-web',sessionId:'one'}).visible,false);
});
test('inactive providers keep renderable viewports behind the native workspace; only explicit dock selection reveals one',()=>{
 const native=view('native'),a=view('chatgpt'),b=view('gemini'),order=[];
 const args={contentView:{addChildView:v=>order.push(v.name)},harness:native,pages:[{id:1,view:a},{id:2,view:b}],healthy:true,width:1450,height:900};
 arrangeBackgroundViews(args);assert.equal(a.shown,true);assert.equal(b.shown,true);assert.deepEqual(order,['native']);
 order.length=0;arrangeBackgroundViews({...args,dock:{visible:true,pageId:1,bounds:{x:600,y:40,width:850,height:860}}});
 assert.deepEqual(order,['native','chatgpt']);assert.equal(b.shown,true);
 order.length=0;arrangeBackgroundViews(args);assert.deepEqual(order,['native']);assert.equal(a.shown,true);
 arrangeBackgroundViews({...args,healthy:false});assert.equal(a.shown,false);assert.equal(b.shown,false);
});
function preload(admit){
 const events=[];const context={process:{isMainFrame:true},location:{hostname:'chatgpt.com'},window:{addEventListener(){}},sessionStorage:{setItem(){},getItem(){}},require:()=>({ipcRenderer:{sendSync:()=>({}),on(){},invoke:async(type,input)=>{events.push(type);return admit(input);}}})};
 vm.runInNewContext(fs.readFileSync(new URL('../desktop/provider-preload.cjs',import.meta.url),'utf8'),context);
 const button={isConnected:true,disabled:false,getAttribute:()=>null,getBoundingClientRect:()=>({x:5,y:5,width:20,height:20}),click:()=>events.push('click')};
 return {send:context.FridayDesktopSubmit,button,events};
}
test('background Send waits for durable admission and clicks once without any window focus or mouse dispatch',async()=>{
 const admitted=new Set(),f=preload(({id})=>{if(admitted.has(id))throw Error('already attempted');admitted.add(id);return {ok:true};});
 await f.send('job',f.button);await assert.rejects(f.send('job',f.button),/already attempted/);
 assert.deepEqual(f.events,['friday-submit','click','friday-submit']);
});
test('failed admission and replaced Send controls never trigger clicks or fallback submission',async()=>{
 const refused=preload(()=>({ok:false}));await assert.rejects(refused.send('job',refused.button),/not admitted/);assert.equal(refused.events.includes('click'),false);
 const replaced=preload(()=>{replaced.button.isConnected=false;return {ok:true};});await assert.rejects(replaced.send('job',replaced.button),/changed after admission/);assert.equal(replaced.events.includes('click'),false);
});
test('only explicit Show paired chat reveals a desktop provider; acquisition remains background',async()=>{
 const store={},reveals=[],updates=[];const tab={id:3,url:'https://chatgpt.com/c/saved',windowId:1};
 const chrome={fridayDesktop:{backgroundExecution:true,revealTab:async id=>reveals.push(id)},storage:{local:{get:async key=>({[key]:store[key]}),set:async data=>Object.assign(store,data)}},tabs:{query:async()=>[tab],get:async()=>tab,create:async()=>tab,update:async()=>updates.push('tab')},windows:{update:async()=>updates.push('window')}};
 const manager=new WebsiteTabManager(chrome),command={sessionId:'session-test',site:'chatgpt-web'};
 await manager.acquire(command);assert.deepEqual(reveals,[]);
 await manager.focus(command);assert.deepEqual(reveals,[3]);assert.deepEqual(updates,[]);
});
