import test from 'node:test';import assert from 'node:assert/strict';
import {RecoveryBudget,recoveryTarget} from '../desktop/recovery.mjs';
import {localHarness,providerURL} from '../desktop/policy.mjs';
test('renderer recovery is bounded independently per view and resets after its time window',()=>{
 const budget=new RecoveryBudget();
 assert.equal(budget.admit('interface',1000),true);assert.equal(budget.admit('interface',2000),true);
 assert.equal(budget.admit('interface',3000),false);assert.equal(budget.admit('provider:1',3000),true);
 assert.equal(budget.admit('interface',62001),true);
});
test('crashed renderer restores only validated saved addresses, never remote local-file targets',()=>{
 assert.equal(recoveryTarget('','http://127.0.0.1:3030/',localHarness),'http://127.0.0.1:3030/');
 assert.equal(recoveryTarget('file:///private','https://evil.example',localHarness),null);
 const allowed=url=>!!providerURL(url,'chatgpt-web');
 assert.equal(recoveryTarget('','https://chatgpt.com/c/saved',allowed),'https://chatgpt.com/c/saved');
 assert.equal(recoveryTarget('https://chatgpt.com/c/current','https://chatgpt.com/c/saved',allowed),'https://chatgpt.com/c/current');
 assert.equal(recoveryTarget('https://evil.example','javascript:alert(1)',allowed),null);
});
