import test from 'node:test';
import assert from 'node:assert/strict';
import {remoteDeclarations} from '../audit-harness-api.mjs';

test('installed API audit distinguishes streaming, unary and renamed remote declarations without executing code',()=>{
 const source=`throw new Error('MUST NOT EXECUTE');
 _list_decorators = [Remote({ mode: "stream" })];
 _kill_decorators = [Remote("stop")];
 super(ctx, "controller", { namespace: "job" });`;
 assert.deepEqual(remoteDeclarations(source),{namespaceCandidates:['job'],methods:[{method:'list',exportName:'list',mode:'stream'},{method:'kill',exportName:'stop',mode:'unary'}]});
 assert.deepEqual(remoteDeclarations('const ordinaryMethod = () => {};'),{namespaceCandidates:[],methods:[]});
});
