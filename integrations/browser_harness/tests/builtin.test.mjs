import test from 'node:test';
import assert from 'node:assert/strict';
import { BrowserBridge } from '../bridge.mjs';
import { BrowserAdapter } from '../index.mjs';
import { BrowserDriver } from '../browser-driver.mjs';

test('managed browser waits for a response placeholder to recover without resending', async () => {
  const driver = new BrowserDriver(); driver.site = 'chatgpt-web'; driver.enabled = true; driver.isConnected = () => true;
  let probes = 0; let sends = 0; const events = [];
  driver.page = {};
  driver.first = async () => ({ evaluate: async () => '', fill: async () => {} });
  driver.waitForSend = async () => ({ click: async () => { sends++; } });
  driver.pageState = async () => ++probes === 1 ? { stopped: true, responses: [] } : { stopped: true,
    responses: [{ key: 'new', complete: true, text: probes === 2 ? 'This response couldn’t load' : 'Recovered answer' }] };
  await driver.run({ id: 'loading', site: 'chatgpt-web', sessionId: 'one', prompt: 'Say hello' }, event => events.push(event));
  assert.equal(sends, 1);
  assert.ok(events.some(event => event.type === 'status' && event.state === 'response-loading'));
  assert.ok(events.some(event => event.type === 'status' && event.state === 'receiving'));
  assert.equal(events.at(-1).type, 'done'); assert.equal(events.at(-1).text, 'Recovered answer');
  assert.equal(events.some(event => event.text?.includes('couldn’t load')), false);
});
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const token = 'local-test-connection-token-01234567890123456789';
async function fixture(t, controller) {
  const bridge = await new BrowserBridge({ port: 0, token, controller, timeoutMs: 3000 }).start();
  t.after(() => bridge.close());
  const base = `http://127.0.0.1:${bridge.port}`;
  const request = (path, body, authorized = true, origin) => fetch(base + path, {
    method: body === undefined ? 'GET' : 'POST', headers: { ...(authorized ? { Authorization: `Bearer ${token}` } : {}),
      'Content-Type': 'application/json', ...(origin ? { Origin: origin } : {}) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return { bridge, base, request };
}
const collect = async iterable => { const events = []; for await (const event of iterable) events.push(event); return events; };

test('standalone UI is removed and browser actions remain authenticated', async t => {
  const controller = { status: () => ({ transport: 'builtin', enabled: false }), close: async () => {}, open: async site => ({ site }) };
  const { request, base } = await fixture(t, controller);
  const page = await request('/', undefined, false); assert.equal(page.status, 401);
  assert.equal((await request('/')).status, 404);
  assert.equal((await request('/ui/status', undefined, false)).status, 401);
  assert.equal((await request('/ui/open', { site: 'chatgpt-web' }, false, base)).status, 401);
  assert.equal((await request('/ui/open', { site: 'chatgpt-web' }, true, 'https://evil.example')).status, 403);
  const opened = await request('/ui/open', { site: 'chatgpt-web' }, true, base);
  assert.deepEqual(await opened.json(), { site: 'chatgpt-web' });
  assert.equal((await request('/../connection.json')).status, 404);
});

test('built-in browser owns dispatch and streams into the native adapter without extension polling', async t => {
  let calls = 0;
  const controller = { isConnected: () => true, status: () => ({ enabled: true, site: 'chatgpt-web' }), close: async () => {},
    async run(job, publish) { calls++; assert.equal(job.sessionId, 'a');
      publish({ type: 'snapshot', text: 'Browser' }); publish({ type: 'done', text: 'Browser connected' }); } };
  const { bridge, request } = await fixture(t, controller);
  const chunks = await collect(new BrowserAdapter(bridge, { introduction: false }).stream({ model: 'chatgpt-web', sessionId: 'a', messages: [] }));
  assert.equal(chunks.filter(event => event.type === 'text-delta').map(event => event.text).join(''), 'Browser connected');
  assert.equal(chunks.at(-1).reason.kind, 'stop'); assert.equal(calls, 1);
  const poll = await request('/poll', { sites: ['chatgpt-web'] }); assert.deepEqual((await poll.json()).commands, []);
});

test('disconnected built-in browser fails with panel guidance rather than waiting for an extension', async t => {
  const { bridge } = await fixture(t, { isConnected: () => false, close: async () => {} });
  await assert.rejects(collect(bridge.request('chatgpt-web', 'test')), /Settings → Models/);
  assert.equal(bridge.jobs.size, 0);
});

test('cancelling a built-in request reaches its browser worker and releases the request slot', async t => {
  let cancelled = false; let begin;
  const began = new Promise(resolve => { begin = resolve; });
  const controller = { isConnected: () => true, close: async () => {},
    run(_job, _publish, signal) { begin(); return new Promise((resolve, reject) => signal.addEventListener('abort', () => {
      cancelled = true; reject(new Error('cancelled browser request')); }, { once: true })); } };
  const { bridge } = await fixture(t, controller); const abort = new AbortController();
  const result = collect(bridge.request('chatgpt-web', 'test', abort.signal));
  const rejection = assert.rejects(result, { name: 'AbortError' }); await began; abort.abort(); await rejection;
  assert.equal(cancelled, true); assert.equal(bridge.jobs.size, 0);
});

test('browser worker is lazy, rejects unknown websites and closes only its owned context', async () => {
  const driver = new BrowserDriver(); assert.equal(driver.status().browserOpen, false);
  assert.equal(driver.status().tabs, 0); await assert.rejects(driver.open('unknown'), /supported website/);
  await assert.rejects(driver.connect('chatgpt-web'), /Open this website/);
  let closes = 0;
  driver.context = { async close() { closes++; } }; await driver.close(); assert.equal(closes, 1);
});

test('conversation reset uses existing page UI and preserves unsent drafts', async () => {
  const driver = new BrowserDriver(); driver.site = 'chatgpt-web'; let clicks = 0;
  const button = { filter() { return this; }, first() { return this; }, async count() { return 1; }, async click() { clicks++; } };
  driver.page = { getByRole: () => button };
  driver.first = async () => ({ evaluate: async () => 'personal draft' });
  await assert.rejects(driver.fresh(), /unsent draft/); assert.equal(clicks, 0);
  driver.first = async () => ({ evaluate: async () => '' });
  driver.requests = 6; driver.characters = 200000;
  await driver.fresh(); assert.equal(clicks, 1); assert.equal(driver.requests, 0); assert.equal(driver.characters, 0);
});

test('startup restores last website; explicit disconnect persists across restarts', async t => {
  const folder = await mkdtemp(join(tmpdir(), 'harness-preferences-'));
  t.after(() => rm(folder, { recursive: true, force: true }));
  const preferencesFile = join(folder, 'preferences.json');
  await writeFile(preferencesFile, JSON.stringify({ site: 'gemini-web', autoConnect: true }));
  const driver = new BrowserDriver({ preferencesFile }); let opened;
  driver.open = async site => { opened = site; driver.site = site; };
  await driver.start(); assert.equal(opened, 'gemini-web');
  await driver.disconnect();
  assert.deepEqual(JSON.parse(await readFile(preferencesFile)), { site: 'gemini-web', autoConnect: false });
  opened = undefined; await driver.start(); assert.equal(opened, undefined);
});

test('readiness accepts an editable signed-out chat without checking account state', async () => {
  const driver = new BrowserDriver(); driver.site = 'chatgpt-web';
  driver.page = { isClosed: () => false, url: () => 'https://chatgpt.com/' };
  let editable = true; driver.first = async (selectors, options) => {
    assert.ok(selectors.includes('#mobile-composer-prompt')); assert.equal(options.editable, true); return editable ? {} : null;
  };
  assert.equal(await driver.checkReady(), true); assert.equal(driver.isConnected('chatgpt-web'), true);
  editable = false; assert.equal(await driver.checkReady(), false); assert.equal(driver.enabled, false);
  assert.match(driver.phase, /Waiting/);
  driver.page.url = () => 'https://accounts.google.com/';
  editable = true; assert.equal(await driver.checkReady(), false); assert.equal(driver.enabled, false);
});

test('website startup failure is contained and a fresh install defaults to ChatGPT', async t => {
  const folder = await mkdtemp(join(tmpdir(), 'harness-preferences-'));
  t.after(() => rm(folder, { recursive: true, force: true }));
  const driver = new BrowserDriver({ preferencesFile: join(folder, 'preferences.json') }); let attempted;
  driver.open = async site => { attempted = site; throw new Error('offline'); };
  await driver.start(); assert.equal(attempted, 'chatgpt-web');
});

test('connection check sends a small prompt and only records a completed reply', async () => {
  const driver = new BrowserDriver(); driver.site = 'chatgpt-web';
  driver.run = async (job, publish, signal) => {
    assert.ok(job.prompt.length < 100); assert.equal(job.site, 'chatgpt-web'); assert.equal(signal.aborted, false);
    publish({ type: 'snapshot', text: 'partial' }); publish({ type: 'done', text: 'HARNESS_CONNECTION_OK' });
  };
  assert.equal((await driver.testConnection()).testReply, 'HARNESS_CONNECTION_OK');
  driver.testReply = ''; driver.run = async () => { throw new Error('website unavailable'); };
  await assert.rejects(driver.testConnection(), /website unavailable/); assert.equal(driver.testReply, '');
});

test('signed-out ChatGPT response regions retain identity and wait for visible response actions', async () => {
  const driver = new BrowserDriver(); driver.site = 'chatgpt-web'; let done = false;
  const turn = { id: 'assistant-turn-uuid', querySelectorAll: () => [{
    getAttribute: () => 'Copy response', getClientRects: () => done ? [1] : [],
  }] };
  const response = { getClientRects: () => [1], innerText: 'HARNESS_CONNECTION_OK', closest: selector => {
    assert.equal(selector, 'li'); return turn;
  } };
  driver.page = {
    evaluate: async () => ({ responses: [], stopped: true, error: '' }),
    getByRole: (role, options) => {
      assert.equal(role, 'region'); assert.deepEqual(options, { name: 'DIL content', exact: true });
      return { evaluateAll: async read => read([response]) };
    },
  };
  const streaming = await driver.pageState();
  assert.deepEqual(streaming.responses, [{ key: 'assistant-turn-uuid', text: 'HARNESS_CONNECTION_OK', complete: false }]);
  done = true; const finished = await driver.pageState();
  assert.equal(finished.responses[0].key, streaming.responses[0].key);
  assert.equal(finished.responses[0].complete, true);
});

test('send waits for a rendered, enabled button and respects cancellation', async () => {
  const driver = new BrowserDriver(); driver.site = 'chatgpt-web'; let probes = 0;
  const button = { isEnabled: async () => probes >= 3 };
  driver.first = async () => ++probes === 1 ? null : button;
  assert.equal(await driver.waitForSend(undefined, 2000), button); assert.equal(probes, 3);
  const abort = new AbortController(); abort.abort();
  await assert.rejects(driver.waitForSend(abort.signal), { name: 'AbortError' });
});
