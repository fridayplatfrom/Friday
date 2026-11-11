window.__ModuleLoader__.load({
  id: 'harness-browser-provider',
  factory: require => {
    const React = require('react');
    const { Button } = require('@deepseek-ai/dsh-client-ui-primitives');
    const h = React.createElement;
    const providers = [['chatgpt-web', 'ChatGPT'], ['deepseek-web','DeepSeek'], ['gemini-web', 'Gemini'], ['kimi-web', 'Kimi']];
    // Small vector provider marks remain legible in both Harness themes.
    function Icon({ site }) {
      const common = { width: 26, height: 26, viewBox: '0 0 24 24', fill: 'none', 'aria-hidden': true };
      if (site === 'gemini-web') return h('svg', common, h('path', { d: 'M12 1C12 8 8 12 1 12c7 0 11 4 11 11 0-7 4-11 11-11C16 12 12 8 12 1Z', fill: '#8ca9ff' }));
      if (site === 'deepseek-web') return h('svg', common, h('path', { d: 'M3 10c2-3 5-4 8-3 3 1 5 3 7 2l3-3v5l-3 2c-1 6-7 9-12 5-2-1-3-4-3-8Zm6 9-2 3 5-2M17 8l-1-5-3 4', fill: '#7195ff' }), h('circle', { cx: 7, cy: 11, r: 1, fill: '#fff' }));
      if (site === 'kimi-web') return h('svg', common, h('rect', { x: 1, y: 1, width: 22, height: 22, rx: 7, fill: '#5189ff' }), h('path', { d: 'M7 6v12M17 6l-7 6 7 6', stroke: '#fff', strokeWidth: 2.5, strokeLinecap: 'round', strokeLinejoin: 'round' }));
      return h('svg', common, ...Array.from({ length: 6 }, (_, i) => h('path', { key: i, d: 'M12 3c5-3 10 3 6 7l-6 4-4-2V7Z', transform: `rotate(${i * 60} 12 12)`, stroke: 'currentColor', strokeWidth: 1.25, strokeLinejoin: 'round' })));
    }
    const providerKind=site=>'friday-provider-'+site;
    let nativeDock;
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
      return h('div',{className:'hbm-header-tools'},h(ProviderShortcuts,props),
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
    const css = `.hbm-session{font-size:12px;color:var(--dsw-alias-label-secondary);padding:10px 14px;border-bottom:1px solid var(--dsw-alias-border-primary,#48484a);max-height:340px;overflow:auto}.hbm-session-line,.hbm-pair-label,.hbm-pair-actions{display:flex;align-items:center;gap:8px}.hbm-session-line{justify-content:space-between;flex-wrap:wrap}.hbm-pair-label svg{width:16px;height:16px}.hbm-session a{color:var(--dsw-alias-label-primary);text-decoration:underline;text-underline-offset:3px}.hbm-chat-url{font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:4px;opacity:.75}.hbm-session-message{margin-top:8px}.hbm-progress{display:block;width:100%;height:6px;margin-top:8px;accent-color:#8ca9ff}.hbm-progress-history{margin-top:8px}.hbm-progress-history p{overflow-wrap:anywhere}.hbm-images{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px}.hbm-images figure{margin:0;max-width:320px}.hbm-images img{display:block;max-width:100%;max-height:200px;object-fit:contain;border-radius:10px}.hbm-images figcaption{margin-top:5px}.hbm-section{margin-top:24px;color:var(--dsw-alias-label-primary);font:inherit}.hbm-section h3{font-size:16px;font-weight:600;margin:0 0 8px}.hbm-description{color:var(--dsw-alias-label-secondary);font-size:13px;line-height:20px;margin:0 0 16px}.hbm-list{border:1px solid var(--dsw-alias-border-primary, #48484a);border-radius:16px;overflow:hidden}.hbm-provider{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 20px}.hbm-provider+.hbm-provider{border-top:1px solid var(--dsw-alias-border-primary,#48484a)}.hbm-identity{display:flex;align-items:center;gap:12px;min-width:0}.hbm-identity svg{flex-shrink:0}.hbm-name{font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px}.hbm-tag{font-size:11px;font-weight:400;color:var(--dsw-alias-label-secondary);border:1px solid var(--dsw-alias-border-primary,#48484a);border-radius:5px;padding:0 5px}.hbm-status{font-size:12px;color:var(--dsw-alias-label-secondary);margin-top:4px;max-width:260px}.hbm-actions{display:flex;align-items:center;gap:8px;flex-shrink:0}.hbm-error{font-size:13px;line-height:20px;color:var(--dsw-alias-label-danger,#ff9999);overflow-wrap:anywhere}.hbm-help{margin:14px 0 0}@media(max-width:720px){.hbm-provider{align-items:flex-start;flex-direction:column;padding:16px}.hbm-actions{flex-wrap:wrap}.hbm-status{max-width:none}}`;
    function apply(ctx) {
      ctx.inject(['sidebarRight','sidebarRightTabs'],scope=>{
        nativeDock=scope.sidebarRight;
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
      ctx.slots.inject('settings.models.footer', () => ctx.slots.register({ name: 'settings.models.footer', id: 'browser-websites', order: -10 }, WebsiteModels));
      ctx.slots.inject('conversation.session.header.utilities', () => ctx.slots.register({ name: 'conversation.session.header.utilities',
        id: 'friday-provider-shortcuts', order: -10, inject: sessionId => ({ sessionId }) }, FridayHeader));
    }
    return { inject: ['slots'], apply };
  }
});
