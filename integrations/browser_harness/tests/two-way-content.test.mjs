import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const script = readFileSync(new URL('../extension/two-way.js', import.meta.url), 'utf8');
test('invalidated extension context stops stale page polling without synchronous errors or duplicate tasks',async()=>{const f=page({invalidate:true});await f.pull({enabled:true});await f.pull({enabled:true});await f.submit();assert.equal(f.sent.length,0);});
function page({invalidate=false,initialText='Create a website',bubbleText}={}) {
  const handlers = {}; const sent = []; let users = []; let turnNodes = []; let mutation; let text = initialText; let id = 0; let timer; let heartbeat;
  const panels=[];
  const node = () => ({ style: {}, isConnected:true, setAttribute() {}, append(item) { if(item?.id==='harness-two-way-status') { item.isConnected=true; panels.push(item); } }, remove() {}, addEventListener() {} });
  const document = { body: node(), createElement: node, addEventListener(type, handler) { handlers[type] = handler; },
    querySelectorAll: selector => selector.includes('data-message-author-role') ? users : selector.includes('data-turn-key') ? turnNodes : [] };
  const composer = { get value() { return text; }, contains: target => target === composer };
  const context = { document, crypto: { randomUUID: () => `00000000-0000-4000-8000-${String(++id).padStart(12, '0')}` }, Date,
    MutationObserver: class { constructor(callback) { mutation = callback; } observe() {} }, setInterval(callback) {timer=callback;},
    chrome: { runtime: { sendMessage(message) { if(invalidate)throw new Error('Extension context invalidated.');sent.push(message); return Promise.resolve(message.type==='harness-listener-refresh'?{ok:true,config:heartbeat}:{ ok: true }); } } } };
  vm.runInNewContext(script, context); const api = context.HarnessTwoWay;
  api.init({ composer: () => composer, responses: () => [], images: () => [], progressTurns: () => [], sendSelectors: ['button.send'],
    cancelActive: () => false, stopWebsite() {} });
  api.configure({ enabled: true, status: 'Ready' });
  return { api, sent, panels, async pull(config) {heartbeat=config;timer();for(let i=0;i<8;i++)await Promise.resolve();}, async submit(trusted = true,click=false) {
    if(click)handlers.click({isTrusted:trusted,target:{closest:()=>true}});
    else handlers.keydown({ isTrusted: trusted, key: 'Enter', shiftKey: false, target: composer });
    const user = { innerText:bubbleText||text }; const turn = { innerText:user.innerText, getAttribute:()=> 'turn-'+id, querySelector:selector=>selector.includes('bubble')?user:null }; user.closest=()=>turn;
    turnNodes.push(turn); users.push(user); text = ''; mutation();
    for (let i = 0; i < 6; i++) await Promise.resolve();
  }, async interactive({ suppressed=false, old=false, trusted=true }={}) {
    const message='Build the selected game'; if(suppressed) api.suppressNext(message);
    if(trusted) handlers.click({isTrusted:true,target:{closest:()=>null}});
    const user={innerText:message}; const turn={innerText:message,getAttribute:()=> 'interactive-'+(++id),querySelector:selector=>selector.includes('bubble')?user:selector.includes('content-search')?{getAttribute:()=> 'fallback-turn-'+(old?0:10)}:null};
    user.closest=()=>turn; turnNodes.push(turn); users.push(user); mutation();
    for(let i=0;i<8;i++) await Promise.resolve();
  }, async observe() { mutation(); for (let i = 0; i < 6; i++) await Promise.resolve(); } };
}

test('trusted native submission is forwarded once after visible user-message confirmation', async () => {
  const fixture = page(); await fixture.submit(); await fixture.observe();
  assert.equal(fixture.sent.length, 1); assert.equal(fixture.sent[0].type, 'harness-web-message');
  assert.equal(fixture.sent[0].text, 'Create a website');
  assert.ok(fixture.api.take(fixture.sent[0].id));
});

test('programmatic Harness submissions cannot echo back as new human requests', async () => {
  const fixture = page(); await fixture.submit(false); await fixture.observe(); assert.equal(fixture.sent.length, 0);
});
test('trusted desktop Send and Enter respect outbound suppression without echoing or capturing',async()=>{
 for(const click of [false,true]){
  const f=page();f.api.suppressNext('Create a website');await f.submit(true,click);await f.observe();
  assert.equal(f.sent.length,0);
 }
});
test('outbound transport ID remains suppressed when the visible prompt is reformatted or shortened',async()=>{
 const prefix='HARNESS_REQUEST_ID aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa';
 const prompt=prefix+'\n\nInstructions ```json {"long":"catalog"} ```';
 const f=page({initialText:prompt,bubbleText:prefix+'\nInstructions json … Show more'});
 f.api.suppressNext(prompt);await f.submit(true,true);await f.observe();assert.equal(f.sent.length,0);
});

test('disabled two-way mode never forwards messages', async () => {
  const fixture = page(); fixture.api.configure({ enabled: false }); await fixture.submit(); assert.equal(fixture.sent.length, 0);
});

test('trusted interactive website action forwards its newly submitted user bubble once',async()=>{
 const fixture=page();await fixture.interactive();await fixture.observe();
 assert.equal(fixture.sent.length,1);assert.equal(fixture.sent[0].text,'Build the selected game');
});

test('explicitly suppressed outbound prompt cannot echo through the user-turn observer',async()=>{
 const fixture=page();await fixture.interactive({suppressed:true});assert.equal(fixture.sent.length,0);
});

test('newly loaded history without a fresh human action is never replayed',async()=>{
 const fixture=page();await fixture.interactive({trusted:false});assert.equal(fixture.sent.length,0);
});

test('scrolling older virtualized history after a human click cannot replay an earlier task',async()=>{
 const fixture=page();await fixture.interactive();await fixture.interactive({old:true});assert.equal(fixture.sent.length,1);
});

test('a status panel removed by website hydration is reattached on the next heartbeat',()=>{
 const fixture=page();const panel=fixture.panels[0];panel.isConnected=false;
 fixture.api.configure({enabled:true,status:'Ready'});assert.equal(panel.isConnected,true);assert.equal(fixture.panels.length,2);
});

test('page pulls connection state when background push delivery is missing',async()=>{
 const fixture=page();await fixture.pull({enabled:false,status:'Disconnected'});await fixture.submit();
 assert.equal(fixture.sent.length,1);assert.equal(fixture.sent[0].type,'harness-listener-refresh');
});
