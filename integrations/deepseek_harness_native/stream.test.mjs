import test from 'node:test';
import assert from 'node:assert/strict';
import { readHarnessStream } from './stream.mjs';

function response(bytes, size = 1) {
  return new Response(new ReadableStream({
    start(controller) {
      for (let i = 0; i < bytes.length; i += size) controller.enqueue(bytes.slice(i, i + size));
      controller.close();
    },
  }));
}
const encode = text => new TextEncoder().encode(text);

test('preserves Unicode and split CRLF frames with no duplicated text', async () => {
  const events = [{ type: 'text-delta', index: 1, text: 'η = 50% — 0 J' },
    { type: 'finish', reason: { kind: 'stop' } }];
  const wire = ': keepalive\r\n\r\n' + events.map(e => `data: ${JSON.stringify(e)}\r\n\r\n`).join('');
  const decoded = [];
  for await (const event of readHarnessStream(response(encode(wire)))) decoded.push(event);
  assert.deepEqual(decoded, events);
});

test('rejects truncated streams, malformed frames, and backend failures', async () => {
  for (const wire of ['data: {"type":"text-delta","text":"partial"}\n\n',
    'data: nope\n\n', 'data: {"type":"error","message":"compute failed"}\n\n']) {
    await assert.rejects(async () => {
      for await (const event of readHarnessStream(response(encode(wire)))) {}
    });
  }
});

test('forwards the first event before the response body completes', async () => {
  let controller;
  const res = new Response(new ReadableStream({ start(c) { controller = c; } }));
  const stream = readHarnessStream(res);
  controller.enqueue(encode('data: {"type":"reasoning-delta","text":"Running"}\n\n'));
  assert.equal((await stream.next()).value.text, 'Running');
  controller.enqueue(encode('data: {"type":"finish","reason":{"kind":"stop"}}\n\n'));
  assert.equal((await stream.next()).value.type, 'finish');
  await stream.return();
});

test('honors cancellation', async () => {
  const abort = new AbortController(); abort.abort();
  await assert.rejects(async () => {
    for await (const event of readHarnessStream(response(encode('')), abort.signal)) {}
  }, { name: 'AbortError' });
});
