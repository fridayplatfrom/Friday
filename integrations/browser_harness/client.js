window.__ModuleLoader__.load({
  id: 'harness-browser-provider',
  factory: require => {
    const React = require('react');
    const { Button } = require('@deepseek-ai/dsh-client-ui-primitives');
    const h = React.createElement;
    const providers = [['chatgpt-web', 'ChatGPT'], ['deepseek-web','DeepSeek'], ['gemini-web', 'Gemini'], ['kimi-web', 'Kimi']];
    // Vendored Lobe Icons 1.97.0 (MIT); see assets/provider-icons-LICENSE.txt.
    const providerMarks = {
  "chatgpt-web": "<title>OpenAI</title><path d=\"M9.205 8.658v-2.26c0-.19.072-.333.238-.428l4.543-2.616c.619-.357 1.356-.523 2.117-.523 2.854 0 4.662 2.212 4.662 4.566 0 .167 0 .357-.024.547l-4.71-2.759a.797.797 0 00-.856 0l-5.97 3.473zm10.609 8.8V12.06c0-.333-.143-.57-.429-.737l-5.97-3.473 1.95-1.118a.433.433 0 01.476 0l4.543 2.617c1.309.76 2.189 2.378 2.189 3.948 0 1.808-1.07 3.473-2.76 4.163zM7.802 12.703l-1.95-1.142c-.167-.095-.239-.238-.239-.428V5.899c0-2.545 1.95-4.472 4.591-4.472 1 0 1.927.333 2.712.928L8.23 5.067c-.285.166-.428.404-.428.737v6.898zM12 15.128l-2.795-1.57v-3.33L12 8.658l2.795 1.57v3.33L12 15.128zm1.796 7.23c-1 0-1.927-.332-2.712-.927l4.686-2.712c.285-.166.428-.404.428-.737v-6.898l1.974 1.142c.167.095.238.238.238.428v5.233c0 2.545-1.974 4.472-4.614 4.472zm-5.637-5.303l-4.544-2.617c-1.308-.761-2.188-2.378-2.188-3.948A4.482 4.482 0 014.21 6.327v5.423c0 .333.143.571.428.738l5.947 3.449-1.95 1.118a.432.432 0 01-.476 0zm-.262 3.9c-2.688 0-4.662-2.021-4.662-4.519 0-.19.024-.38.047-.57l4.686 2.71c.286.167.571.167.856 0l5.97-3.448v2.26c0 .19-.07.333-.237.428l-4.543 2.616c-.619.357-1.356.523-2.117.523zm5.899 2.83a5.947 5.947 0 005.827-4.756C22.287 18.339 24 15.84 24 13.296c0-1.665-.713-3.282-1.998-4.448.119-.5.19-.999.19-1.498 0-3.401-2.759-5.947-5.946-5.947-.642 0-1.26.095-1.88.31A5.962 5.962 0 0010.205 0a5.947 5.947 0 00-5.827 4.757C1.713 5.447 0 7.945 0 10.49c0 1.666.713 3.283 1.998 4.448-.119.5-.19 1-.19 1.499 0 3.401 2.759 5.946 5.946 5.946.642 0 1.26-.095 1.88-.309a5.96 5.96 0 004.162 1.713z\"></path>",
  "deepseek-web": "<title>DeepSeek</title><path d=\"M23.748 4.482c-.254-.124-.364.113-.512.234-.051.039-.094.09-.137.136-.372.397-.806.657-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-.156-.708-.311-.955-.65-.172-.241-.219-.51-.305-.774-.055-.16-.11-.323-.293-.35-.2-.031-.278.136-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.393.137.093.172.187.129.323-.082.28-.18.552-.266.833-.055.179-.137.217-.329.14a5.526 5.526 0 01-1.736-1.18c-.857-.828-1.631-1.742-2.597-2.458a11.365 11.365 0 00-.689-.471c-.985-.957.13-1.743.388-1.836.27-.098.093-.432-.779-.428-.872.004-1.67.295-2.687.684a3.055 3.055 0 01-.465.137 9.597 9.597 0 00-2.883-.102c-1.885.21-3.39 1.102-4.497 2.623C.082 8.606-.231 10.684.152 12.85c.403 2.284 1.569 4.175 3.36 5.653 1.858 1.533 3.997 2.284 6.438 2.14 1.482-.085 3.133-.284 4.994-1.86.47.234.962.327 1.78.397.63.059 1.236-.03 1.705-.128.735-.156.684-.837.419-.961-2.155-1.004-1.682-.595-2.113-.926 1.096-1.296 2.746-2.642 3.392-7.003.05-.347.007-.565 0-.845-.004-.17.035-.237.23-.256a4.173 4.173 0 001.545-.475c1.396-.763 1.96-2.015 2.093-3.517.02-.23-.004-.467-.247-.588zM11.581 18c-2.089-1.642-3.102-2.183-3.52-2.16-.392.024-.321.471-.235.763.09.288.207.486.371.739.114.167.192.416-.113.603-.673.416-1.842-.14-1.897-.167-1.361-.802-2.5-1.86-3.301-3.307-.774-1.393-1.224-2.887-1.298-4.482-.02-.386.093-.522.477-.592a4.696 4.696 0 011.529-.039c2.132.312 3.946 1.265 5.468 2.774.868.86 1.525 1.887 2.202 2.891.72 1.066 1.494 2.082 2.48 2.914.348.292.625.514.891.677-.802.09-2.14.11-3.054-.614zm1-6.44a.306.306 0 01.415-.287.302.302 0 01.2.288.306.306 0 01-.31.307.303.303 0 01-.304-.308zm3.11 1.596c-.2.081-.399.151-.59.16a1.245 1.245 0 01-.798-.254c-.274-.23-.47-.358-.552-.758a1.73 1.73 0 01.016-.588c.07-.327-.008-.537-.239-.727-.187-.156-.426-.199-.688-.199a.559.559 0 01-.254-.078c-.11-.054-.2-.19-.114-.358.028-.054.16-.186.192-.21.356-.202.767-.136 1.146.016.352.144.618.408 1.001.782.391.451.462.576.685.914.176.265.336.537.445.848.067.195-.019.354-.25.452z\" fill=\"#4D6BFE\"></path>",
  "gemini-web": "<title>Gemini</title><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"#3186FF\"></path><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"url(#lobe-icons-gemini-0-_R_0_)\"></path><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"url(#lobe-icons-gemini-1-_R_0_)\"></path><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"url(#lobe-icons-gemini-2-_R_0_)\"></path><defs><linearGradient gradientUnits=\"userSpaceOnUse\" id=\"lobe-icons-gemini-0-_R_0_\" x1=\"7\" x2=\"11\" y1=\"15.5\" y2=\"12\"><stop stop-color=\"#08B962\"></stop><stop offset=\"1\" stop-color=\"#08B962\" stop-opacity=\"0\"></stop></linearGradient><linearGradient gradientUnits=\"userSpaceOnUse\" id=\"lobe-icons-gemini-1-_R_0_\" x1=\"8\" x2=\"11.5\" y1=\"5.5\" y2=\"11\"><stop stop-color=\"#F94543\"></stop><stop offset=\"1\" stop-color=\"#F94543\" stop-opacity=\"0\"></stop></linearGradient><linearGradient gradientUnits=\"userSpaceOnUse\" id=\"lobe-icons-gemini-2-_R_0_\" x1=\"3.5\" x2=\"17.5\" y1=\"13.5\" y2=\"12\"><stop stop-color=\"#FABC12\"></stop><stop offset=\".46\" stop-color=\"#FABC12\" stop-opacity=\"0\"></stop></linearGradient></defs>",
  "kimi-web": "<title>Kimi</title><path d=\"M21.846 0a1.923 1.923 0 110 3.846H20.15a.226.226 0 01-.227-.226V1.923C19.923.861 20.784 0 21.846 0z\" fill=\"#1783FF\"></path><path d=\"M11.065 11.199l7.257-7.2c.137-.136.06-.41-.116-.41H14.3a.164.164 0 00-.117.051l-7.82 7.756c-.122.12-.302.013-.302-.179V3.82c0-.127-.083-.23-.185-.23H3.186c-.103 0-.186.103-.186.23V19.77c0 .128.083.23.186.23h2.69c.103 0 .186-.102.186-.23v-3.25c0-.069.025-.135.069-.178l2.424-2.406a.158.158 0 01.205-.023l6.484 4.772a7.677 7.677 0 003.453 1.283c.108.012.2-.095.2-.23v-3.06c0-.117-.07-.212-.164-.227a5.028 5.028 0 01-2.027-.807l-5.613-4.064c-.117-.078-.132-.279-.028-.381z\" fill=\"currentColor\"></path>"
};
    function Icon({ site }) {
      return h('svg', { className:'hbm-provider-icon', width:20, height:20, viewBox:'0 0 24 24', fill:'currentColor', 'aria-hidden':true, dangerouslySetInnerHTML:{__html:providerMarks[site]||providerMarks['chatgpt-web']} });
    }
    const providerKind=site=>'friday-provider-'+site;
    let nativeDock;
    let openAdvancedModels;
    let selectModelsPage;
    function ModelsSettingsBridge({openSettings,wide}){
      React.useEffect(()=>{openAdvancedModels=()=>{openSettings('models');document.dispatchEvent(new Event('friday-open-api-models'));};return()=>{openAdvancedModels=null;};},[openSettings]);
      return h(Button,{className:'hbm-models-launcher hbm-settings-launcher',title:'Settings','aria-label':'Settings',onClick:()=>openSettings()},
        h('svg',{width:20,height:20,viewBox:'0 0 24 24',fill:'none',stroke:'currentColor',strokeWidth:1.6,'aria-hidden':true},h('path',{d:'m9.5 3-.7 2.1-2 .9-2.1-.4-2.2 3.8 1.4 1.7v2.2l-1.4 1.7 2.2 3.8 2.1-.4 2 .9.7 2.1h4.4l.7-2.1 2-.9 2.1.4 2.2-3.8-1.4-1.7v-2.2l1.4-1.7-2.2-3.8-2.1.4-2-.9-.7-2.1z'}),h('circle',{cx:11.7,cy:12.1,r:3})),wide?h('span',null,'Settings'):null);
    }
    function ModelsLauncher({wide}){
      return h(Button,{className:'hbm-models-launcher',title:'Models','aria-label':'Models',onClick:()=>window.fridayDesktopWorkspace?.setup?window.dispatchEvent(new Event('friday-show-setup')):selectModelsPage?.('friday-models')},
        h('svg',{width:20,height:20,viewBox:'0 0 24 24',fill:'none',stroke:'currentColor',strokeWidth:1.6,'aria-hidden':true},
          h('rect',{x:5,y:5,width:14,height:14,rx:4}),h('path',{d:'M9 1v4m6-4v4M9 19v4m6-4v4M1 9h4m-4 6h4m14-6h4m-4 6h4'}),h('path',{d:'M9 9h6v6H9z'})),wide?h('span',null,'Models'):null);
    }
    function openProvider(site,sessionId){
      if(!nativeDock||!sessionId)return;
      window.fridayDesktopWorkspace?.revealProvider?.(site,sessionId);
      const existing=nativeDock.openTabs.getSnapshot().find(tab=>tab.sessionId===sessionId&&tab.kind===providerKind(site));
      if(existing)nativeDock.focus(existing.tabId);else nativeDock.openTab(providerKind(site));
    }
    function ProviderTitle({site,sessionId}){return h('span',{className:'hbm-protected-provider',title:'Protected provider tab · login saved locally',onClick:()=>window.fridayDesktopWorkspace?.revealProvider?.(site,sessionId)},h(Icon,{site}),providers.find(([id])=>id===site)?.[1]);}
    function ProviderBody({site,sessionId,useTabInfo}){
      const {tab}=useTabInfo();const host=React.useRef(null);
      React.useLayoutEffect(()=>{
        const desktop=window.fridayDesktopWorkspace;if(!desktop)return;
        let last='';const report=()=>{
          const element=host.current;if(!element)return;
          const r=element.getBoundingClientRect();
          const visible=tab.visible&&r.width>1&&r.height>1&&!document.querySelector('[role="dialog"],[role="menu"],[data-friday-popup="true"]');
          const input={site,sessionId,tabId:tab.id,visible:!!visible,x:r.x,y:r.y,width:r.width,height:r.height};
          const signature=JSON.stringify(input);if(last!==signature){last=signature;desktop.dock(input);}
        };
        const observer=new ResizeObserver(report);observer.observe(host.current);report();
        const timer=setInterval(report,150);window.addEventListener('resize',report);
        return()=>{observer.disconnect();clearInterval(timer);window.removeEventListener('resize',report);desktop.dock({site,sessionId,tabId:tab.id,visible:false});};
      },[site,sessionId,tab.id,tab.visible]);
      return h('div',{ref:host,className:'hbm-provider-host'},window.fridayDesktopWorkspace?h('div',{style:{padding:'28px',color:'var(--dsw-alias-label-secondary)'}},h('p',null,'The provider runs in the background.'),h(Button,{onClick:()=>window.fridayDesktopWorkspace.revealProvider(site,sessionId)},'Show '+(providers.find(([id])=>id===site)?.[1]||'provider'))):h('p',null,'Open Friday Desktop to use this protected provider tab.'));
    }
    function ProviderShortcuts({sessionId}){
      React.useEffect(()=>window.fridayDesktopWorkspace?.onFocus(input=>{if(input.sessionId===sessionId)openProvider(input.site,sessionId);}),[sessionId]);
      return h('div',{className:'hbm-provider-shortcuts','aria-label':'Model websites'},...providers.map(([site,name])=>h('button',{key:site,type:'button',title:name,'aria-label':'Open '+name,onClick:()=>openProvider(site,sessionId)},h(Icon,{site}))));
    }
    function FridayHeader(props){
      const [open,setOpen]=React.useState(false);
      React.useEffect(()=>{setOpen(false);},[props.sessionId]);
      React.useEffect(()=>window.fridayDesktopWorkspace?.onFocus(input=>{if(input.sessionId===props.sessionId)openProvider(input.site,props.sessionId);}),[props.sessionId]);
      return h('div',{className:'hbm-header-tools'},
        h('details',{'data-friday-popup':open?'true':undefined,onToggle:event=>setOpen(event.currentTarget.open)},
          h('summary',{title:'Connection and task activity','aria-label':'Connection and task activity'},'ⓘ'),
          h('div',{className:'hbm-header-activity'},h(SessionWebsite,props))));
    }
    function FridayModelLabel({provider,model}){
      if(provider.id!=='browser-web')return model.name;
      const name=providers.find(([id])=>id===model.id)?.[1]||model.name;
      return h('span',{className:'hbm-model-label'},h(Icon,{site:model.id}),h('span',null,name));
    }
    function FridayLogo(){return h('img',{className:'hbm-friday-logo',src:'/browser-models/brand/friday.png',alt:'Friday',width:320,height:100});}
    function FridayMark({size=24}){return h('span',{className:'hbm-friday-mark',role:'img','aria-label':'Friday',style:{width:size,height:size}},'F');}
    function FridayWordmark(){return h('img',{className:'hbm-friday-wordmark',src:'/browser-models/brand/friday.png',alt:'Friday',width:110,height:38});}
    // BEGIN GENERATED LAYOUT PREFERENCES
const KEY='friday.layout.v1';
const valid=value=>Number.isFinite(value)&&value>=300&&value<=20000;
/** Keep the native root store and divider authoritative; persist only its width preference. */
function installLayoutPreferences({store,storage,events,delay=150,setTimer=setTimeout,clearTimer=clearTimeout}){
  if(!store?.getSnapshot||!store?.subscribe||!store?.actions?.setRightbar)return()=>{};
  const info=()=>store.getSnapshot().layoutInfo;
  if(!info()||!Number.isFinite(info().viewportWidth)||info().viewportWidth<=0)return()=>{};
  let saved;try{const data=JSON.parse(storage?.getItem(KEY)||'null');if(data?.version===1&&valid(data.rightbar))saved=data.rightbar;}catch{}
  // Set a preference only; native layout still decides visibility, clamping and fullscreen.
  const initial=saved??Math.round((info().viewportWidth-56)*.68);
  store.actions.setRightbar(initial);
  let previous=info().rightbar,pending=null,timer=null,disposed=false;
  const flush=()=>{if(timer!==null)clearTimer(timer);timer=null;if(pending===null)return;
    try{storage?.setItem(KEY,JSON.stringify({version:1,rightbar:pending}));}catch{}pending=null;};
  const unsubscribe=store.subscribe(()=>{
    const width=info()?.rightbar;if(width===previous)return;previous=width;
    if(!valid(width))return;pending=width;
    if(timer!==null)clearTimer(timer);timer=setTimer(flush,delay);
  });
  const release=()=>{queueMicrotask(()=>{if(!disposed)flush();});};
  events?.addEventListener('pointerup',release);events?.addEventListener('pointercancel',release);
  events?.addEventListener('pagehide',flush);events?.addEventListener('beforeunload',flush);
  return()=>{disposed=true;unsubscribe();flush();events?.removeEventListener('pointerup',release);events?.removeEventListener('pointercancel',release);events?.removeEventListener('pagehide',flush);events?.removeEventListener('beforeunload',flush);};
}

/** Adapt the existing layout action and rendered divider; never replace native actions. */
function nativeLayoutStore({layout,document,events}){
  if(typeof layout?.panels?.setRightbar!=='function')return null;
  let rightbar=null;
  const viewport=()=>document.querySelector('.mP3x-q_frame')?.getBoundingClientRect().width||events.innerWidth;
  return {
    getSnapshot:()=>({layoutInfo:{viewportWidth:viewport(),rightbar}}),
    actions:{setRightbar:px=>{layout.panels.setRightbar(px);rightbar=Math.min(Math.max(300,viewport()*.7),Math.max(300,Math.round(px)));}},
    subscribe(listener){
      let dragging=false,disposed=false;
      const start=event=>{dragging=!!event.target?.closest?.('.mP3x-q_handle[data-side="rightbar"]');};
      const finish=()=>{if(!dragging)return;dragging=false;queueMicrotask(()=>{
        if(disposed)return;
        const frame=document.querySelector('.mP3x-q_frame');
        if(!frame||frame.hasAttribute('data-rightbar-fullscreen'))return;
        const width=document.querySelector('.mP3x-q_rightbarCol')?.getBoundingClientRect().width;
        if(valid(width)){rightbar=width;listener();}
      });};
      events.addEventListener('pointerdown',start);events.addEventListener('pointerup',finish);events.addEventListener('pointercancel',finish);
      return()=>{disposed=true;events.removeEventListener('pointerdown',start);events.removeEventListener('pointerup',finish);events.removeEventListener('pointercancel',finish);};
    }
  };
}

    // END GENERATED LAYOUT PREFERENCES
    async function api(action, body) {
      const response = await fetch(`/browser-models/${action}`, { credentials: 'same-origin',
        method: body === undefined ? 'GET' : 'POST', headers: { 'X-Harness-Models': '1', 'Content-Type': 'application/json' },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Connection unavailable.'); return data;
    }
    function NativeInteractionRecord({node,item}){
      const data=item||node?.data;if(!data)return null;
      const labels={'requested':'Requested — use the native controls below','allowed-once':'Allowed once','rejected':'Rejected','cancelled':'Cancelled','unavailable':'Approval unavailable','answered':'Answered','continued':'Work continued — answer through the native question card','interrupted':'Interrupted — review the native task before continuing','error':'Question failed','closed':'Question closed'};
      return h('section',{className:'hbm-interaction', 'aria-label':data.kind==='approval'?'Friday approval record':'Friday question record'},
        h('strong',null,data.kind==='approval'?`Approval · ${data.toolName||'Harness tool'}`:'Question for you'),
        h('p',{role:'status'},labels[data.status]||'Review the native transcript'),
        data.reason?h('p',null,data.reason):null,
        ...(data.questions||[]).map(q=>h('div',{key:q.id},h('p',null,q.question),q.detail?h('p',null,q.detail):null,h('ul',null,...(q.options||[]).map(o=>h('li',{key:o.label},o.label,o.description?` — ${o.description}`:''))))),
        data.answers?.length?h('p',null,'Answer: '+data.answers.map(a=>[...(a.selected||[]),a.custom||''].filter(Boolean).join(', ')).join('; ')):null,
        data.message?h('p',null,data.message):null);
    }
    function WorkspaceBrowser({sessionId}){
      const [state,setState]=React.useState(null),[error,setError]=React.useState(''),[working,setWorking]=React.useState(false);
      const run=async(action,extra={})=>{setWorking(true);try{setState(await api('workspace-browser/'+action,{sessionId,...extra}));setError('');}catch(e){setError(e.message);}finally{setWorking(false);}};
      React.useEffect(()=>{setState(null);setError('');},[sessionId]);
      return h('details',{className:'hbm-workspace-browser',onToggle:event=>{if(event.currentTarget.open&&!state&&!working)void run('status');}},
        h('summary',null,'Workspace browser · saved login and tabs'),
        h(Button,{disabled:working,onClick:()=>void run('open')},'Open workspace browser'),
        h(Button,{disabled:working,onClick:()=>void run('status')},'Refresh browser status'),
        state?h('p',null,`${state.tabs.length} saved tabs · ${state.pending.length} actions need review`):null,
        ...(state?.pending||[]).map(action=>h('section',{key:action.id},h('p',{role:'alert'},`${action.tool}: interrupted. It may already have applied. Check the website before continuing.`),
          h(Button,{disabled:working,onClick:()=>{if(window.confirm('Have you checked the actual website and confirmed this action already happened? Friday will record your decision, without repeating it.'))void run('review',{id:action.id,decision:'confirmed-applied',revision:state.revision});}},'I checked: action happened'),
          h(Button,{disabled:working,onClick:()=>{if(window.confirm('Have you checked the actual website and confirmed this action did not happen? Friday will record your decision, without repeating it.'))void run('review',{id:action.id,decision:'confirmed-not-applied',revision:state.revision});}},'I checked: action did not happen'))),
        error?h('p',{role:'status'},error):null,
        h('p',null,'Logins stay in this workspace’s local Chrome profile. Website sessions can expire. Restart recovery opens saved pages without replaying forms or posts.'));
    }
    function SessionWebsite({ sessionId }) {
      React.useEffect(()=>{window.fridayDesktopWorkspace?.selectSession(sessionId);},[sessionId]);
      const [state, setState] = React.useState(null);
      const [activity, setActivity] = React.useState(null);
      const [error, setError] = React.useState('');
      const [streamError,setStreamError]=React.useState('');
      React.useEffect(() => {
        setState(null); setActivity(null); setError('');setStreamError(''); if (!sessionId) return;
        let disposed = false; let pending = false; let cursor=0;let observer=null;let observedRun=null;let recoveryAt=-Infinity;
        const refresh = async () => {
          if (pending) return; pending = true;
          try {
            const next=await api(`session/${encodeURIComponent(sessionId)}`);if(disposed)return;setState(next);
            if(next.sessionId&&!next.nativeSession?.loaded&&Date.now()-recoveryAt>30000){
              recoveryAt=Date.now();
              await api('recover-session',{sessionId});if(disposed)return;
            }
            const run=next.aguiRuns?.at(-1);
            if(run){
              if(run.runId!==observedRun){
                const module=await import('/browser-models/ag-ui-client.mjs');if(disposed)return;
                observer?.stop();observedRun=run.runId;
                observer=module.observeRun({threadId:sessionId,runId:run.runId,onActivity:value=>{if(!disposed)setActivity(value);},onStatus:value=>{if(!disposed)setStreamError(value);}});
              }
            }else{
              const events=await api(`activity/${encodeURIComponent(sessionId)}?after=${cursor}`);
              if(!disposed&&!events.unchanged){setActivity(previous=>({...events,events:events.reset?events.events:[...(previous?.events||[]),...events.events].slice(-180)}));cursor=events.revision;}
            }
            setError('');
          }
          catch (e) { if (!disposed) setError(e.message); } finally { pending = false; }
        };
        void refresh(); const timer = setInterval(refresh, 800);
        return () => { disposed = true; clearInterval(timer); observer?.stop(); };
      }, [sessionId]);
      if (!state) return error?h('p',{className:'hbm-session',role:'status'},'Friday offline — waiting to reconnect. Saved activity will return when Harness is available.'):null;
      const busy = ['queued','waiting', 'generating','receiving','uploading','reconnecting','executing'].includes(state.phase);
      return h('section', { className: 'hbm-session', 'aria-label': 'Friday task activity' },
        h(WorkspaceBrowser,{sessionId,key:sessionId}),
        state.pairs?.[state.site]?h(Button,{onClick:()=>void api('focus',{site:state.site,sessionId}).catch(e=>setError(e.message))},'Show paired chat'):null,
        state.failureDetails?.category==='website-capacity'?h('p',{role:'status'},state.failureDetails.nextAction):null,
        state.pendingHandoff?h('p',{role:'status'},`Model handoff · ${providers.find(([id])=>id===state.pendingHandoff.from)?.[1]||state.pendingHandoff.from} → ${providers.find(([id])=>id===state.pendingHandoff.to)?.[1]||state.pendingHandoff.to} · ${state.pendingHandoff.status}`):null,
        state.handoffs?.length?h('details',null,h('summary',null,'Saved model chats'),...Object.entries(state.pairs||{}).map(([site,pair])=>h('p',{key:site},h(Button,{disabled:busy,title:pair.url,onClick:()=>void api('focus',{site,sessionId}).catch(e=>setError(e.message))},h(Icon,{site}), ' ',providers.find(([id])=>id===site)?.[1]||site),state.activeProvider===site?' · current':'')),h('p',null,'Use the existing model selector to continue this same task. Saved chats reopen automatically when needed.')):null,
        activity?.revision?h('details',{className:'hbm-activity'},
          h('summary',null,h('span',{role:'status'},`Friday · ${activity.phase} · ${activity.message||'Task activity'}`)),
          h('ol',{className:'hbm-timeline'},...(activity.events||[]).filter(event=>event.type==='CUSTOM'&&event.name==='friday.connection'||['RUN_STARTED','RUN_FINISHED','RUN_ERROR','TOOL_CALL_START','TOOL_CALL_RESULT'].includes(event.type)).slice(-18).map(event=>h('li',{key:event.metadata.friday.revision},
            h('time',null,new Date(event.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})), ' ',
            event.type==='CUSTOM'?event.value.message:event.type==='TOOL_CALL_START'?`${event.toolCallName} requested`:event.type==='TOOL_CALL_RESULT'?'Harness returned a tool result':event.type==='RUN_STARTED'?'Harness task started':event.type==='RUN_ERROR'?event.message:'Harness turn finished'))),
          ...(activity.tools||[]).slice(-12).map(tool=>h('details',{className:'hbm-tool',key:tool.id},
            h('summary',null,`${tool.name} · ${tool.status}`),h('pre',null,tool.arguments),tool.result?h('pre',null,tool.result):h('p',null,tool.status==='requested'?'Awaiting Harness execution or permission decision.':'No text output. See the native transcript for attachments or details.'))),
          ...(activity.interactions||[]).slice(-8).map(item=>h(NativeInteractionRecord,{key:item.id,item})),
          activity.screenshots?.length?h('div',{className:'hbm-images'},...activity.screenshots.slice(-6).map(image=>h('figure',{key:image.id},h('a',{href:image.url,target:'_blank',rel:'noopener'},h('img',{src:image.url,alt:image.alt||'Harness tool screenshot',loading:'lazy'})),h('figcaption',null,'Harness screenshot')))):null,
          activity.phase==='interrupted'?h('p',null,'Review the native transcript and pending tool results before retrying. Completed actions are never automatically replayed.'):null):null,
        state.warnings?.length?h('details',{open:true},h('summary',null,'File transfer needs attention'),...state.warnings.map((warning,index)=>h('p',{key:index,role:'alert'},warning))):null,
        state.recovery?.length?h('details',{className:'hbm-recovery'},h('summary',null,'Last recovery diagnostic'),
          h(Button,{disabled:busy,onClick:()=>void api('health',{site:state.site,sessionId}).catch(e=>setError(e.message))},'Check this connection'),h(Button,{disabled:busy,onClick:()=>void api('refresh-provider',{site:state.site,sessionId}).catch(e=>setError(e.message))},'Refresh paired tab'),h(Button,{disabled:busy,onClick:()=>void api('pair-provider',{site:state.site,sessionId}).catch(e=>setError(e.message))},'Pair active Chrome tab'),
          h('p',null,`${state.recovery.at(-1).provider} · ${state.recovery.at(-1).category} · submission: ${state.recovery.at(-1).submission}`),
          h('p',null,state.recovery.at(-1).nextAction),
          h('p',null,'No request was automatically repeated or sent to a backup. To use DeepSeek, enable it in Settings → Models and select DeepSeek for a new request. Review uncertain earlier actions first.')):null,
        busy && !activity?.revision ?
          h('div', { className: 'hbm-session-message', role: 'status' }, state.message,
            state.percent !== null && state.percent !== undefined ? ` · ${state.percent}%` : '') : null,
        state.phase === 'generating' ? h('progress', { className: 'hbm-progress', max: 100,
          ...(state.percent === null ? {} : { value: state.percent }), 'aria-label': 'Website image generation progress' }) : null,
        state.progress?.length ? h('details', { className: 'hbm-progress-history' },
          h('summary', null, 'Reported image progress'), h('p', null, state.progress.map(item => `${item.percent}%`).join(' → '))) : null,
        error||streamError ? h('p', { className: 'hbm-error', role: 'status' }, error||streamError) : null);
    }
    function WebsiteModels() {
      const [state, setState] = React.useState(null);
      const [working, setWorking] = React.useState('');
      const [error, setError] = React.useState('');
      const [loadError, setLoadError] = React.useState('');
      React.useEffect(() => {
        let disposed = false; let pending = false;
        const refresh = async () => { if (pending) return; pending = true;
          try { const value = await api('status'); if (!disposed) { setState(value); setLoadError(''); } }
          catch (e) { if (!disposed) setLoadError(e.message); } finally { pending = false; } };
        void refresh(); const timer = setInterval(refresh, 2000);
        return () => { disposed = true; clearInterval(timer); };
      }, []);
      async function act(action, site) {
        if (working) return; setWorking(`${site}:${action}`); setError('');
        try { await api(action, { site }); setState(await api('status')); }
        catch (e) { setError(e.message); } finally { setWorking(''); }
      }
      const disabled = !!working || !!state?.busy || !state;
      return h('section', { className: 'hbm-section', 'aria-label': 'Friday browser website models' },
        h('h3', null, 'Friday'),
        window.fridayDesktopWorkspace?.setup?h(Button,{onClick:event=>{
          event.currentTarget.closest('[role="dialog"]')?.querySelector('button[aria-label="Close"]')?.click();
          window.dispatchEvent(new Event('friday-show-setup'));
        }},'Connect an assistant'):null,
        h('p', { className: 'hbm-description' }, 'Use a website chat without a model API key. Sign in only if the website requires it.'),
        h('div', { className: 'hbm-list' }, ...(state?.providers||providers.map(([id,name])=>({id,name}))).map(provider => {const site=provider.id,name=provider.name;
          const shared=state?.transport==='shared-browser';const extension=shared||state?.transport==='extension'||state?.transport==='desktop';
          const active = state?.site === site; const open = active && state.browserOpen; const connected = extension?state.connected&&state.enabledSites?.includes(site):active&&state.enabled;
          return h('div', { className: 'hbm-provider', key: site },
            h('div', { className: 'hbm-identity' }, h(Icon, { site }), h('div', null,
              h('div', { className: 'hbm-name' }, name, h('span', { className: 'hbm-tag' }, site==='chatgpt-web'?'Website':'Experimental')),
              h('div', { className: 'hbm-status', role: 'status' }, working.startsWith(site) ? 'Working…' : shared?!state.connected?'Friday browser is starting':connected?'Protected model tab · persistent profile':'Connection disabled':extension?!state.connected?(state.transport==='desktop'?'Open Friday desktop':'Open Chrome with Friday enabled'):connected?(state.transport==='desktop'?'Desktop connector enabled':'Chrome connector enabled'):'Connector disabled':open ? state.phase : 'Not connected'),
              h('div',{className:'hbm-description'},`${provider.backup?'Backup · ':''}${provider.health?.state||'unchecked'} · ${provider.capabilities?.fileTransfer?'text, tools, images and files':'text and tool protocol; other transfers unverified'}`))),
            extension?h('div',{className:'hbm-actions'},h(Button,{disabled:disabled||!state.connected,onClick:()=>act('health',site)},'Check health'),shared?h(Button,{disabled:disabled||!state.connected,onClick:()=>act('open',site)},'Show model tab'):null,h(Button,{disabled:disabled||state.pending>0||!state.connected,onClick:()=>act(connected?'disconnect':'connect',site)},connected?'Disable connector':'Enable connector')):h('div', { className: 'hbm-actions' },
              h(Button, { disabled, onClick: () => act('open', site), 'aria-label': `Open ${name} website` }, open ? 'Reopen website' : 'Open website'),
              h(Button, { disabled: disabled || !open, onClick: () => act(connected ? 'test' : 'connect', site), 'aria-label': connected ? `Test ${name} connection` : `Connect ${name}` }, connected ? 'Test' : 'Connect'),
              open ? h(Button, { disabled, onClick: () => act('disconnect', site), 'aria-label': `Disconnect ${name}` }, 'Disconnect') : null));
        })),
        error || loadError ? h('p', { className: 'hbm-error', role: 'alert' }, error || loadError) : null,
        state?.lastError && !error ? h('p', { className: 'hbm-error', role: 'alert' }, state.lastError) : null,
        state?.testReply ? h('p', { className: 'hbm-description', role: 'status' }, `Website test reply: ${state.testReply}`) : null,
        state?.backendVersion?h('p',{className:'hbm-description'},`Friday backend ${state.backendVersion} · connector ${state.extensionVersion||'not seen'}`):null,
        state?.metrics?h('details',null,h('summary',null,'Local transport diagnostics'),
          h('p',{className:'hbm-description'},`${state.metrics.attempts} recent attempts · ${state.metrics.completed} replies completed · ${state.metrics.failed} failed · ${state.metrics.cancelled} cancelled. These are transport attempts, not complete-task success rates.`),
          state.metrics.meanDurationMs!==null?h('p',{className:'hbm-description'},`Mean observed request duration: ${(state.metrics.meanDurationMs/1000).toFixed(1)}s. Measurements stay local; no token usage is inferred.`):null):null,
        state?.journalWindow?h('p',{className:'hbm-description'},`Recent audit cache: ${state.journalWindow.records} records, ${(state.journalWindow.serializedBytes/1048576).toFixed(1)} MiB of serialized content. Full history remains on disk.`):null,
        h('p', { className: 'hbm-description hbm-help' },state?.transport==='shared-browser'?'ChatGPT and task tabs use the same Friday browser window. Model tabs are hidden from task-tab tools. Login stays in the dedicated Friday profile; your normal Chrome profile is untouched. Sign in only if required. Enabled indicates the browser worker heartbeat, not a verified reply or login.':state?.transport==='extension'?'Friday pairs a Chrome website conversation automatically when you send a task. Two-way chat enables after pairing. Enabled indicates the connector heartbeat, not a successful model-reply test.':'Friday reconnects when the website chat is ready. Sign in only if the website requires it.'));
    }
    const css = `/* Keep Harness's accessible toggle and its real open/close action. */
.wtg9ga_railMark, .wtg9ga_brandMark { display:none !important; }
.wtg9ga_toggle .wtg9ga_panelIcon { display:inline-flex !important; opacity:1 !important; }
.wtg9ga_root.wtg9ga_collapsed { padding-inline:0 !important; }
.wtg9ga_collapsed .wtg9ga_logoRow { width:100%; }
.wtg9ga_collapsed .wtg9ga_iconButton,
.wtg9ga_collapsed .wtg9ga_panelRow,
.GAkraW_rail .GAkraW_search { align-self:center; flex-shrink:0; }
.wtg9ga_collapsed .wtg9ga_regionArea { align-items:center; width:100%; }
.wtg9ga_collapsed .wtg9ga_newSession { margin-inline:auto !important; }
.wtg9ga_collapsed .wtg9ga_toggle { background:transparent !important; }
.wtg9ga_toggle:hover { background:var(--dsw-alias-interactive-bg-hover) !important; }
.hbm-provider-icon { width:18px; height:18px; flex:none; vertical-align:middle; }
.hbm-session{font-size:12px;color:var(--dsw-alias-label-secondary);padding:10px 14px;border-bottom:1px solid var(--dsw-alias-border-primary,#48484a);max-height:340px;overflow:auto}.hbm-session-line,.hbm-pair-label,.hbm-pair-actions{display:flex;align-items:center;gap:8px}.hbm-session-line{justify-content:space-between;flex-wrap:wrap}.hbm-pair-label svg{width:16px;height:16px}.hbm-session a{color:var(--dsw-alias-label-primary);text-decoration:underline;text-underline-offset:3px}.hbm-chat-url{font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:4px;opacity:.75}.hbm-session-message{margin-top:8px}.hbm-progress{display:block;width:100%;height:6px;margin-top:8px;accent-color:#8ca9ff}.hbm-progress-history{margin-top:8px}.hbm-progress-history p{overflow-wrap:anywhere}.hbm-images{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px}.hbm-images figure{margin:0;max-width:320px}.hbm-images img{display:block;max-width:100%;max-height:200px;object-fit:contain;border-radius:10px}.hbm-images figcaption{margin-top:5px}.hbm-section{margin-top:24px;color:var(--dsw-alias-label-primary);font:inherit}.hbm-section h3{font-size:16px;font-weight:600;margin:0 0 8px}.hbm-description{color:var(--dsw-alias-label-secondary);font-size:13px;line-height:20px;margin:0 0 16px}.hbm-list{border:1px solid var(--dsw-alias-border-primary, #48484a);border-radius:16px;overflow:hidden}.hbm-provider{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 20px}.hbm-provider+.hbm-provider{border-top:1px solid var(--dsw-alias-border-primary,#48484a)}.hbm-identity{display:flex;align-items:center;gap:12px;min-width:0}.hbm-identity svg{flex-shrink:0}.hbm-name{font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px}.hbm-tag{font-size:11px;font-weight:400;color:var(--dsw-alias-label-secondary);border:1px solid var(--dsw-alias-border-primary,#48484a);border-radius:5px;padding:0 5px}.hbm-status{font-size:12px;color:var(--dsw-alias-label-secondary);margin-top:4px;max-width:260px}.hbm-actions{display:flex;align-items:center;gap:8px;flex-shrink:0}.hbm-error{font-size:13px;line-height:20px;color:var(--dsw-alias-label-danger,#ff9999);overflow-wrap:anywhere}.hbm-help{margin:14px 0 0}@media(max-width:720px){.hbm-provider{align-items:flex-start;flex-direction:column;padding:16px}.hbm-actions{flex-wrap:wrap}.hbm-status{max-width:none}}`;
    function apply(ctx) {
      ctx.inject(['layout'],scope=>{
        scope.effect(()=>{selectModelsPage=id=>scope.layout.selectPanel(id);return()=>{selectModelsPage=null;};});
        scope.slots.inject('main',()=>scope.slots.register({name:'main',key:'friday-models'},()=>h('section',{className:'hbm-models-web'},h(Button,{onClick:()=>scope.layout.selectPanel(null)},'Back to Friday'),h(WebsiteModels),h(Button,{onClick:()=>openAdvancedModels?.()},'Advanced API model settings'))));
      });
      ctx.effect(()=>{
        let disposed=false,cleanup;
        if(window.fridayDesktopWorkspace?.setup)void import('/browser-models/onboarding-client.mjs').then(async module=>{
          if(disposed)return;
          cleanup=await module.mountSetup({desktop:window.fridayDesktopWorkspace,marks:providerMarks,openAdvanced:()=>openAdvancedModels?.()});
          if(disposed)cleanup?.();
        }).catch(error=>console.warn('Friday setup unavailable:',error.message));
        return()=>{disposed=true;cleanup?.();};
      });
      ctx.slots.inject('sidebar.footer.action',()=>ctx.slots.register({name:'sidebar.footer.action',id:'friday-models',order:-100},ModelsLauncher));
      ctx.slots.inject('settings.launcher',()=>{
        if(ctx.slots.entries?.('settings.launcher')?.length)return()=>{};
        return ctx.slots.register({name:'settings.launcher',order:-100},ModelsSettingsBridge);
      });
      ctx.effect(()=>{
        let disposed=false,cleanup;
        void import('/browser-models/models-navigation.mjs').then(module=>{if(!disposed)cleanup=module.hideModelsSettingsNavigation({document,slots:ctx.slots});}).catch(error=>console.warn('Friday Models navigation unavailable:',error.message));
        return()=>{disposed=true;cleanup?.();};
      });
      ctx.effect(()=>{const style=document.createElement('style');style.textContent='.hbm-models-launcher{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:40px;background:transparent;color:inherit;border:0;border-radius:9px;cursor:pointer}.hbm-models-launcher:hover{background:#bca9ec14}.hbm-models-launcher:focus-visible{outline:2px solid #bca9ec;outline-offset:-2px}.hbm-models-launcher:has(span){justify-content:flex-start;padding-inline:16px}div:has(>.hbm-models-launcher){width:100%;flex:none}div:has(>div>.hbm-models-launcher):has(>div button[aria-label="Settings"]){flex-direction:column;align-items:stretch}';document.head.append(style);return()=>style.remove();});
      // Restore native frame preferences rather than overriding grid/drag geometry.
      ctx.inject(['layout'],scope=>scope.effect(()=>{
        const store=nativeLayoutStore({layout:scope.layout,document,events:window});
        let storage;try{storage=window.localStorage;}catch{}
        return installLayoutPreferences({store,storage,events:window});
      }));
      ctx.inject(['sidebarRight','sidebarRightTabs'],scope=>{
        nativeDock=scope.sidebarRight;
        scope.effect(()=>{
          if(!window.fridayDesktopWorkspace?.registerTaskBrowser)return;
          // The webview's native methods belong to the renderer's main world.
          const register=()=>{for(const element of document.querySelectorAll('webview[data-sidebar-browser-frame="webview"]'))try{
            const guestId=element.getWebContentsId(),tabId=element.closest('[data-sidebar-right-tab]')?.dataset.sidebarRightTab,sessionId=element.closest('[data-sidebar-right-session]')?.dataset.sidebarRightSession;
            if(guestId&&tabId&&sessionId)window.fridayDesktopWorkspace.registerTaskBrowser({guestId,tabId,sessionId});
          }catch{}};
          const timer=setInterval(register,500);register();return()=>clearInterval(timer);
        });
        scope.effect(()=>window.fridayDesktopWorkspace?.onTaskBrowser(async input=>{
          try{
            const tabs=nativeDock.openTabs.getSnapshot();
            if(input.action==='close'||input.action==='focus'){
              if(!tabs.some(t=>t.tabId===input.tabId&&t.sessionId===input.sessionId&&t.kind==='browser'))throw Error('Native task tab is no longer available.');
              if(input.action==='close')nativeDock.close(input.tabId);else{
                nativeDock.focus(input.tabId);
                // Wait for the original retained tab to become the rendered
                // input surface before the main process focuses its guest.
                await new Promise(resolve=>setTimeout(resolve,0));
                const body=[...document.querySelectorAll('[data-sidebar-right-tab]')].find(el=>el.dataset.sidebarRightTab===input.tabId&&el.querySelector('webview'));
                body?.querySelector('webview')?.focus();
              }
            }else{
              const selected=nativeDock.commandTarget?.();
              const candidates=tabs.filter(t=>t.sessionId===input.sessionId&&t.kind==='browser');
              const existing=!input.fresh&&(candidates.find(t=>t.tabId===selected?.tabId)||candidates[0]);
              if(existing){
                nativeDock.focus(existing.tabId);
                // The upstream Browser deliberately restores saved pages only on
                // request. An agent connection is an explicit request to resume it.
                // Focusing a retained tab commits asynchronously. Wait for its
                // own body, never a similarly named control in another tab.
                for(let attempt=0;attempt<50;attempt++){
                  const bodies=[...document.querySelectorAll('[data-sidebar-right-tab]')].filter(el=>el.dataset.sidebarRightTab===existing.tabId);
                  const restore=bodies.flatMap(el=>[...el.querySelectorAll('button')]).find(button=>button.textContent.trim()==='Restore page');
                  if(restore){restore.click();break;}
                  if(bodies.some(el=>el.querySelector('webview')))break;
                  await new Promise(resolve=>setTimeout(resolve,100));
                }
              }else nativeDock.openTab('browser',{params:{url:input.url}});
            }
            window.fridayDesktopWorkspace.taskBrowserResult(input.nonce,{ok:true});
          }catch(error){window.fridayDesktopWorkspace.taskBrowserResult(input.nonce,{ok:false,error:error.message});}
        }));
        for(const [site,name] of providers){
          const id=providerKind(site);
          scope.effect(()=>scope.sidebarRightTabs.register({id,kind:id,title:()=>name,keepMounted:true}));
          scope.effect(()=>scope.sidebarRight.registerCloseHandler(id,()=>{throw Error('Provider tabs are protected. Select another tab to hide this provider.');}));
          scope.slots.inject('sidebar.right.pane.tab',()=>scope.slots.register({name:'sidebar.right.pane.tab',key:id,inject:sessionId=>({site,sessionId})},ProviderBody));
          scope.slots.inject('sidebar.right.pane.tab.title',()=>scope.slots.register({name:'sidebar.right.pane.tab.title',key:id,inject:sessionId=>({site,sessionId})},ProviderTitle));
        }
      });
      ctx.effect(()=>{const style=document.createElement('style');style.textContent='[role=tab]:has(.hbm-protected-provider) button[aria-label="Close"]{display:none!important}.hbm-provider-host{position:absolute;inset:0;background:#151515}.hbm-protected-provider{display:inline-flex;align-items:center;gap:6px}.hbm-protected-provider svg{width:15px;height:15px}.hbm-header-tools{position:relative}.hbm-header-tools,.hbm-provider-shortcuts{display:flex;align-items:center;gap:3px}.hbm-provider-shortcuts button,.hbm-header-tools>details>summary{display:flex;align-items:center;justify-content:center;width:28px;height:28px;background:transparent;color:inherit;border:0;border-radius:6px;cursor:pointer;list-style:none}.hbm-provider-shortcuts button:hover,.hbm-header-tools>details>summary:hover{background:#ffffff12}.hbm-provider-shortcuts svg{width:18px;height:18px}.hbm-header-activity{position:absolute;z-index:1000;top:100%;right:0;width:min(410px,80vw);background:var(--dsw-specific-input-major,#242424);border:1px solid #48484a;border-radius:10px;box-shadow:0 12px 36px #0006}.hbm-header-tools>details:not([open])>.hbm-header-activity{display:none}';document.head.append(style);return()=>style.remove();});

      ctx.effect(()=>{const style=document.createElement('style');style.textContent='[aria-label="Good response"],[aria-label="Bad response"]{display:none!important}';document.head.append(style);return()=>style.remove();});
      // Keep native approval/question action carriers and composer takeover untouched.
      // These definitions only add durable, non-actionable records to native chat.
      ctx.inject(['uiConversation'],scope=>scope.effect(()=>{
        let disposed=false;const cleanup=[];
        void import('/browser-models/interactions.mjs').then(module=>{
          if(disposed)return;
          for(const definition of module.interactionDefinitions())cleanup.push(scope.uiConversation.events.register(definition));
          cleanup.push(ctx.slots.inject('conversation.chat.node',()=>ctx.slots.register({name:'conversation.chat.node',key:'friday-native-interaction'},NativeInteractionRecord)));
        }).catch(error=>console.warn('Friday native interaction records unavailable:',error.message));
        return()=>{disposed=true;for(const dispose of cleanup.reverse())dispose?.();};
      }));
      ctx.effect(()=>{const style=document.createElement('style');style.textContent='.hbm-interaction{border:1px solid var(--dsw-alias-border-primary,#48484a);border-radius:12px;padding:12px 16px;margin:10px 0;background:var(--dsw-specific-input-major);overflow-wrap:anywhere}.hbm-interaction p{white-space:pre-wrap;margin:6px 0;line-height:1.5}.hbm-interaction [role=status]{color:var(--dsw-alias-label-secondary)}';document.head.append(style);return()=>style.remove();});
      // Presentation alias for upstream product descriptions in native Settings.
      // Never rewrite saved messages, editable fields, code, package IDs or license files.
      ctx.effect(()=>{let scheduled=false;const update=()=>{scheduled=false;for(const dialog of document.querySelectorAll('[role="dialog"]')){const walker=document.createTreeWalker(dialog,NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode()))if(!node.parentElement?.closest('textarea,input,[contenteditable],pre,code')&&/DeepSeek\s+Harness/.test(node.nodeValue))node.nodeValue=node.nodeValue.replace(/DeepSeek\s+Harness/g,'Friday');}};const observer=new MutationObserver(()=>{if(!scheduled){scheduled=true;queueMicrotask(update);}});observer.observe(document.body,{subtree:true,childList:true,characterData:true});update();return()=>observer.disconnect();});
      ctx.effect(() => { const style = document.createElement('style'); style.textContent = css; document.head.append(style); return () => style.remove(); });
      ctx.effect(()=>{const style=document.createElement('style');style.textContent='.hbm-activity>summary{cursor:pointer;line-height:1.6;overflow-wrap:anywhere;color:var(--dsw-alias-label-primary)}.hbm-timeline{padding-left:18px;line-height:1.7}.hbm-timeline time{font-variant-numeric:tabular-nums;opacity:.65}.hbm-tool{border-top:1px solid var(--dsw-alias-border-primary,#48484a);padding:8px 0}.hbm-tool summary{cursor:pointer}.hbm-tool pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;max-height:180px;overflow:auto;line-height:1.5}.hbm-activity .hbm-images img{max-height:140px;max-width:240px}';document.head.append(style);return()=>style.remove();});
      ctx.effect(()=>{const style=document.createElement('style');style.textContent='.hbm-model-label{display:inline-flex;align-items:center;gap:7px}.hbm-model-label svg{width:18px;height:18px;flex:none}.hbm-friday-logo{display:block;width:min(320px,65vw);height:100px;object-fit:cover;object-position:center}span:has(.hbm-friday-logo){width:auto!important;height:auto!important;overflow:visible!important}span:has(.hbm-friday-logo)+span{display:none}';document.head.append(style);return()=>style.remove();});
      ctx.slots.inject('conversation.input.model.label',()=>ctx.slots.register({name:'conversation.input.model.label',order:-100},FridayModelLabel));
      ctx.slots.inject('conversation.hero.brand.mark',()=>ctx.slots.register({name:'conversation.hero.brand.mark',order:-100},FridayLogo));
      ctx.effect(()=>{const style=document.createElement('style');style.textContent='.hbm-friday-mark{display:inline-flex;align-items:center;justify-content:center;border:1.5px solid currentColor;border-radius:6px;font:bold 20px Georgia,serif;line-height:1;flex-shrink:0}.hbm-friday-wordmark{display:block;width:110px;height:38px;object-fit:cover;object-position:center}';document.head.append(style);return()=>style.remove();});
      ctx.slots.inject('sidebar.brand.mark',()=>ctx.slots.register({name:'sidebar.brand.mark',order:-100},FridayMark));
      ctx.slots.inject('sidebar.brand.name',()=>ctx.slots.register({name:'sidebar.brand.name',order:-100},FridayWordmark));
      ctx.slots.inject('conversation.session.header.utilities', () => ctx.slots.register({ name: 'conversation.session.header.utilities',
        id: 'friday-connection-activity', order: -10, inject: sessionId => ({ sessionId }) }, FridayHeader));
    }
    return { inject: ['slots'], apply };
  }
});
