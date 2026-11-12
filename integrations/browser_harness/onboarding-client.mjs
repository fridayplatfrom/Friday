export const setupCSS=`
.friday-setup{position:fixed;inset:0;z-index:2147483000;display:grid;grid-template-columns:minmax(340px,32%) minmax(0,1fr);gap:10px;padding:10px;background:var(--dsw-alias-bg-base,#202023);color:var(--dsw-alias-label-primary,#f5f3f8);font:14px/1.5 system-ui,sans-serif;box-sizing:border-box}
.friday-setup *{box-sizing:border-box}.friday-setup-left,.friday-setup-right{border-radius:16px;min-width:0;overflow:auto}
.friday-setup-left{display:flex;flex-direction:column;padding:clamp(24px,3vw,44px);background:linear-gradient(165deg,#55535b 0%,#62536f 60%,#9e6bd2 145%)}
.friday-setup-brand{display:block;width:128px;height:46px;object-fit:cover;margin-bottom:42px}.friday-setup-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:42px}.friday-setup-top .friday-setup-brand{margin:0}.friday-setup-top .friday-setup-secondary{margin:0;font-size:12px}.friday-model-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.friday-model-actions .friday-setup-secondary{margin:0;font-size:12px;padding:8px}.friday-setup h1{font-size:clamp(25px,2.5vw,34px);font-weight:600;line-height:1.15;letter-spacing:-1px;margin:10px 0 12px}.friday-setup p{margin:0 0 22px;color:#e0dbe8}.friday-setup small{color:#ded7e7;font-size:12px;line-height:1.6}.friday-setup-step{font-size:11px;text-transform:uppercase;letter-spacing:1.6px;color:#e2d5f7}
.friday-setup-options{display:grid;gap:8px;margin:8px 0 24px}.friday-setup button{font:inherit;cursor:pointer;border-radius:10px;transition:background .15s ease;min-height:44px}.friday-setup-choice{display:flex;align-items:center;gap:12px;text-align:left;padding:12px 14px;border:1px solid #ffffff20;background:#202023b8;color:#f5f3f8}.friday-setup-choice svg{height:22px;width:22px;flex:none}.friday-setup-choice span:nth-last-child(1){margin-left:auto;font-size:12px;color:#cfc5dd}.friday-setup-choice[aria-pressed=true]{border-color:#d2b8fa;background:#2d253b}.friday-setup button:focus-visible{outline:2px solid #eee0ff;outline-offset:3px}.friday-setup button:disabled{cursor:default;opacity:.55}
.friday-setup-primary{width:100%;padding:11px 16px;border:0;background:#c6aff0;color:#241b30;font-weight:600!important}.friday-setup-primary:hover:not(:disabled){background:#dcc7ff}.friday-setup-secondary{display:block;margin:8px auto 0;border:0;background:transparent;color:#eee7f5;padding:8px 14px}.friday-setup-status{padding:12px 14px;border-radius:10px;background:#202023a8;white-space:pre-wrap;margin:0 0 16px!important;font-size:13px}.friday-setup-footer{margin-top:auto;padding-top:24px}.friday-setup-right{position:relative;display:flex;align-items:center;justify-content:center;background:var(--dsw-alias-bg-layer-1,#101012);border:1px solid #ffffff0c}.friday-setup-placeholder{max-width:360px;padding:32px;text-align:center}.friday-setup-placeholder svg{width:38px;height:38px;margin-bottom:18px;color:#c6aff0}.friday-setup-placeholder h2{font-size:21px;font-weight:500;margin:0 0 10px}.friday-setup-placeholder p{font-size:13px;color:#aaa5b2}.friday-setup [hidden]{display:none!important}
@media(max-width:850px){.friday-setup{grid-template-columns:320px minmax(0,1fr)}.friday-setup-left{padding:24px}.friday-setup-brand{margin-bottom:24px}}@media(prefers-reduced-motion:reduce){.friday-setup button{transition:none}}
`;

/** One trusted local setup surface; provider pages retain their original native views. */
export async function mountSetup({desktop,marks,openAdvanced,document=globalThis.document,window=globalThis.window}){
 if(!desktop?.setup)return()=>{};
 let root,style,host,observer,timer,state,busy=false,disposed=false,previousFocus,signature='',localError='',background=[];
 const names=[['chatgpt-web','ChatGPT'],['gemini-web','Gemini'],['deepseek-web','DeepSeek'],['kimi-web','Kimi']];
 const el=(tag,text,cls)=>{const node=document.createElement(tag);if(text)node.textContent=text;if(cls)node.className=cls;return node;};
 const icon=site=>{const wrap=el('span');wrap.innerHTML='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'+marks[site]+'</svg>';return wrap;};
 function close(){observer?.disconnect();observer=null;clearInterval(timer);timer=null;root?.remove();style?.remove();root=null;style=null;signature='';for(const [node,inert]of background)node.inert=inert;background=[];previousFocus?.isConnected&&previousFocus.focus();}
 function report(){if(host&&state?.site&&root?.isConnected){const r=host.getBoundingClientRect();desktop.setupDock({x:r.x,y:r.y,width:r.width,height:r.height});}}
 async function act(action,site){if(busy)return;busy=true;localError='';try{state=await desktop.setup({action,site});signature='';render();}catch(error){localError=error.message;}finally{busy=false;render();}}
 function showError(message){const status=root?.querySelector('[role=status]');if(status)status.textContent=message;}
 function render(){
  if(disposed)return;if(!state?.visible){close();return;}
  const next=JSON.stringify(state)+busy+localError;if(root&&signature===next){report();return;}signature=next;
  const hadRoot=!!root;const focusId=document.activeElement?.dataset?.setupFocus;
  if(!root){previousFocus=document.activeElement;background=[...document.body.children].map(node=>[node,node.inert]);for(const [node]of background)node.inert=true;style=el('style');style.textContent=setupCSS;document.head.append(style);root=el('section',null,'friday-setup');root.setAttribute('aria-label','Friday first-time setup');document.body.append(root);}
  root.replaceChildren();const left=el('div',null,'friday-setup-left');host=el('div',null,'friday-setup-right');root.append(left,host);
  const managing=state.mode==='manage',disabled=!!state.providers?.[state.site]?.disabled;
  const logo=el('img',null,'friday-setup-brand');logo.src='/browser-models/brand/friday.png';logo.alt='Friday';
  if(managing){const top=el('div',null,'friday-setup-top');const back=el('button','← Back to Friday','friday-setup-secondary');back.type='button';back.dataset.setupFocus='back';back.disabled=busy||state.test?.status==='running';back.onclick=()=>void act('skip');top.append(logo,back);left.append(top);}else left.append(logo);
  const passed=state.test?.status==='passed'&&!disabled,running=state.test?.status==='running';
  left.append(el('div',managing?'Your assistants':passed?'Ready to go':state.site?'02 / Verify connection':'01 / Choose an assistant','friday-setup-step'));
  const heading=el('h1',managing?'Models.':passed?'Your assistant is ready.':'Connect your assistant.');heading.tabIndex=-1;left.append(heading);
  left.append(el('p',managing?'Connect, test and manage your assistants. Choose a provider to open its saved browser profile.':passed?'Your test message made the round trip. Add more assistants anytime from Models in the sidebar.':'Choose one to get started. Sign in on the right if the website asks you to.'));
  const choices=el('div',null,'friday-setup-options');choices.setAttribute('aria-label','Choose a provider');left.append(choices);
  for(const [site,name]of names){const record=state.providers?.[site],verified=(site===state.site?passed:record?.test?.status==='passed'&&!record?.disabled);const label=record?.disabled?'Disabled':verified?(state.defaultProvider===site?'Default · Tested':'Reply tested'):state.site===site?'Selected':'Connect';const b=el('button',null,'friday-setup-choice');b.type='button';b.dataset.setupFocus=site;b.setAttribute('aria-pressed',String(state.site===site));b.disabled=busy||running;b.append(icon(site),el('strong',name),el('span',label));b.onclick=()=>void act('select',site);choices.append(b);}
  const status=el('p',null,'friday-setup-status');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  status.textContent=localError||(disabled?'Connection disabled. Saved login and chats are kept. Test the connection to enable it again.':running?'Waiting for the test reply… Keep Friday open.':state.test?.message|| (state.site?'Finish sign-in or continue as a guest if offered. Then test the connection.':'No API key needed. You only need one assistant.'));if(passed&&state.test.finishedAt)status.textContent+='\nLast reply test: '+new Date(state.test.finishedAt).toLocaleString();left.append(status);
  const test=el('button',passed&&!managing?'Start using Friday':running?'Testing connection…':'Test connection','friday-setup-primary');test.type='button';test.dataset.setupFocus='primary';test.disabled=busy||running||!state.site;test.onclick=()=>void act(passed&&!managing?'finish':'test');left.append(test);
  left.append(el('small',passed&&!managing?'Start using Friday makes this assistant the default for new chats. Existing conversations keep their selected model.':'The test sends one short message. It does not run commands or change your files.'));
  if(managing){
   const actions=el('div',null,'friday-model-actions');left.append(actions);
   const makeDefault=el('button',state.defaultProvider===state.site?'Default for new chats':'Make default for new chats','friday-setup-secondary');makeDefault.type='button';makeDefault.disabled=busy||running||!passed||state.defaultProvider===state.site;makeDefault.onclick=()=>void act('default');actions.append(makeDefault);
   if(state.site){const disable=el('button','Disable connection','friday-setup-secondary');disable.type='button';disable.disabled=busy||running||disabled;disable.onclick=()=>void act('disable');actions.append(disable);}
   if(openAdvanced){const advanced=el('button','Advanced API model settings','friday-setup-secondary');advanced.type='button';advanced.disabled=busy||running;advanced.onclick=async()=>{await act('skip');if(!state.visible)openAdvanced();};left.append(advanced);}
  }
  if(!managing){const skip=el('button',passed?'Connect another later':'Set up later','friday-setup-secondary');skip.type='button';skip.disabled=busy||running;skip.dataset.setupFocus='skip';skip.onclick=()=>void act(passed?'finish':'skip');left.append(skip);}
  const footer=el('div',null,'friday-setup-footer');footer.append(el('small','Logins stay in Friday’s browser profile on this device. Providers may ask you to sign in again when a session expires.'));left.append(footer);
  const placeholder=el('div',null,'friday-setup-placeholder');if(state.site)placeholder.append(icon(state.site));placeholder.append(el('h2',state.site?names.find(([id])=>id===state.site)[1]:'Your assistant opens here'),el('p',state.site?'Use the provider’s own page to sign in. Saved logins are kept when you return to Friday.':'Your chat and task browser will use this same space.'));host.append(placeholder);
  observer?.disconnect();observer=new ResizeObserver(report);observer.observe(host);report();
  if(!timer)timer=setInterval(()=>void refresh(),1500);
  if(!hadRoot)heading.focus();else if(focusId){root.querySelectorAll('[data-setup-focus]').forEach(node=>{if(node.dataset.setupFocus===focusId&&!node.disabled)node.focus();});}
 }
 async function refresh(){if(disposed||busy)return;try{state=await desktop.setup({action:'status'});render();}catch(error){showError(error.message);}}
 const unlisten=desktop.onSetup?.(()=>void act('show'));
 const show=()=>void act('show');window.addEventListener('friday-show-setup',show);
 window.addEventListener('resize',report);
 await refresh();
 return()=>{disposed=true;unlisten?.();window.removeEventListener('resize',report);window.removeEventListener('friday-show-setup',show);close();};
}
