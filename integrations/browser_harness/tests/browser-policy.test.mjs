import test from 'node:test';
import assert from 'node:assert/strict';
import {taskOrigins,patchTaskBrowser,DEFAULT_TASK_ORIGINS} from '../browser-policy.mjs';

test('task origin policy allows intended local site/assets while refusing broad or credential-bearing values',()=>{
 assert.deepEqual(taskOrigins(['http://127.0.0.1:8010/','http://127.0.0.1:8010']),['http://127.0.0.1:8010']);
 for(const value of ['*','file:///C:/private','https://user:pass@example.test','https://*.example.test','https://example.test/path','https://example.test/?secret=x'])assert.throws(()=>taskOrigins([value]));
 assert.ok(DEFAULT_TASK_ORIGINS.includes('http://127.0.0.1:8010'));
});
test('browser policy patches only the existing native backend and preserves other plugins and custom origins',()=>{
 const profile="- insert:\n    - id: harness-playwright\n      name: native-browser\n      config:\n        args: ['--isolated', '--allowed-origins', 'http://127.0.0.1:8767;https://existing.test']\n    - id: untouched\n      config:\n        value: http://127.0.0.1:8767\n- id: preset\n  name: unchanged\n";
 const result=patchTaskBrowser(profile);
 assert.ok(result.profile.includes("['--isolated', '--allowed-origins'"));
 assert.ok(result.profile.endsWith(profile.slice(profile.indexOf('    - id: untouched'))));
 assert.ok(result.origins.includes('https://existing.test'));assert.ok(result.origins.includes('http://127.0.0.1:8010'));
 assert.equal(patchTaskBrowser(result.profile).profile,result.profile);
 assert.throws(()=>patchTaskBrowser('- id: other\n'),/No browser was added/);
 assert.throws(()=>patchTaskBrowser('- id: harness-playwright\n  args: []\n'),/custom config/);
 assert.throws(()=>patchTaskBrowser("- insert:\n    - id: harness-playwright\n      args: []\n- id: another\n  args: ['--allowed-origins', 'https://unrelated.test']\n"),/custom config/,'never borrow an origin option from another plugin');
});
