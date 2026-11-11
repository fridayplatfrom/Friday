import test from 'node:test';
import assert from 'node:assert/strict';
import {sessionRecovery} from '../session-recovery.mjs';

test('native recovery deduplicates cold activation without submitting prompts or changing selection',async()=>{
 let inspections=0,resolves=0,release;
 const barrier=new Promise(r=>release=r);
 const agent={id:'saved',status:'idle',followup(){throw new Error('Recovery must never submit work');}};
 const bridge={sessions:{get:id=>id==='saved'?{pairs:{}}:null}};
 const recover=sessionRecovery(bridge,{
  async inspect(){inspections++;await barrier;return {meta:{cwd:'C:/workspace'},events:[{type:'request/header',data:{header:{config:{provider:'browser-web',model:'kimi-web'}}}},{type:'model/selection',data:{provider:'browser-web',model:'gemini-web'}}]};},
  async resolveAgent(id){assert.equal(id,'saved');resolves++;return {agent};},
 });
 const first=recover('saved'),second=recover('saved');assert.equal(first,second);release();
 assert.deepEqual(await first,{ok:true,sessionId:'saved',loaded:true,status:'idle',provider:'browser-web',model:'gemini-web',replayed:false});
 assert.equal(inspections,1);assert.equal(resolves,1);
 await assert.rejects(recover('unknown'),/Unknown saved/);assert.equal(resolves,1);
});

test('native recovery refuses other providers, child sessions and writer failures without fallback creation',async()=>{
 let inspections=0,resolves=0;
 let inspection={meta:{origin:'subagent'},events:[]};
 const recover=sessionRecovery({sessions:{get:()=>({})}},{async inspect(){inspections++;return inspection;},async resolveAgent(){resolves++;return {error:new Error('writer held')};}});
 await assert.rejects(recover('saved'),/Subagent/);
 inspection={meta:{},events:[{type:'model/selection',data:{provider:'another',model:'api'}}]};
 await assert.rejects(recover('saved'),/not using a Friday/);assert.equal(resolves,0);
 inspection.events[0].data.provider='browser-web';
 await assert.rejects(recover('saved'),/writer held/);await assert.rejects(recover('saved'),/writer held/);
 assert.equal(resolves,2);assert.equal(inspections,4);
});
