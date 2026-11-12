/** Fixed text-only test: never executes model-produced tools or replays a test ID. */
export const setupSession=(clientId,site)=>'friday-setup-'+clientId+'-'+site;
export function startSetupTest(bridge,input){
 if(!bridge.desktopOwner||input.clientId!==bridge.desktopOwner)throw Error('Friday Desktop ownership required.');
 if(!['chatgpt-web','gemini-web','deepseek-web','kimi-web'].includes(input.site)||! /^[a-f0-9-]{36}$/.test(input.id||''))throw Error('Invalid setup test.');
 bridge.setupTests??=new Map();
 if(bridge.setupTests.has(input.id))return bridge.setupTests.get(input.id);
 const sessionId='friday-setup-'+input.id;
 const saved=bridge.sessions.get(sessionId)?.setupConnectionTest;
 if(saved){const restored={...saved};if(restored.status==='running'){restored.status='interrupted';restored.message='The test was interrupted. Inspect the provider chat before starting a new test.';}bridge.setupTests.set(input.id,restored);return restored;}
 if(bridge.setupTests.size>=100)throw Error('Too many setup tests. Restart Friday before testing again.');
 if(bridge.schedulingStatus().pending)throw Error('Finish the active task before testing a connection.');
 const result={status:'running',ok:false,site:input.site};bridge.setupTests.set(input.id,result);
 bridge.sessions.update(sessionId,{setupConnectionTest:{...result}});
 void(async()=>{
  try{
   let reply='';
   for await(const event of bridge.request(input.site,'Friday connection test only. Reply with exactly FRIDAY_SETUP_READY. Do not use tools, browse, create files or continue earlier tasks.',AbortSignal.timeout(120000),{sessionId:setupSession(input.clientId,input.site),purpose:'context'})){
    if(event.type==='done'||event.type==='snapshot')reply=event.text;
   }
   result.ok=reply.trim()==='FRIDAY_SETUP_READY';result.status=result.ok?'passed':'failed';
   result.message=result.ok?'Message sent and reply received.':'The reply did not match the connection test. Inspect the provider chat before retrying.';
  }catch(error){result.status='failed';result.message=String(error.message).slice(0,400);}
  finally{bridge.sessions.update(sessionId,{setupConnectionTest:{...result}});}
 })();return result;
}
