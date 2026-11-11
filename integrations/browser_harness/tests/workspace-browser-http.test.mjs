import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {workspaceControlServer} from '../workspace-browser-http.mjs';
const token='test-workspace-control-token-01234567890123456789';
async function fixture(t){
 const calls=[],state={summary:()=>({persistent:true,pending:[]}),review:(...args)=>calls.push(['review',...args]),acknowledge:(...args)=>calls.push(['acknowledge',...args])};
 const manager={running:false,lease:null,workspace(directory){calls.push(['workspace',directory]);return {state};},select(input){calls.push(['select',input]);return {ok:true};},release(id){calls.push(['release',id]);},async close(){calls.push(['close']);},async context(){calls.push(['open']);}};
 const server=workspaceControlServer(manager,token);await new Promise(r=>server.listen(0,'127.0.0.1',r));t.after(()=>{server.closeAllConnections();return new Promise(r=>server.close(r));});
 const url=`http://127.0.0.1:${server.address().port}`;
 const request=(route='/status',input={directory:'native-workspace'},headers={},method='POST')=>fetch(url+route,{method,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',...headers},...(method==='GET'?{}:{body:JSON.stringify(input)})});
 return {server,request,manager,calls,url};
}
test('private workspace control rejects foreign hosts, browser origins, invalid tokens and non-POST requests before accessing state',async t=>{
 const f=await fixture(t);
 const foreignHost=await new Promise((resolve,reject)=>{const req=http.request(f.url+'/status',{method:'POST',headers:{Host:'foreign.invalid',Authorization:'Bearer '+token,'Content-Type':'application/json'}},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});req.on('error',reject);req.end('{}');});assert.equal(foreignHost,403);
 for(const headers of [{Origin:'https://attacker.invalid'},{Origin:'chrome-extension://'+'a'.repeat(32)},{Authorization:'Bearer wrong'}])assert.equal((await f.request('/status',{},headers)).status,403,JSON.stringify(headers));
 assert.equal((await f.request('/status',{}, {},'GET')).status,403);assert.deepEqual(f.calls,[]);
 const response=await f.request();assert.equal(response.status,200);assert.equal(response.headers.get('access-control-allow-origin'),null);assert.equal(response.headers.get('cache-control'),'no-store');assert.equal(JSON.stringify(await response.json()).includes(token),false);
});
test('malformed, non-object, oversized and unknown requests cannot open a profile or review a receipt',async t=>{
 const f=await fixture(t);
 assert.equal((await f.request('/open',null)).status,409);assert.equal((await f.request('/review',[])).status,409);
 assert.equal((await f.request('/open',{}, {'Content-Type':'text/plain'})).status,415);
 assert.equal((await f.request('/open',{directory:'x'.repeat(17000)})).status,413);
 assert.equal((await fetch(f.url+'/open',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:'{bad'})).status,409);
 assert.equal((await f.request('/not-a-route')).status,404);assert.deepEqual(f.calls,[]);
});
test('chunked oversized requests receive a bounded rejection and never reach workspace dispatch',async t=>{
 const f=await fixture(t);
 const status=await new Promise((resolve,reject)=>{const req=http.request(f.url+'/open',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json','Transfer-Encoding':'chunked'}},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});req.on('error',reject);req.write('x'.repeat(10000));req.end('y'.repeat(10000));});
 assert.equal(status,413);assert.deepEqual(f.calls,[]);
});
test('active native dispatch blocks profile lifecycle and owner review while allowing result acknowledgement',async t=>{
 const f=await fixture(t);f.manager.running=true;
 for(const route of ['/open','/review','/checkpoint'])assert.equal((await f.request(route,{directory:'native-workspace'})).status,409);
 assert.ok(!f.calls.some(c=>['open','close','review'].includes(c[0])));
 assert.equal((await f.request('/acknowledge',{directory:'native-workspace',id:'native-call',sessionId:'session',success:false})).status,200);
 assert.ok(f.calls.some(c=>c[0]==='acknowledge'&&c[1]==='native-call'&&c[3]===false));
 f.manager.running=false;assert.equal((await f.request('/checkpoint',{})).status,200);assert.equal(f.calls.filter(c=>c[0]==='close').length,1);
});
