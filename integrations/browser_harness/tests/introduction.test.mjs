import test from 'node:test';
import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';
import { BrowserBridge } from '../bridge.mjs';
import { BrowserAdapter } from '../index.mjs';
import { HARNESS_INTRODUCTION, INTRODUCTION_ACK, INTRODUCTION_VERSION } from '../protocol.mjs';

const collect = async iterable => { const chunks = []; for await (const chunk of iterable) chunks.push(chunk); return chunks; };
const options = (sessionId = 'one', text = 'Say hello') => ({ model: 'chatgpt-web', sessionId,
  messages: [{ role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text }] }] });
async function fixture(t) {
  const token = 'test-local-introduction-token-0123456789';
  const bridge = await new BrowserBridge({ token, port: 0, timeoutMs: 4000, connectionGraceMs: 2000 }).start();
  t.after(() => bridge.close());
  const post = async (path, data) => {
    const response = await fetch(`http://127.0.0.1:${bridge.port}${path}`, { method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    const body = await response.json(); assert.equal(response.status, 200, JSON.stringify(body)); return body;
  };
  const next = async () => {
    for (let i = 0; i < 100; i++) {
      const result = await post('/poll', { sites: ['chatgpt-web', 'gemini-web'] });
      if (result.commands.length) return result.commands[0];
      await delay(10);
    }
    throw new Error('No browser command dispatched.');
  };
  const done = (job, text) => post('/event', { id: job.id, type: 'done', text });
  return { bridge, post, next, done };
}

test('introduction precedes the task once; tool follow-ups and adapter restart reuse acknowledgement', async t => {
  const { bridge, post, next, done } = await fixture(t);
  const result = collect(new BrowserAdapter(bridge).stream(options()));
  const intro = await next(); assert.equal(intro.prompt, HARNESS_INTRODUCTION);
  assert.match(intro.prompt, /Never return the prefix alone/);
  assert.equal(bridge.sessions.get('one').message, 'Introducing Harness to ChatGPT');
  await post('/event', { id: intro.id, type: 'binding', tabId: 1, url: 'https://chatgpt.com/c/one' });
  await done(intro, INTRODUCTION_ACK);
  const task = await next(); assert.notEqual(task.id, intro.id); assert.equal(task.sessionId, intro.sessionId);
  assert.ok(task.prompt.includes('Say hello')); assert.notEqual(task.prompt, HARNESS_INTRODUCTION);
  await done(task, 'Hello'); const chunks = await result;
  assert.equal(chunks.filter(chunk => chunk.type === 'text-delta').map(chunk => chunk.text).join(''), 'Hello');
  assert.equal(bridge.sessions.introductionReady('one', 'chatgpt-web', INTRODUCTION_VERSION), true);
  const followup = collect(new BrowserAdapter(bridge).stream({ ...options(), messages: [
    ...options().messages, { role: 'tool', toolCallId: 'call', content: [{ type: 'text', text: 'File saved' }] },
  ] }));
  const continued = await next(); assert.ok(continued.prompt.includes('File saved'));
  assert.notEqual(continued.prompt, HARNESS_INTRODUCTION); await done(continued, 'Verified'); await followup;
});

test('failed acknowledgement never submits the task or marks the conversation initialized', async t => {
  const { bridge, next, done } = await fixture(t);
  const result = collect(new BrowserAdapter(bridge).stream(options()));
  const rejected = assert.rejects(result, /did not acknowledge/);
  await done(await next(), 'I cannot access your computer.'); await rejected;
  assert.equal(bridge.jobs.size, 0);
  assert.equal(bridge.sessions.introductionReady('one', 'chatgpt-web', INTRODUCTION_VERSION), false);
  assert.equal(bridge.sessions.get('one').phase, 'error');
  const retry = collect(new BrowserAdapter(bridge).stream(options()));
  const retryRejected = assert.rejects(retry, /did not acknowledge/);
  const retriedIntro = await next(); assert.equal(retriedIntro.prompt, HARNESS_INTRODUCTION);
  await done(retriedIntro, 'Still not acknowledged'); await retryRejected;
});

test('cancellation during introduction never sends a task', async t => {
  const { bridge, next } = await fixture(t); const abort = new AbortController();
  const result = collect(new BrowserAdapter(bridge).stream({ ...options(), signal: abort.signal }));
  const rejected = assert.rejects(result, { name: 'AbortError' });
  assert.equal((await next()).prompt, HARNESS_INTRODUCTION); abort.abort(); await rejected;
  assert.equal(bridge.jobs.size, 0);
  assert.equal(bridge.sessions.introductionReady('one', 'chatgpt-web', INTRODUCTION_VERSION), false);
});

test('image-only request skips introduction; the next coding task still initializes the same session', async t => {
  const { bridge, next, done } = await fixture(t);
  const image = collect(new BrowserAdapter(bridge).stream(options('one', 'Create a dog image')));
  const job = await next(); assert.equal(job.prompt, 'Create a dog image');
  await done(job, 'Image generation unavailable'); await image;
  assert.equal(bridge.sessions.introductionReady('one', 'chatgpt-web', INTRODUCTION_VERSION), false);
  const task = collect(new BrowserAdapter(bridge).stream(options()));
  await done(await next(), INTRODUCTION_ACK);
  const actual = await next(); assert.ok(actual.prompt.includes('Say hello')); await done(actual, 'Hello'); await task;
});

test('a different Harness session gets its own introduction', async t => {
  const { bridge, next, done } = await fixture(t);
  bridge.sessions.acknowledgeIntroduction('one', 'chatgpt-web', INTRODUCTION_VERSION);
  const result = collect(new BrowserAdapter(bridge).stream(options('two')));
  const intro = await next(); assert.equal(intro.sessionId, 'two'); assert.equal(intro.prompt, HARNESS_INTRODUCTION);
  await done(intro, INTRODUCTION_ACK); await done(await next(), 'Hello'); await result;
});
