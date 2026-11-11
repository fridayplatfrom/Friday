import test from 'node:test';
import assert from 'node:assert/strict';
import {buildPrompt,buildContextTransfer,TASK_SCOPE_INSTRUCTION} from '../protocol.mjs';
import {prepareContext} from '../context.mjs';

test('active-task boundaries survive snapshots, deltas and multipart commit without removing history',()=>{
 const input={model:'gemini-web',system:'Preserve workspace constraints.',messages:[{role:'user',content:[{type:'text',text:'Older failed request'}]}]};
 const first=prepareContext(input);
 const next={...input,messages:[...input.messages,{role:'user',content:[{type:'text',text:'Only print the new marker'}]}]};
 const delta=prepareContext(next,first.checkpoint);
 assert.equal(delta.incremental,true);
 for(const prompt of [buildPrompt(next),delta.prompt,buildContextTransfer(next).prompt])assert.ok(prompt.includes(TASK_SCOPE_INSTRUCTION));
 assert.ok(buildPrompt(next).includes('Older failed request'));
 assert.ok(buildPrompt(next).includes('Preserve workspace constraints.'));
 assert.ok(delta.prompt.includes('Only print the new marker'));
 assert.match(TASK_SCOPE_INSTRUCTION,/dependent steps of the active task/);
 assert.match(TASK_SCOPE_INSTRUCTION,/explicitly continued goals/);
});
