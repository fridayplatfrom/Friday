import {SITES} from './protocol.mjs';

const modelHosts=new Set(Object.values(SITES).map(site=>new URL(site.url).hostname));
export const isModelURL=value=>{try{return modelHosts.has(new URL(value).hostname);}catch{return false;}};

// Serialize role assignment before Playwright emits its context "page" event.
export function createOwnedPage(context,protectedPages,model=false){
 const operation=(protectedPages.creationQueue||Promise.resolve()).then(async()=>{
  protectedPages.creatingModel=model;
  try{const page=await context.newPage();if(model)protectedPages.add(page);return page;}finally{protectedPages.creatingModel=false;}
 });protectedPages.creationQueue=operation.catch(()=>{});return operation;
}

/** Operational tab ownership for the existing MCP tools; not an OS/RCE sandbox. */
export function protectedTaskContext(context,protectedPages){
 const wrappers=new WeakMap(),listeners=new WeakMap(),routes=new WeakMap(),scripts=[];
 const isProtected=page=>protectedPages.has(page)||isModelURL(page.url());
 const assertTask=page=>{if(isProtected(page))throw new Error('Protected Friday model tab: use task tabs for website automation.');};
 const wrap=value=>{
  if(value instanceof Promise)return value.then(wrap);
  if(Array.isArray(value))return value.map(wrap);
  if(!value||typeof value!=='object')return value;
  if(value===context)return proxy;
  if(wrappers.has(value))return wrappers.get(value);
  // Only wrap Playwright page/frame/locator handles, not protocol payloads.
  if(!(typeof value.context==='function'&&typeof value.goto==='function')&&!(typeof value.page==='function'))return value;
  if(typeof value.context==='function')assertTask(value);
  const result=new Proxy(value,{get(target,key){
   if(key==='context')return ()=>proxy;
   const member=Reflect.get(target,key,target);
   if(typeof member!=='function')return member;
   return (...args)=>{if(typeof target.context==='function')assertTask(target);return wrap(member.apply(target,args));};
  }});wrappers.set(value,result);return result;
 };
 const taskPages=()=>context.pages().filter(page=>!isProtected(page));
 const browser=context.browser();
 const safeBrowser=browser&&new Proxy(browser,{get(target,key){
  if(key==='contexts')return ()=>[proxy];
  if(['close','newContext','newPage','newBrowserCDPSession','startTracing','stopTracing'].includes(key))return ()=>{throw new Error('Friday owns the shared browser lifecycle. Task tools cannot replace or close it.');};
  const member=Reflect.get(target,key,target);return typeof member==='function'?member.bind(target):member;
 }});
 const proxy=new Proxy(context,{get(target,key){
  if(key==='pages')return ()=>taskPages().map(wrap);
  if(key==='browser')return ()=>safeBrowser;
  if(key==='newPage')return async()=>{const page=await createOwnedPage(context,protectedPages);for(const script of scripts)await page.addInitScript(script);return wrap(page);};
  if(key==='close')return async()=>{for(const page of taskPages())await page.close();};
  if(['storageState','setStorageState','cookies','addCookies','clearCookies','newCDPSession','exposeBinding','exposeFunction','setExtraHTTPHeaders','clearPermissions','grantPermissions','setGeolocation','setOffline','setHTTPCredentials','unrouteAll'].includes(key))return ()=>{throw new Error('Shared-profile operation is protected to preserve the Friday login. Use task-page tools.');};
  if(['request','tracing','serviceWorkers','backgroundPages'].includes(key))throw new Error('Shared-profile access is protected to preserve the Friday login.');
  if(key==='addInitScript')return async script=>{scripts.push(script);for(const page of taskPages())await page.addInitScript(script);};
  if(['on','once','addListener'].includes(key))return (event,listener)=>{
   const filtered=(...args)=>{if(event==='page'&&(protectedPages.creatingModel||isProtected(args[0])))return;listener(...args.map(wrap));};
   let entries=listeners.get(listener);if(!entries)listeners.set(listener,entries=new Map());entries.set(event,filtered);target[key](event,filtered);return proxy;
  };
  if(['off','removeListener'].includes(key))return(event,listener)=>{target[key](event,listeners.get(listener)?.get(event)||listener);return proxy;};
  if(key==='route')return async(pattern,handler,options)=>{
   const filtered=(route,request)=>{let page;try{page=request.frame().page();}catch{return route.fallback();}return protectedPages.has(page)?route.fallback():handler(route,request);};
   routes.set(handler,filtered);return target.route(pattern,filtered,options);
  };
  if(key==='unroute')return(pattern,handler)=>target.unroute(pattern,routes.get(handler)||handler);
  const member=Reflect.get(target,key,target);return typeof member==='function'?member.bind(target):member;
 }});
 return proxy;
}
