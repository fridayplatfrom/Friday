import test from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import fs from 'node:fs';
function article(index,text,native){
 const attrs={'data-testid':'conversation-turn-'+index,...(native?{'data-turn-key':native}:{})};
 const user=text===null?null:{textContent:text,getAttribute:()=>null,querySelector:()=>null};
 return {attrs,user,getAttribute:key=>attrs[key]||null,setAttribute:(key,value)=>{attrs[key]=value;},closest(){return attrs['data-turn-key']?this:null;},querySelector:()=>user};
}
function load(articles){const context={location:{hostname:'chatgpt.com'},document:{body:{},querySelectorAll:()=>articles},MutationObserver:class{observe(){}},queueMicrotask};vm.runInNewContext(fs.readFileSync(new URL('../extension/turns.js',import.meta.url),'utf8'),context);return context.FridayTurns;}
test('separate user and assistant articles share one stable request key without requiring foreground rendering',()=>{
 const id='aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa',u=article(1,'HARNESS_REQUEST_ID '+id+'\nFull prompt'),a=article(2,null);
 load([u,a]);assert.equal(u.attrs['data-turn-key'],'friday-turn:'+id);assert.equal(a.attrs['data-turn-key'],u.attrs['data-turn-key']);
 const remount=article(1,'HARNESS_REQUEST_ID '+id+'\nFull prompt');load([remount]);assert.equal(remount.attrs['data-turn-key'],u.attrs['data-turn-key']);
});
test('native website grouping is preserved and repeated human text does not merge distinct turns',()=>{
 const native=article(1,'human','website-key'),a=article(2,null),u2=article(3,'same text'),a2=article(4,null),u3=article(5,'same text'),a3=article(6,null);
 const sync=load([native,a,u2,a2,u3,a3]);sync.sync();assert.equal(native.attrs['data-turn-key'],'website-key');assert.equal(a.attrs['data-turn-key'],'website-key');
 assert.notEqual(u2.attrs['data-turn-key'],u3.attrs['data-turn-key']);assert.equal(a2.attrs['data-turn-key'],u2.attrs['data-turn-key']);assert.equal(a3.attrs['data-turn-key'],u3.attrs['data-turn-key']);
 assert.equal(native.attrs['data-friday-derived-turn'],undefined);
});
test('assistant-only content before a known user turn is never attributed to a new request',()=>{
 const a=article(1,null);load([a]);assert.equal(a.attrs['data-turn-key'],undefined);
});
