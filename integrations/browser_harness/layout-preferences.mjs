const KEY='friday.layout.v1';
const valid=value=>Number.isFinite(value)&&value>=300&&value<=20000;
/** Keep the native root store and divider authoritative; persist only its width preference. */
export function installLayoutPreferences({store,storage,events,delay=150,setTimer=setTimeout,clearTimer=clearTimeout}){
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
export function nativeLayoutStore({layout,document,events}){
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
