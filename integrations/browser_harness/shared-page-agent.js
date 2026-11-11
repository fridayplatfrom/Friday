// Injected only in the protected model page. No bridge token or cookies are exposed.
(() => {
 if(window!==window.top||globalThis.__fridaySharedDispatch)return;
 const handlers=[];
 const runtime={sendMessage:message=>globalThis.__fridaySharedMessage(message),onMessage:{addListener:listener=>handlers.push(listener)}};
 Object.defineProperty(globalThis,'chrome',{value:{runtime},configurable:true});
 globalThis.__fridaySharedDispatch=message=>new Promise((resolve,reject)=>{
  let pending=false,done=false;
  const respond=value=>{if(!done){done=true;resolve(value);}};
  for(const handler of handlers)try{if(handler(message,{},respond)===true)pending=true;}catch(error){reject(error);return;}
  if(!pending&&!done)resolve({ok:false,error:'Page agent not ready'});
 });
})();
