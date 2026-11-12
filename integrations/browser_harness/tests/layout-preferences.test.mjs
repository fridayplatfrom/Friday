import test from 'node:test';import assert from 'node:assert/strict';
import {installLayoutPreferences,nativeLayoutStore} from '../layout-preferences.mjs';
const key='friday.layout.v1';
function fixture(saved){
 let state={layoutInfo:{viewportWidth:1450,rightbar:null,rightbarShown:false}},next=0;
 const listeners=new Set(),timers=new Map(),events=new EventTarget(),writes=[];
 const storage={value:saved,getItem:()=>storage.value,setItem:(k,v)=>{writes.push([k,v]);storage.value=v;}};
 const store={getSnapshot:()=>state,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},actions:{setRightbar:width=>{state={layoutInfo:{...state.layoutInfo,rightbar:Math.min(1015,Math.max(300,Math.round(width)))}};for(const fn of listeners)fn();}}};
 const install=()=>installLayoutPreferences({store,storage,events,setTimer:fn=>{timers.set(++next,fn);return next;},clearTimer:id=>timers.delete(id)});
 return {store,storage,events,writes,timers,install,notify:()=>{for(const fn of listeners)fn();}};
}
test('first use gives browser more room through the native action without opening panels',()=>{
 const f=fixture();const stop=f.install();assert.equal(f.store.getSnapshot().layoutInfo.rightbar,948);assert.equal(f.store.getSnapshot().layoutInfo.rightbarShown,false);assert.equal(f.writes.length,0);stop();
});
test('dragged width persists on release and is restored by a fresh startup',async()=>{
 const f=fixture();const stop=f.install();f.store.actions.setRightbar(840);f.store.actions.setRightbar(875);
 assert.equal(f.writes.length,0);f.events.dispatchEvent(new Event('pointerup'));await Promise.resolve();
 assert.deepEqual(JSON.parse(f.storage.value),{version:1,rightbar:875});assert.equal(f.writes[0][0],key);assert.equal(f.timers.size,0);
 stop();const fresh=fixture(f.storage.value);const cleanup=fresh.install();assert.equal(fresh.store.getSnapshot().layoutInfo.rightbar,875);cleanup();
});
test('unrelated layout notifications and teardown do not overwrite a saved width',()=>{
 const f=fixture(JSON.stringify({version:1,rightbar:810}));const stop=f.install();f.notify();assert.equal(f.timers.size,0);assert.equal(f.writes.length,0);stop();assert.equal(f.writes.length,0);
});
test('shutdown flushes a last drag and removes subscriptions',()=>{
 const f=fixture();const stop=f.install();f.store.actions.setRightbar(900);f.events.dispatchEvent(new Event('pagehide'));assert.equal(JSON.parse(f.storage.value).rightbar,900);stop();f.store.actions.setRightbar(800);assert.equal(f.timers.size,0);assert.equal(f.writes.length,1);
});
test('invalid preferences fall back safely and unavailable storage never disables resizing',()=>{
 for(const saved of ['{bad',JSON.stringify({version:99,rightbar:850}),JSON.stringify({version:1,rightbar:-100}),JSON.stringify({version:1,rightbar:'850'})]){const f=fixture(saved);const stop=f.install();assert.equal(f.store.getSnapshot().layoutInfo.rightbar,948);stop();}
 const f=fixture();f.storage.getItem=()=>{throw Error('denied');};f.storage.setItem=()=>{throw Error('denied');};const stop=f.install();f.store.actions.setRightbar(820);assert.doesNotThrow(stop);assert.equal(f.store.getSnapshot().layoutInfo.rightbar,820);
 assert.doesNotThrow(()=>installLayoutPreferences({store:{},storage:null})());
});

test('native adapter delegates sizing and persists only actual right-divider drags',async()=>{
 const events=new EventTarget();events.innerWidth=1450;let width=948,fullscreen=false;const calls=[];
 const setter=px=>calls.push(px),layout={panels:{setRightbar:setter}};
 const document={querySelector:s=>s==='.mP3x-q_frame'?{getBoundingClientRect:()=>({width:1450}),hasAttribute:()=>fullscreen}:{getBoundingClientRect:()=>({width})}};
 const storage={value:null,getItem(){return this.value;},setItem(k,v){this.value=v;}};
 const store=nativeLayoutStore({layout,document,events});const stop=installLayoutPreferences({store,storage,events});assert.equal(calls[0],948);assert.equal(layout.panels.setRightbar,setter);
 const down=matches=>{const event=new Event('pointerdown');Object.defineProperty(event,'target',{value:{closest:()=>matches?{}:null}});events.dispatchEvent(event);};
 down(false);width=920;events.dispatchEvent(new Event('pointerup'));await Promise.resolve();assert.equal(storage.value,null);
 down(true);width=970;events.dispatchEvent(new Event('pointerup'));await Promise.resolve();assert.equal(JSON.parse(storage.value).rightbar,970);
 fullscreen=true;down(true);width=1450;events.dispatchEvent(new Event('pointerup'));await Promise.resolve();assert.equal(JSON.parse(storage.value).rightbar,970);stop();
});
