import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { SessionStore, websiteURL } from '../session-store.mjs';
import {INTRODUCTION_VERSION} from '../protocol.mjs';

test('always-on two-way activates only after verified introduction and is disarmed for a different conversation',()=>{
 const store=new SessionStore(undefined,{autoTwoWay:true});
 store.bind({sessionId:'auto',site:'chatgpt-web',url:'https://chatgpt.com/c/one',tabId:10});assert.equal(store.get('auto').twoWay,undefined);
 store.acknowledgeIntroduction('auto','chatgpt-web',INTRODUCTION_VERSION);assert.equal(store.get('auto').twoWay,true);
 store.bind({sessionId:'auto',site:'chatgpt-web',url:'https://chatgpt.com/c/two',tabId:10});assert.equal(store.get('auto').twoWay,false);assert.equal(store.introductionReady('auto','chatgpt-web',INTRODUCTION_VERSION),false);
 store.acknowledgeIntroduction('auto','chatgpt-web',INTRODUCTION_VERSION);assert.equal(store.get('auto').twoWay,true);
});

test('chat URLs, progress and images survive backend restarts', t => {
  const directory = mkdtempSync(join(tmpdir(), 'harness-image-test-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const store = new SessionStore(directory);
  store.bind({ sessionId: 'one', site: 'chatgpt-web', tabId: 7, url: 'https://chatgpt.com/c/abc?secret=no#ignored' });
  store.update('one', { phase: 'generating', progress: [{ percent: 27 }] });
  const image = store.saveImage(Buffer.from('89504e470d0a1a0a', 'hex'), 'image/png');
  store.update('one', { images: [image] });
  const restarted = new SessionStore(directory);
  assert.equal(restarted.get('one').pairs['chatgpt-web'].url, 'https://chatgpt.com/c/abc');
  assert.equal(restarted.get('one').phase, 'interrupted');
  assert.equal(restarted.readImage(image.id).mime, 'image/png');
  assert.equal(restarted.readImage('../../connection.json'), null);
  assert.equal(websiteURL('chatgpt-web', 'https://evil.example/a'), null);
  assert.equal(websiteURL('chatgpt-web', 'https://user:pass@chatgpt.com/a'), null);
  assert.throws(() => store.saveImage(Buffer.from('<svg/>'), 'image/png'), /Invalid/);
});

test('introduction acknowledgement survives restarts and resets only for a different conversation', t => {
  const directory = mkdtempSync(join(tmpdir(), 'harness-intro-test-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const store = new SessionStore(directory);
  store.acknowledgeIntroduction('one', 'chatgpt-web', 1);
  store.bind({ sessionId: 'one', site: 'chatgpt-web', tabId: 1, url: 'https://chatgpt.com/c/first' });
  const restarted = new SessionStore(directory);
  assert.equal(restarted.introductionReady('one', 'chatgpt-web', 1), true);
  assert.equal(restarted.introductionReady('one', 'chatgpt-web', 2), false);
  restarted.bind({ sessionId: 'one', site: 'chatgpt-web', tabId: 2, url: 'https://chatgpt.com/c/first' });
  assert.equal(restarted.introductionReady('one', 'chatgpt-web', 1), true);
  restarted.bind({ sessionId: 'one', site: 'chatgpt-web', tabId: 2, url: 'https://chatgpt.com/c/second' });
  assert.equal(restarted.introductionReady('one', 'chatgpt-web', 1), false);
  restarted.acknowledgeIntroduction('one', 'chatgpt-web', 1);
  restarted.bind({ sessionId: 'one', site: 'chatgpt-web', tabId: 2, url: 'https://chatgpt.com/' });
  assert.equal(restarted.introductionReady('one', 'chatgpt-web', 1), false);
});
