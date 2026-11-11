import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { setTimeout as delay } from 'node:timers/promises';
import { BrowserBridge } from '../bridge.mjs';
import { BrowserAdapter } from '../index.mjs';
import { TOOL_PREFIX } from '../protocol.mjs';

const token = 'test-local-pairing-token-01234567890123456789';
async function fixture(t, options = {}) {
  const bridge = await new BrowserBridge({ token, port: 0, timeoutMs: 3000, connectionGraceMs: 1000, ...options }).start();
  t.after(() => bridge.close());
  const request = async (path, body, headers = {}) => fetch(`http://127.0.0.1:${bridge.port}${path}`, {
    method: body === undefined ? 'GET' : 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...headers },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const poll = async () => (await request('/poll', { sites: ['chatgpt-web'] })).json();
  return { bridge, request, poll };
}
const collect = async iterable => { const chunks = []; for await (const chunk of iterable) chunks.push(chunk); return chunks; };

test('native planning and goal tools retain their schemas and return calls to Harness for execution',async t=>{
 const {bridge,request,poll}=await fixture(t);
 const tools=[{name:'todo_write',parameters:{type:'object',properties:{todos:{type:'array',items:{type:'object'}}},required:['todos']}},
 {name:'create_goal',parameters:{type:'object',properties:{objective:{type:'string'}},required:['objective']}}];
 const options={sessionId:'native-controls',model:'chatgpt-web',system:'Workspace Write permissions. Harness owns approvals.',tools,
 messages:[{role:'user',content:[{type:'text',text:'Plan this task'}]}]};
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream(options));const job=await nextCommand(poll);
 assert.ok(job.prompt.includes(JSON.stringify(tools)));assert.ok(job.prompt.includes(options.system));
 const args={todos:[{content:'Inspect the project',status:'in_progress'}]};
 await request('/event',{id:job.id,type:'done',text:TOOL_PREFIX+JSON.stringify({name:'todo_write',arguments:args})});
 const chunks=await result;const block=chunks.find(chunk=>chunk.type==='block-end').block;
 assert.equal(block.type,'tool-call');assert.equal(block.name,'todo_write');assert.deepEqual(JSON.parse(block.arguments),args);
 assert.equal(chunks.at(-1).reason.kind,'tool-calls');
});

test('Harness compaction uses the same provider and returns its summary without a separate workflow',async t=>{
 const {bridge,request,poll}=await fixture(t);
 const directive='You are now acting as a compaction engine. Summarize the previous work.';
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({sessionId:'compact-native',model:'chatgpt-web',purpose:'compaction',
 messages:[{role:'user',content:[{type:'text',text:'Build a store'}]},{role:'assistant',content:[{type:'text',text:'MongoDB backend created; tests pending.'}]},{role:'user',content:[{type:'text',text:directive}]}]}));
 const job=await nextCommand(poll);assert.ok(job.prompt.includes(directive));assert.ok(job.prompt.includes('tests pending'));
 await request('/event',{id:job.id,type:'done',text:'## Current Work\nMongoDB store implemented; runtime tests pending.'});
 const chunks=await result;assert.match(chunks.find(chunk=>chunk.type==='block-end').block.text,/runtime tests pending/);assert.equal(chunks.at(-1).reason.kind,'stop');
});
async function nextCommand(poll) {
  for (let i = 0; i < 100; i++) { const { commands } = await poll(); if (commands.length) return commands[0]; await delay(10); }
  throw new Error('Expected a queued browser command.');
}

test('response-loading status pauses the bridge timeout and exposes waiting status until recovery', async t => {
  let clock = 0;
  const { bridge, poll, request } = await fixture(t, { timeoutMs: 250, now: () => clock });
  const result = collect(bridge.request('chatgpt-web', 'test', undefined, { sessionId: 'loading' }));
  const { commands: [job] } = await poll();
  assert.equal((await request('/event', { id: job.id, type: 'status', state: 'response-loading' })).status, 200);
  clock = 5000; await delay(150);
  assert.equal(bridge.jobs.has(job.id), true);
  assert.equal(bridge.sessions.get('loading').message, 'Response couldn’t load — waiting to load');
  assert.equal(bridge.sessions.get('loading').phase, 'waiting');
  await request('/event', { id: job.id, type: 'status', state: 'receiving' });
  await request('/event', { id: job.id, type: 'done', text: 'Recovered answer' });
  const events = await result;
  assert.deepEqual(events.map(event => event.type), ['done']);
  assert.equal(events[0].text, 'Recovered answer');
});

test('plain-text website revisions finish with the authoritative final block without replaying a task',async t=>{
 const {bridge,poll,request}=await fixture(t);
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({model:'chatgpt-web',sessionId:'rewrite',messages:[]}));
 const job=await nextCommand(poll);
 await request('/event',{id:job.id,type:'snapshot',text:'Preparing file [Download](sandbox:/'});
 await delay(120);
 await request('/event',{id:job.id,type:'snapshot',text:'Download report.csv'});
 await request('/event',{id:job.id,type:'done',text:'Download report.csv'});
 const chunks=await result;
 assert.equal(chunks.find(chunk=>chunk.type==='block-end').block.text,'Download report.csv');
 assert.equal(chunks.some(chunk=>chunk.type==='tool-call-delta'),false);
 assert.equal(bridge.journal.list('rewrite').filter(event=>event.type==='request').length,1);
});

test('cancellation still stops a request waiting beyond its timeout for response loading', async t => {
  let clock = 0;
  const { bridge, poll, request } = await fixture(t, { timeoutMs: 250, now: () => clock });
  const abort = new AbortController();
  const result = collect(bridge.request('chatgpt-web', 'test', abort.signal));
  const rejected = assert.rejects(result, { name: 'AbortError' });
  const { commands: [job] } = await poll();
  await request('/event', { id: job.id, type: 'status', state: 'response-loading' });
  clock = 5000; await delay(150); abort.abort(); await rejected;
  assert.equal(bridge.jobs.size, 0);
  assert.equal((await request('/event', { id: job.id, type: 'done', text: 'late' })).status, 410);
});

test('adapter dispatches only the actual human image prompt even with a huge agent context', async t => {
  const { bridge, request, poll } = await fixture(t);
  const prompt = 'Create a dog image with warm light and a blue collar.';
  const result = collect(new BrowserAdapter(bridge, { introduction: false }).stream({ model: 'chatgpt-web', sessionId: 'direct-image',
    system: 'Code instructions '.repeat(10000), tools: [{ name: 'write', parameters: {} }], messages: [
      { role: 'system', content: [{ type: 'text', text: 'More coding instructions' }] },
      { role: 'user', source: { kind: 'user' }, content: [{ type: 'text', text: prompt }] },
      { role: 'user', source: { kind: 'runtime-context' }, content: [{ type: 'text', text: 'Workspace and permission context' }] },
      { role: 'user', source: { kind: 'time-context' }, content: [{ type: 'text', text: 'Time snapshot' }] },
    ] }));
  const { commands: [job] } = await poll();
  assert.equal(job.prompt, prompt); assert.equal(job.sessionId, 'direct-image');
  await request('/event', { id: job.id, type: 'done', text: 'Image generation is unavailable.' });
  assert.equal((await result).at(-1).reason.kind, 'stop');
});

test('image-only routing cannot execute an agent tool from the website reply', async t => {
  const { bridge, request, poll } = await fixture(t);
  const result = collect(new BrowserAdapter(bridge, { introduction: false }).stream({ model: 'chatgpt-web', sessionId: 'image-no-tools',
    tools: [{ name: 'write', parameters: {} }], messages: [{ role: 'user', content: [{ type: 'text', text: 'Create a dog image' }] }] }));
  const rejected = assert.rejects(result, /tool not offered/);
  const { commands: [job] } = await poll();
  await request('/event', { id: job.id, type: 'done', text: TOOL_PREFIX + '{"name":"write","arguments":{}}' });
  await rejected;
  assert.equal(bridge.sessions.get('image-no-tools').phase, 'error');
});

test('image-only reply preserves reported progress, transfers chunks and yields a persistent image in native chat', async t => {
  const { bridge, request, poll } = await fixture(t);
  const result = collect(new BrowserAdapter(bridge, { introduction: false }).stream({ model: 'chatgpt-web', sessionId: 'image-chat', messages: [] }));
  const { commands: [job] } = await poll(); assert.equal(job.sessionId, 'image-chat');
  const send = async event => { const response = await request('/event', { id: job.id, ...event }); assert.equal(response.status, 200, await response.text()); };
  await send({ type: 'binding', url: 'https://chatgpt.com/c/image-chat', tabId: 123 });
  for (const percent of [null, 7, 27, 65, 97]) await send({ type: 'progress', percent, message: 'Creating image' });
  assert.deepEqual(bridge.sessions.get('image-chat').progress.map(p => p.percent), [7, 27, 65, 97]);
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jp1sAAAAASUVORK5CYII=', 'base64');
  await send({ type: 'image-start', mime: 'image/png', alt: 'Generated image 1' });
  const data = png.toString('base64');
  await send({ type: 'image-chunk', index: 0, data: data.slice(0, 40) });
  await send({ type: 'image-chunk', index: 1, data: data.slice(40) });
  await send({ type: 'image-end' });
  assert.deepEqual(bridge.sessions.get('image-chat').images[0].progress.map(p=>p.percent),[7,27,65,97]);
  assert.equal(bridge.journal.list('image-chat').filter(event=>event.type==='progress').length,5);
  await send({ type: 'done', text: '' });
  const chunks = await result;
  const block = chunks.find(c => c.type === 'block-end').block;
  assert.match(block.text, /!\[Generated image\]\(\/browser-models\/media\//);
  assert.equal(chunks.at(-1).reason.kind, 'stop');
  const state = bridge.sessions.get('image-chat'); assert.equal(state.phase, 'complete');
  assert.equal(state.percent, 97); // Completion does not invent an unseen 100%.
  assert.deepEqual(bridge.sessions.readImage(state.images[0].id).bytes, png);
});

test('malformed image transfers and invalid percentages cannot become successful replies', async t => {
  const { bridge, request, poll } = await fixture(t);
  const result = collect(bridge.request('chatgpt-web', 'image'));
  const rejected = assert.rejects(result, /test ended/);
  const { commands: [job] } = await poll();
  for (const event of [{ type: 'progress', percent: 101 }, { type: 'image-chunk', index: 0, data: 'YWJj' },
    { type: 'image-start', mime: 'image/svg+xml' }]) assert.equal((await request('/event', { id: job.id, ...event })).status, 400);
  await request('/event', { id: job.id, type: 'image-start', mime: 'image/png' });
  assert.equal((await request('/event', { id: job.id, type: 'image-chunk', index: 1, data: 'YWJj' })).status, 400);
  assert.equal((await request('/event', { id: job.id, type: 'done', text: 'ok' })).status, 400);
  await request('/event', { id: job.id, type: 'error', message: 'test ended' }); await rejected;
});

test('bridge rejects missing token, hostile origin and incorrect Host', async t => {
  const { request, bridge } = await fixture(t);
  assert.equal((await request('/status', undefined, { Authorization: '' })).status, 401);
  assert.equal((await request('/poll', {}, { Origin: 'https://chatgpt.com' })).status, 403);
  assert.equal((await request('/poll', {}, { Origin: 'https://evil.example' })).status, 403);
  // Node fetch replaces Host; use raw HTTP to exercise DNS-rebinding defense.
  const wrongHostStatus = await new Promise((resolve, reject) => {
    const req = http.get({ hostname: '127.0.0.1', port: bridge.port, path: '/status',
      headers: { Host: 'evil.example', Authorization: `Bearer ${token}` } }, res => { res.resume(); resolve(res.statusCode); });
    req.on('error', reject);
  });
  assert.equal(wrongHostStatus, 403);
  assert.equal((await request('/status')).status, 200);
});

test('real bridge + adapter stream incrementally and end without fabricated usage', async t => {
  const { bridge, request, poll } = await fixture(t); const adapter = new BrowserAdapter(bridge, { introduction: false });
  const iterator = adapter.stream({ model: 'chatgpt-web', messages: [{ role: 'user', content: [{ type: 'text', text: 'Say hello' }] }] });
  const first = iterator.next();let firstDelivered=false;void first.then(()=>{firstDelivered=true;},()=>{});
  const { commands: [job] } = await poll(); assert.ok(job.prompt.includes('Say hello'));
  await request('/event', { id: job.id, type: 'snapshot', text: 'Hello' });
  await delay(20);assert.equal(firstDelivered,false,'short transient text remains buffered');
  const paragraph='Hello. '+ 'This is the verified application response with useful details. '.repeat(6);
  await request('/event', { id: job.id, type: 'snapshot', text: paragraph });
  assert.equal((await first).value.type, 'block-start');
  assert.equal((await iterator.next()).value.text, paragraph);
  await request('/event', { id: job.id, type: 'snapshot', text: paragraph+'Final detail.' });
  assert.equal((await iterator.next()).value.text, 'Final detail.');
  await request('/event', { id: job.id, type: 'done', text: paragraph+'Final detail.' });
  const rest = await collect(iterator);
  assert.equal(rest[0].type, 'block-end'); assert.deepEqual(rest.at(-1), { type: 'finish', reason: { kind: 'stop' } });
  assert.equal(rest.some(chunk => chunk.type === 'usage'), false); assert.equal(bridge.jobs.size, 0);
  assert.equal((await request('/event', { id: job.id, type: 'done', text: 'late' })).status, 410);
});

test('tool request round trip yields a native tool-call and next prompt carries its result', async t => {
  const { bridge, request, poll } = await fixture(t); const adapter = new BrowserAdapter(bridge, { introduction: false });
  const tools = [{ name: 'read_file', parameters: { type: 'object' } }];
  const result = collect(adapter.stream({ model: 'chatgpt-web', tools, messages: [] }));
  const { commands: [job] } = await poll();
  await request('/event', { id: job.id, type: 'done', text: TOOL_PREFIX + '{"name":"read_file","arguments":{"path":"demo.txt"}}' });
  const chunks = await result; const call = chunks.find(chunk => chunk.type === 'block-end').block;
  assert.equal(call.name, 'read_file'); assert.equal(chunks.at(-1).reason.kind, 'tool-calls');
  assert.equal(chunks.some(chunk => chunk.type === 'text-delta'), false);
  const next = collect(adapter.stream({ model: 'chatgpt-web', tools, messages: [
    { role: 'assistant', content: [call] }, { role: 'tool', toolCallId: call.id, content: [{ type: 'text', text: 'contents from demo.txt' }] },
  ] }));
  const { commands: [followup] } = await poll(); assert.ok(followup.prompt.includes('contents from demo.txt'));
  await request('/event', { id: followup.id, type: 'done', text: 'The file contains contents from demo.txt.' });
  assert.equal((await next).at(-1).reason.kind, 'stop');
});

test('cancellation removes the job and rejects late replies', async t => {
  const { bridge, poll, request } = await fixture(t); const controller = new AbortController();
  const result = collect(bridge.request('chatgpt-web', 'test', controller.signal));
  const rejected = assert.rejects(result, { name: 'AbortError' });
  const { commands: [job] } = await poll(); controller.abort(); await rejected;
  assert.equal(bridge.jobs.size, 0); assert.deepEqual((await poll()).activeIds, []);
  assert.equal((await request('/event', { id: job.id, type: 'snapshot', text: 'late' })).status, 410);
});

test('explicit website failure reaches the caller, without successful finish', async t => {
  const { bridge, request, poll } = await fixture(t);
  const result = collect(new BrowserAdapter(bridge, { introduction: false }).stream({ model: 'chatgpt-web', messages: [] }));
  const rejected = assert.rejects(result, /Please log in/);
  const { commands: [job] } = await poll();
  await request('/event', { id: job.id, type: 'error', message: 'Please log in on the website.' });
  await rejected;
});

test('disconnected extension and stalled website have bounded failure paths', async t => {
  const { bridge } = await fixture(t, { connectionGraceMs: 20, timeoutMs: 500 });
  await assert.rejects(collect(bridge.request('chatgpt-web', 'test')), /extension not connected/);
  const second = await fixture(t, { timeoutMs: 150 });
  const result = collect(second.bridge.request('chatgpt-web', 'test'));
  const rejected = assert.rejects(result, /timed out/); await second.poll(); await rejected;
});

test('one consumer per request, no duplicate dispatch and one active request per conversation', async t => {
  const { bridge, poll, request } = await fixture(t);
  const result = collect(bridge.request('chatgpt-web', 'test'));
  const { commands: [job] } = await poll(); assert.ok(job);
  assert.deepEqual((await poll()).commands, []);
  const queued=collect(bridge.request('chatgpt-web','other'));
  assert.equal(bridge.scheduler.queue.length,1);
  await request('/event', { id: job.id, type: 'done', text: 'done' }); await result;
  const next=await nextCommand(poll);assert.notEqual(next.id,job.id);
  await request('/event',{id:next.id,type:'done',text:'second'});await queued;
});

test('only enabled sites receive queued requests; unknown models fail', async t => {
  const { bridge, request, poll } = await fixture(t);
  const result = collect(bridge.request('gemini-web', 'test'));
  assert.deepEqual((await poll()).commands, []);
  const { commands: [job] } = await (await request('/poll', { sites: ['gemini-web'] })).json();
  assert.equal(job.site, 'gemini-web');
  await request('/event', { id: job.id, type: 'done', text: 'done' }); await result;
  await assert.rejects(collect(bridge.request('unknown', 'test')), /Unknown/);
});

test('catalog limits image input to the implemented ChatGPT route', async t => {
  const { bridge } = await fixture(t); const adapter = new BrowserAdapter(bridge, { introduction: false });
  const models = await adapter.listModels('browser-web'); assert.equal(models.length, 4);
  assert.deepEqual(models.find(model=>model.id==='chatgpt-web').inputModalities,['text','image']);
  assert.ok(models.filter(model=>model.id!=='chatgpt-web').every(model=>model.inputModalities.join()==='text'));
  assert.deepEqual(models.map(model=>model.name),['ChatGPT','DeepSeek','Gemini','Kimi']);
  await assert.rejects(adapter.resolveModel('browser-web', 'not-a-model'), /Unknown/);
});

test('incomplete tool reply gets one format correction before any native call is emitted', async t => {
  const { bridge, request, poll } = await fixture(t);
  const result = collect(new BrowserAdapter(bridge, { introduction: false }).stream({ model: 'chatgpt-web', tools: [{ name: 'write' }], messages: [] }));
  const { commands: [first] } = await poll();
  await request('/event', { id: first.id, type: 'done', text: 'HARNESS_TOOL_CALL' });
  const repair = await nextCommand(poll); assert.match(repair.prompt, /executed NOTHING/);
  assert.match(repair.prompt, /this turn failed\nIncomplete browser tool-request prefix\./);
  assert.match(repair.prompt, /another available tool or approach/);
  await request('/event', { id: repair.id, type: 'done', text: TOOL_PREFIX + '{"name":"write","arguments":{"path":"demo.txt"}}' });
  const chunks = await result;
  assert.equal(chunks.filter(chunk => chunk.type === 'tool-call-delta').length, 1);
  assert.equal(chunks.some(chunk => chunk.type === 'text-delta'), false);
});

test('prose before a tool request receives bounded feedback without a false final answer',async t=>{
 const {bridge,request,poll}=await fixture(t);
 const result=collect(new BrowserAdapter(bridge,{introduction:false}).stream({model:'chatgpt-web',tools:[{name:'navigate'}],messages:[]}));
 const job=await nextCommand(poll);
 await request('/event',{id:job.id,type:'done',text:'The command succeeded.\n'+TOOL_PREFIX+'```json\n{"name":"navigate","arguments":{}}\n```'});
 const repair=await nextCommand(poll);assert.match(repair.prompt,/Misplaced browser tool-request prefix/);
 await request('/event',{id:repair.id,type:'done',text:TOOL_PREFIX+'{"name":"navigate","arguments":{}}'});
 const chunks=await result;assert.equal(chunks.at(-1).reason.kind,'tool-calls');
 assert.equal(chunks.filter(c=>c.type==='block-end').length,1);assert.equal(chunks.some(c=>c.type==='text-delta'),false);
});

test('format correction is bounded and never retries an unknown tool', async t => {
  const { bridge, request, poll } = await fixture(t);
  const adapter = new BrowserAdapter(bridge, { introduction: false });
  const result = collect(adapter.stream({ model: 'chatgpt-web', tools: [{ name: 'write' }], messages: [] }));
  const rejected = assert.rejects(result, /Incomplete/);
  for (let i = 0; i < 2; i++) {
    const job = await nextCommand(poll); await request('/event', { id: job.id, type: 'done', text: 'HARNESS_TOOL_CALL' });
  }
  await rejected; assert.equal(bridge.jobs.size, 0);
  const unknown = collect(adapter.stream({ model: 'chatgpt-web', tools: [], messages: [] }));
  const unknownRejected = assert.rejects(unknown, /not offered/);
  const { commands: [job] } = await poll();
  await request('/event', { id: job.id, type: 'done', text: TOOL_PREFIX + '{"name":"unknown","arguments":{}}' });
  await unknownRejected; assert.deepEqual((await poll()).commands, []);
});
