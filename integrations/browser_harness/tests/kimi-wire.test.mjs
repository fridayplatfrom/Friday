import test from 'node:test';
import assert from 'node:assert/strict';
import {browserWirePrompt} from '../protocol.mjs';
import {BrowserBridge} from '../bridge.mjs';
import {setTimeout as delay} from 'node:timers/promises';

test('Kimi single-line wire request retains exact multiline and escaped tool text',()=>{
 const source='Task\r\n\n```json\n{"command":"$value=1; Write-Output \\\"x\\\"","path":"C:\\\\folder"}\n```\n<literal>\tΩ';
 const wire=browserWirePrompt('kimi-web',source,'synthetic-id');
 assert.equal(/[\r\n]/.test(wire),false);assert.ok(wire.startsWith('FRIDAY_REQUEST_ID synthetic-id '));
 assert.equal(JSON.parse(wire.slice(wire.indexOf('{"requestText"'))).requestText,source);
 assert.ok(!/^(?:You are answering one request|Harness continuation:)/.test(wire));
});

test('other providers and website-origin empty requests remain byte-identical',()=>{
 const source='one\ntwo';for(const site of ['chatgpt-web','deepseek-web','gemini-web'])assert.equal(browserWirePrompt(site,source,'id'),source);
 assert.equal(browserWirePrompt('kimi-web','','id'),'');
});

test('wire expansion fails explicitly before oversize Kimi submission',()=>{
 assert.throws(()=>browserWirePrompt('kimi-web','\\'.repeat(50000),'id'),error=>error.code==='FRIDAY_CONTEXT_LIMIT'&&/no prompt was submitted/.test(error.message));
});

test('real Kimi bridge transports context as one line while retaining native request purpose and exact data',async t=>{
 const token='synthetic-kimi-wire-token-long-enough';const bridge=await new BrowserBridge({token,port:0,timeoutMs:3000,connectionGraceMs:1000}).start();t.after(()=>bridge.close());
 const post=async(path,body)=>(await fetch(`http://127.0.0.1:${bridge.port}${path}`,{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
 const original='Context part\n{"literal":"$value\\nsecond"}';
 const received=(async()=>{const events=[];for await(const event of bridge.request('kimi-web',original,undefined,{sessionId:'wire-test',purpose:'context'}))events.push(event);return events;})();
 let command;for(let i=0;i<50&&!command;i++){command=(await post('/poll',{sites:['kimi-web']})).commands[0];if(!command)await delay(10);}
 assert.ok(command);assert.equal(command.purpose,'task');assert.equal(bridge.jobs.get(command.id).purpose,'context');assert.equal(/[\r\n]/.test(command.prompt),false);
 assert.equal(JSON.parse(command.prompt.slice(command.prompt.indexOf('{"requestText"'))).requestText,original);
 await post('/event',{id:command.id,type:'done',text:'ACK'});assert.equal((await received).at(-1).text,'ACK');
});
