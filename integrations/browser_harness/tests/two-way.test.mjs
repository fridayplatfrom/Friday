import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { BrowserBridge } from '../bridge.mjs';
import { BrowserAdapter } from '../index.mjs';
import { INTRODUCTION_VERSION, TOOL_PREFIX } from '../protocol.mjs';

const collect = async stream => { const result = []; for await (const event of stream) result.push(event); return result; };
async function fixture(t) {
  const token = 'two-way-test-token-012345678901234567890';
  const bridge = await new BrowserBridge({ token, port: 0, timeoutMs: 4000 }).start(); t.after(() => bridge.close());
  bridge.sessions.bind({ sessionId: 'one', site: 'chatgpt-web', tabId: 10, url: 'https://chatgpt.com/c/one' });
  bridge.sessions.acknowledgeIntroduction('one', 'chatgpt-web', INTRODUCTION_VERSION);
  bridge.twoWay.enable('one', true);
  const messages = [];
  const agent = { status: 'idle', followup: message => messages.push(message), cancel() {}, whenIdle: async () => {} };
  bridge.resolveAgent = id => id === 'one' ? agent : null;
  const input = { sessionId: 'one', site: 'chatgpt-web', tabId: 10, url: 'https://chatgpt.com/c/one', id: randomUUID(), text: 'Create a landing page' };
  const post = async (path, body, headers = {}) => fetch(`http://127.0.0.1:${bridge.port}${path}`, { method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });
  const poll = async () => (await post('/poll', { sites: ['chatgpt-web'], bindings: [input] })).json();
  return { bridge, messages, agent, input, post, poll };
}

test('website message enters native agent once, adopts its tool call, then returns tool results through the same session', async t => {
  const { bridge, messages, input, post, poll } = await fixture(t);
  assert.equal((await post('/inbound', input)).status, 200);
  assert.equal((await (await post('/inbound', input)).json()).duplicate, true); assert.equal(messages.length, 1);
  assert.equal(messages[0].content[0].text, input.text); assert.equal(messages[0].source.rpcId, input.id);
  const tools = [{ name: 'write', parameters: { type: 'object' } }];
  const first = collect(new BrowserAdapter(bridge).stream({ model: 'chatgpt-web', sessionId: 'one', messages, tools }));
  const { commands: [capture] } = await poll(); assert.equal(capture.externalMessageId, input.id); assert.equal(capture.prompt, '');
  await post('/event', { id: capture.id, type: 'done', text: TOOL_PREFIX + '{"name":"write","arguments":{"file_path":"index.html","content":"demo"}}' });
  const chunks = await first; const call = chunks.find(chunk => chunk.type === 'block-end').block;
  assert.equal(call.type, 'tool-call'); assert.equal(call.name, 'write');
  const next = collect(new BrowserAdapter(bridge).stream({ model: 'chatgpt-web', sessionId: 'one', tools, messages: [
    ...messages, { role: 'assistant', content: [call] }, { role: 'tool', toolCallId: call.id, content: [{ type: 'text', text: 'File created successfully' }] },
  ] }));
  const { commands: [followup] } = await poll(); assert.equal(followup.externalMessageId, undefined);
  assert.ok(followup.prompt.includes('File created successfully')); assert.equal(followup.sessionId, 'one');
  await post('/event', { id: followup.id, type: 'done', text: 'The file was created.' }); await next;
});

test('inbound requests require local authentication, enabled exact pairing, and valid text', async t => {
  const { bridge, input, post, messages } = await fixture(t);
  assert.equal((await post('/inbound', input, { Authorization: '' })).status, 401);
  assert.equal((await post('/inbound', input, { Origin: 'https://chatgpt.com' })).status, 403);
  for (const changes of [{ tabId: 11 }, { url: 'https://chatgpt.com/c/other' }, { site: 'gemini-web' }, { text: '' }, { id: 'bad' }]) {
    assert.equal((await post('/inbound', { ...input, ...changes })).status, 409);
  }
  bridge.twoWay.enable('one', false); assert.equal((await post('/inbound', input)).status, 409); assert.equal(messages.length, 0);
});

test('simultaneous delivery is idempotent and uncertain admissions cannot be replayed', async t => {
  const { bridge, input, messages, agent } = await fixture(t);
  await Promise.all([bridge.twoWay.accept(input), bridge.twoWay.accept(input)]); assert.equal(messages.length, 1);
  const another = { ...input, id: randomUUID() }; let attempts = 0;
  agent.followup = () => { attempts++; throw new Error('uncertain delivery'); };
  await assert.rejects(bridge.twoWay.accept(another), /uncertain delivery/);
  const retry = await bridge.twoWay.accept(another); assert.equal(retry.ok, false); assert.equal(attempts, 1);
});

test('new paired website input automatically restores its saved native conversation once',async t=>{
 const {bridge,input,agent,messages}=await fixture(t);let restored=0,live=false;
 bridge.resolveAgent=()=>live?agent:null;
 bridge.recoverSession=async id=>{assert.equal(id,'one');restored++;live=true;return {provider:'browser-web',model:'chatgpt-web'};};
 assert.match(bridge.twoWay.listeners([input])[0].status,/reconnects when you send/);
 await Promise.all([bridge.twoWay.accept(input),bridge.twoWay.accept(input)]);
 assert.equal(restored,1);assert.equal(messages.length,1);
 await bridge.twoWay.accept(input);assert.equal(restored,1);assert.equal(messages.length,1);
});

test('paired website recovery cannot override a saved different model',async t=>{
 const {bridge,input,messages}=await fixture(t);
 bridge.resolveAgent=()=>null;bridge.recoverSession=async()=>({provider:'browser-web',model:'gemini-web'});
 await assert.rejects(bridge.twoWay.accept(input),/No prompt was submitted/);
 assert.equal(messages.length,0);assert.equal(bridge.sessions.get('one').webReceipts,undefined);
});

test('new website input interrupts the running turn before following up; stop uses the same admission fence', async t => {
  const { bridge, input, agent } = await fixture(t); const events = [];
  agent.status = 'running'; agent.cancel = () => events.push('cancel'); agent.whenIdle = async () => events.push('idle');
  agent.followup = () => events.push('followup');
  await bridge.twoWay.accept(input); assert.deepEqual(events.slice(0, 3), ['cancel', 'idle', 'followup']);
  const beforeStaleStop = events.length;
  await bridge.twoWay.stop({ ...input, jobId: randomUUID() }); assert.equal(events.length, beforeStaleStop);
  await bridge.twoWay.stop(input); assert.equal(events.at(-1), 'cancel');
  await assert.rejects(bridge.twoWay.stop({ ...input, tabId: 99 }), /paired/);
});

test('changing the paired conversation disables listening until explicitly initialized again', async t => {
  const { bridge } = await fixture(t);
  bridge.sessions.bind({ sessionId: 'one', site: 'chatgpt-web', tabId: 10, url: 'https://chatgpt.com/c/new' });
  assert.equal(bridge.sessions.get('one').twoWay, false);
  assert.throws(() => bridge.twoWay.enable('one', true), /initialize/);
});

test('website-origin task cannot switch to a model API route during its tool loop', async t => {
  const { bridge, input, messages } = await fixture(t); await bridge.twoWay.accept(input);
  assert.throws(() => bridge.twoWay.validateRoute({ sessionId: 'one', provider: 'deepseek', model: 'api-model', messages }), /No model API request/);
  assert.doesNotThrow(() => bridge.twoWay.validateRoute({ sessionId: 'one', provider: 'browser-web', model: 'chatgpt-web', messages }));
  assert.doesNotThrow(() => bridge.twoWay.validateRoute({ sessionId: 'one', provider: 'deepseek', model: 'api-model',
    messages: [{ role: 'user', source: { kind: 'user', rpcId: randomUUID() }, content: [{ type: 'text', text: 'New Harness request' }] }] }));
});

test('native agent failures are exposed in the paired website status', async t => {
  const { bridge, input, agent } = await fixture(t); let report;
  agent.ctx = { on: (_event, handler) => { report = handler; return () => {}; } };
  agent.followup = () => report({ error: new Error('The workspace is unavailable') });
  await bridge.twoWay.accept(input);
  assert.equal(bridge.sessions.get('one').phase, 'error');
  assert.equal(bridge.twoWay.listeners([input])[0].status, 'The workspace is unavailable');
});
