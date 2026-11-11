import test from 'node:test';
import assert from 'node:assert/strict';
import { DemoFormServer } from '../demo-form.mjs';

test('local form records and displays only a valid submission, escaping HTML', async t => {
  const demo = await new DemoFormServer({ port: 0 }).start(); t.after(() => demo.close());
  const url = `http://127.0.0.1:${demo.port}`;
  assert.match(await (await fetch(url + '/form')).text(), /Local Harness automation test/);
  const invalid = await fetch(url + '/submit', { method: 'POST', body: 'name=test' }); assert.equal(invalid.status, 400);
  assert.equal(demo.submissions, 0);
  const fields = { name: '<b>Test</b>', email: 'test@example.invalid', topic: 'browser-automation', notes: 'Browser loop', testData: 'yes' };
  const response = await fetch(url + '/submit', { method: 'POST', body: new URLSearchParams(fields) });
  const page = await response.text(); assert.match(page, /Demo request saved/); assert.ok(page.includes('&lt;b&gt;Test&lt;/b&gt;'));
  assert.deepEqual(await (await fetch(url + '/result')).json(), { submissions: 1, result: fields });
});
