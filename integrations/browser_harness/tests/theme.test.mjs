import {readFileSync} from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {fridayTheme} from '../desktop/theme.mjs';

function fixture(enabled=true){
  const wc=new EventEmitter(), inserted=[],removed=[];let url='http://127.0.0.1:3030/';
  Object.assign(wc,{isDestroyed:()=>false,getURL:()=>url,
    insertCSS:async(css,options)=>{inserted.push({css,options});return 'style-'+inserted.length;},
    removeInsertedCSS:async key=>removed.push(key)});
  return {wc,inserted,removed,url:value=>url=value,theme:fridayTheme({webContents:wc,css:'body{color:plum}',enabled,
    allowed:url=>new URL(url).origin==='http://127.0.0.1:3030'})};
}
test('Friday design is on by default and appearance changes do not navigate, resend or change storage',async()=>{
  const f=fixture();await f.theme.apply();assert.equal(f.inserted.length,1);
  await f.theme.set(true);assert.equal(f.inserted.length,2);assert.equal(f.inserted[0].options.cssOrigin,'user');
  await f.theme.set(false);assert.deepEqual(f.removed,['style-1','style-2']);assert.equal(f.theme.enabled,false);
});
test('theme cannot apply to a provider or lookalike origin',async()=>{
  const f=fixture(true);for(const url of ['https://chatgpt.com/','http://127.0.0.1:3030.evil.test/','file:///shell.html']){
    f.url(url);await f.theme.apply();
  }assert.equal(f.inserted.length,0);
});
test('refresh reapplies one stylesheet and rapid toggles leave the final selection',async()=>{
  const f=fixture(true);await f.theme.apply();
  f.wc.emit('did-start-navigation',{},'http://127.0.0.1:3030/',false,true);
  f.wc.emit('did-finish-load');await f.theme.apply();
  await Promise.all([f.theme.set(false),f.theme.set(true),f.theme.set(false)]);
  assert.equal(f.theme.enabled,false);assert.equal(f.removed.at(-1),'style-3');
});

test('web startup installs the shared design once without navigation or storage writes',async()=>{
  const {runInNewContext}=await import('node:vm');
  const {fridayCSS,fridayThemeScript}=await import('../theme.mjs');
  const nodes=[];const document={head:{append:s=>nodes.push(s)},getElementById:id=>nodes.find(s=>s.id===id),createElement:type=>({type})};
  runInNewContext(fridayThemeScript(),{document});runInNewContext(fridayThemeScript(),{document});
  assert.equal(nodes.length,1);assert.equal(nodes[0].type,'style');assert.equal(nodes[0].textContent,fridayCSS());
});

test('early boot branding waits for native splash and preserves its error and progress nodes',async()=>{
  const {runInNewContext}=await import('node:vm');
  let visible=false,notify,disconnected=false;
  const mark={setAttribute(){},replaceChildren(...nodes){this.children=nodes;}},hint={textContent:'Loading plugins…',hidden:false};
  const progress={value:0.4},failure={text:'Real startup error'};
  const boot={progress,failure,querySelector:selector=>selector.includes('_wordmark_')?mark:selector.includes('_hint_')?hint:null};
  const document={documentElement:{},querySelector:()=>visible?boot:null,createElement:type=>({type,style:{}})};
  class Observer{constructor(fn){notify=fn;}observe(){}disconnect(){disconnected=true;}}
  runInNewContext(readFileSync(new URL('../boot-branding.js',import.meta.url),'utf8'),{document,MutationObserver:Observer,setTimeout(){}});
  assert.equal(mark.children,undefined);visible=true;notify();
  assert.equal(mark.children[0].alt,'Friday');assert.equal(mark.children[0].src,'/browser-models/brand/friday.png');
  assert.equal(hint.hidden,true);assert.equal(hint.textContent,'');assert.equal(disconnected,true);
  assert.equal(boot.progress,progress);assert.equal(boot.failure,failure);assert.equal(failure.text,'Real startup error');
});
