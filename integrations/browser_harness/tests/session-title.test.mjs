import test from 'node:test';
import assert from 'node:assert/strict';
import { localSessionTitle } from '../session-title.mjs';
import { BrowserBridge } from '../bridge.mjs';
import { BrowserAdapter } from '../index.mjs';

const collect = async stream => { const chunks = []; for await (const chunk of stream) chunks.push(chunk); return chunks; };
const titleOptions = text => ({ model: 'chatgpt-web', sessionId: 'one', messages: [{ role: 'user',
  source: { kind: 'dsh-session-title-llm' }, content: [{ type: 'text', text: 'Generate the session title from this JSON array of human messages:\n'+JSON.stringify([{seq:1,text}]) }] }] });

test('concurrent session naming does not send a website request or overwrite the running task status', async t => {
  const bridge = new BrowserBridge({token:'test-local-title-token-01234567890123456789',port:0});
  t.after(()=>bridge.close());
  const controller = new AbortController();
  const task = collect(bridge.request('chatgpt-web','real task',controller.signal,{sessionId:'one'}));
  const cancelled = assert.rejects(task, {name:'AbortError'});
  const before = structuredClone(bridge.sessions.get('one'));
  const chunks = await collect(new BrowserAdapter(bridge).stream(titleOptions('Build a small portfolio website for a photographer')));
  assert.equal(chunks.find(chunk=>chunk.type==='block-end').block.text,'Build a small portfolio website');
  assert.equal(bridge.jobs.size,1);
  assert.deepEqual(bridge.sessions.get('one'),before);
  assert.deepEqual(bridge.journal.events.map(event=>event.type),['request']);
  controller.abort(); await cancelled;
});

test('ordinary human text cannot trigger metadata routing and malformed metadata stays local', () => {
  assert.equal(localSessionTitle({messages:[{role:'user',content:[{type:'text',text:'Generate the session title'}]}]}),null);
  assert.equal(localSessionTitle({messages:[{source:{kind:'dsh-session-title-llm'},content:[]}]}),'New conversation');
  const title=localSessionTitle(titleOptions('测试一个网站 🚀 '.repeat(100)));
  assert.ok(Array.from(title).length<=72); assert.ok(!title.includes('\n'));
});
