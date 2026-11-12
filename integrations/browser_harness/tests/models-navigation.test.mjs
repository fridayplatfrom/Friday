import test from 'node:test';import assert from 'node:assert/strict';
import {hideModelsSettingsNavigation} from '../models-navigation.mjs';
test('only the localized native Models navigation row is hidden; teardown restores it',()=>{
 const row=text=>{const attrs=new Map(),css=new Map();return {textContent:text,style:{getPropertyValue:k=>css.get(k)?.value||'',getPropertyPriority:k=>css.get(k)?.priority||'',setProperty:(k,value,priority)=>css.set(k,{value,priority}),removeProperty:k=>css.delete(k)},getAttribute:k=>attrs.get(k)??null,setAttribute:(k,v)=>attrs.set(k,v),removeAttribute:k=>attrs.delete(k)};};
 const models=row('Modèles'),general=row('Général');let observed,disconnected=false;
 let listener,clicks=0;models.click=()=>{clicks++;};
 const document={body:{},addEventListener:(_name,fn)=>{listener=fn;},removeEventListener:()=>{},querySelectorAll:selector=>{assert.equal(selector,'[data-shortcut-modal="settings"] nav button');return [models,general];}};
 const slots={entries:()=>[{options:{id:'models',label:()=>'Modèles'}}]};
 const stop=hideModelsSettingsNavigation({document,slots,observe:callback=>({observe:()=>{observed=callback;},disconnect:()=>{disconnected=true;}})});
 assert.equal(models.style.getPropertyValue('display'),'none');assert.equal(models.getAttribute('aria-hidden'),'true');assert.equal(general.style.getPropertyValue('display'),'');
 observed();assert.equal(clicks,0);listener();observed();assert.equal(clicks,1);
 stop();assert.equal(models.style.getPropertyValue('display'),'');assert.equal(models.getAttribute('aria-hidden'),null);assert.equal(disconnected,true);
});
