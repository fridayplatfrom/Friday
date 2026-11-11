import test from 'node:test';
import assert from 'node:assert/strict';
import {FRIDAY_CONTEXT_WINDOW,FRIDAY_COMPACTION_POLICY,nativeCompactionPatch} from '../native-compaction.mjs';
import {BrowserAdapter} from '../index.mjs';

test('Friday native pressure and retention budgets fit Harness request/output headroom',async()=>{
 const model=await new BrowserAdapter({}).resolveModel('browser-web','chatgpt-web');
 assert.equal(model.context.contextWindow,FRIDAY_CONTEXT_WINDOW);
 const p=FRIDAY_COMPACTION_POLICY;
 const threshold=Math.floor(Math.min(FRIDAY_CONTEXT_WINDOW*p.thresholdRatio,FRIDAY_CONTEXT_WINDOW-model.defaultMaxTokens-p.headroomTokens));
 assert.equal(threshold,19660);assert.ok(p.retainTokens<threshold);assert.ok(p.maxTokens<FRIDAY_CONTEXT_WINDOW-p.headroomTokens);
 assert.throws(()=>new BrowserAdapter({},{contextWindow:100}),/contextWindow/);
});

test('native policy patch preserves every existing preset plugin and scopes the override to Friday',()=>{
 const dump="- id: unrelated\n  name: other\n- id: preset-standard\n  name: '@deepseek-ai/dsh-agent-preset'\n  config:\n    plugins:\n      - id: tools\n        name: all-original-tools\n      - id: compaction\n        name: cordis:group\n        config:\n          - id: compaction-basic\n            name: '@deepseek-ai/dsh-compaction-basic'\n          - id: prune\n            name: original-pruner\n- id: other-preset\n  name: untouched\n";
 const patch=nativeCompactionPatch(dump);assert.ok(patch.includes('name: all-original-tools'));assert.ok(patch.includes('name: original-pruner'));
 assert.ok(!patch.includes('id: unrelated'));assert.ok(!patch.includes('id: other-preset'));
 assert.match(patch,/auto: true/);assert.match(patch,/modelPolicies:\n\s+- provider: browser-web\n\s+model: chatgpt-web/);
 assert.equal((patch.match(/- id: compaction-basic/g)||[]).length,1);
 assert.equal((patch.match(/provider: browser-web/g)||[]).length,1);
 const spaced=nativeCompactionPatch(dump.replace("            name: '@deepseek-ai/dsh-compaction-basic'","\n            name: '@deepseek-ai/dsh-compaction-basic'"));
 assert.equal((spaced.match(/provider: browser-web/g)||[]).length,1);
 assert.throws(()=>nativeCompactionPatch(dump.replace("name: '@deepseek-ai/dsh-compaction-basic'\n","name: '@deepseek-ai/dsh-compaction-basic'\n            config:\n              auto: false\n")),/custom compaction config/);
 assert.throws(()=>nativeCompactionPatch('- id: other\n  name: untouched\n'),/No native/);
});
