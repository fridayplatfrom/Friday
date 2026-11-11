(() => {
  let config = null; let api; let panel; let label; let flushing = false; let heartbeatAt = 0; let pullAt = -Infinity; let pulling = false;
  let contextAlive=true;
  function runtimeSend(message){
    if(!contextAlive)return Promise.resolve({ok:false,error:'Friday updated. Refresh this paired page to reconnect.'});
    const failed=error=>{if(/context invalidated|extension context/i.test(String(error?.message))){contextAlive=false;config=null;notify('Friday updated. Refresh this paired page to reconnect.');}throw error;};
    try{return Promise.resolve(chrome.runtime.sendMessage(message)).catch(failed);}catch(error){try{failed(error);}catch(failure){return Promise.reject(failure);}}
  }
  const captures = new Map();
  const captureKey=typeof location!=='undefined'?'harness-captures:'+location.pathname:null;
  const persistCaptures=()=>{if(typeof sessionStorage!=='undefined'&&captureKey)sessionStorage.setItem(captureKey,JSON.stringify([...captures.values()].filter(capture=>capture.turnKey).map(({id,text,at,state,turnKey,fileIds})=>({id,text,at,state,turnKey,fileIds}))));};
  if(typeof sessionStorage!=='undefined'&&captureKey){try{for(const saved of JSON.parse(sessionStorage.getItem(captureKey)||'[]'))captures.set(saved.id,{...saved,baseline:new Set(),baselineImages:new Set(),baselineTurns:new Set(),userNodes:new Set(),turnKeys:new Set()});}catch{}}
  let seenTurns = new Set(); const suppressed = []; let lastHumanActionAt = -Infinity; let newestTurn = -1;
  const turnNumber = turn => Number(turn.querySelector?.('[data-content-search-turn-key]')?.getAttribute('data-content-search-turn-key')?.match(/fallback-turn-(\d+)$/)?.[1] ?? NaN);
  const normalize = text => String(text || '').replace(/\s+/g, ' ').trim();
  const transportId=text=>normalize(text).match(/^HARNESS_REQUEST_ID\s+([a-f0-9-]{36})(?:\s|$)/i)?.[1]?.toLowerCase();
  const outboundMatches=(expected,actual)=>expected===normalize(actual)||!!transportId(expected)&&transportId(expected)===transportId(actual);
  const userSelector = '[data-message-author-role="user"], [data-user-message-bubble="true"]';
  const users = () => [...document.querySelectorAll(userSelector)];
  const turns = () => [...document.querySelectorAll('[data-turn-key]')];
  const value = composer => (composer?.value || composer?.innerText || '').trim();
  function notify(text) { if (label) label.textContent = text; }
  function configure(next) {
    if (next.url && typeof location !== 'undefined' && next.url !== location.origin + location.pathname) next = { enabled: false };
    heartbeatAt = Date.now();
    if (next.enabled && !config?.enabled) {
      seenTurns = new Set(turns().map(turn => turn.getAttribute('data-turn-key')));
      newestTurn = Math.max(-1, ...turns().map(turnNumber).filter(Number.isFinite));
    }
    config = next;
    if (!next.enabled) { panel?.remove(); panel = null; label = null; return; }
    if (!panel) {
      panel = document.createElement('aside'); panel.id = 'harness-two-way-status';
      panel.setAttribute('aria-label', 'Friday two-way connection');
      panel.style.cssText = 'position:fixed;right:16px;bottom:100px;z-index:2147483600;max-width:290px;padding:12px 14px;border:1px solid #555;border-radius:12px;background:#202124;color:#eee;font:12px/1.5 system-ui;box-shadow:0 8px 24px #0005';
      const heading = document.createElement('strong'); heading.textContent = 'Friday · Two-way chat';
      label = document.createElement('div'); label.setAttribute('role', 'status');
      const stop = document.createElement('button'); stop.textContent = 'Stop task'; stop.style.cssText = 'margin-top:8px;cursor:pointer';
      stop.addEventListener('click', () => {
        api.cancelActive();
        void runtimeSend({ type: 'harness-web-stop' }).then(result => notify(result.ok ? 'Harness stopped' : result.error)).catch(()=>notify('Refresh this paired page to reconnect.'));
        api.stopWebsite();
      });
      panel.append(heading, label, stop); document.body.append(panel);
    }
    // ChatGPT hydration can replace the body after our initial idle injection.
    if (panel.isConnected === false) document.body.append(panel);
    if (next.online === false || ![...captures.values()].some(capture => capture.state === 'pending')) notify(next.status);
  }
  function intent() {
    if (!config?.enabled || !api) return;
    const text = value(api.composer()); if (!text || text.length > 80000) return;
    // Desktop input events are trusted mouse/keyboard events. They still belong
    // to this outbound request; do not capture or cancel it as a human turn.
    // Leave the suppression entry for the subsequent user-bubble observer.
    if(suppressed.some(item=>outboundMatches(item.text,text)&&Date.now()-item.at<120000))return;
    const recent = [...captures.values()].at(-1);
    if (recent && recent.text === text && Date.now() - recent.at < 250) return;
    const capture = { id: crypto.randomUUID(), text, at: Date.now(), state: 'pending',
      baseline: new Set(api.responses()), baselineImages: new Set(api.images().map(image => image.currentSrc || image.src)),
      baselineTurns: new Set(api.progressTurns()), userNodes: new Set(users()), turnKeys: new Set(turns().map(turn => turn.getAttribute('data-turn-key'))) };
    captures.set(capture.id, capture);
    const oldJobId = api.cancelActive();
    if (oldJobId) void runtimeSend({ type: 'harness-web-stop', jobId: oldJobId }).catch(() => {});
    notify('Waiting for ChatGPT to accept your message…');
  }
  async function flush() {
    if (flushing || !config?.enabled || !api) return;
    flushing = true;
    try {
      // Website interactive buttons can submit a user turn without an editor Send event.
      // Observe newly added user turns; explicitly suppress our own outbound prompts.
      for (const turn of turns()) {
        const turnKey = turn.getAttribute('data-turn-key'); if (!turnKey || seenTurns.has(turnKey)) continue;
        const user = turn.querySelector?.(userSelector);
        const text = normalize(user?.innerText); if (!text) continue;
        seenTurns.add(turnKey);
        const number = turnNumber(turn); const older = Number.isFinite(number) && number <= newestTurn;
        if (Number.isFinite(number)) newestTurn = Math.max(newestTurn, number);
        const ignored = suppressed.findIndex(item => outboundMatches(item.text,text) && Date.now() - item.at < 120000);
        // One request can be remounted under several DOM turn keys. Keep its
        // unique transport identity suppressed for the entire admission window.
        if (ignored >= 0) continue;
        if ([...captures.values()].some(capture => capture.turnKey === turnKey || capture.state === 'pending' && normalize(capture.text) === text)) continue;
        if (older || Date.now() - lastHumanActionAt > 15000) continue;
        if (text.length > 80000) { notify('Message is too large for Harness. No task was created.'); continue; }
        const capture = { id: crypto.randomUUID(), text: user.innerText.trim(), at: Date.now(), state: 'pending', turnKey,
          baseline: new Set(), baselineImages: new Set(), baselineTurns: new Set(), userNodes: new Set(), turnKeys: new Set() };
        captures.set(capture.id, capture);
        const oldJobId = api.cancelActive();
        if (oldJobId) void runtimeSend({ type: 'harness-web-stop', jobId: oldJobId }).catch(() => {});
      }
      for (const capture of captures.values()) {
        if (capture.state !== 'pending') continue;
        const turn = (capture.turnKey && turns().find(node => node.getAttribute('data-turn-key') === capture.turnKey)) || turns().find(node => !capture.turnKeys.has(node.getAttribute('data-turn-key')) && normalize(node.innerText).includes(normalize(capture.text))) ||
          users().find(node => !capture.userNodes.has(node) && normalize(node.innerText).includes(normalize(capture.text)))?.closest?.('[data-turn-key]');
        if (!turn?.getAttribute('data-turn-key')) {
          if (Date.now() - capture.at > 45000) { capture.state = 'unconfirmed'; notify('ChatGPT submission not confirmed. No Harness task was created.'); }
          continue;
        }
        capture.turnKey = turn.getAttribute('data-turn-key');
        persistCaptures();
        if (capture.retryAt && Date.now() < capture.retryAt) continue;
        notify('Sending your message to Harness…');
        let result;
        try {
          capture.fileIds ??= await globalThis.HarnessFiles?.take() || [];
          result = await runtimeSend({ type: 'harness-web-message', id: capture.id, text: capture.text,fileIds:capture.fileIds }); }
        catch (error) { result = { ok: false, error: error.message }; }
        if (result?.ok) { capture.state = 'accepted'; notify('Harness is receiving this ChatGPT reply…'); }
        else { capture.retryAt = Date.now() + 5000; notify(result?.error || 'Waiting to reconnect to Harness…'); }
        persistCaptures();
      }
      // Keep unconsumed accepted captures: a delayed agent must be able to attach.
      for (const [id, capture] of captures) if (capture.state === 'unconfirmed' && Date.now() - capture.at > 120000) captures.delete(id);
    } finally { flushing = false; }
  }
  function init(adapter) {
    api = adapter;
    document.addEventListener('keydown', event => {
      if (event.isTrusted && api.composer()?.contains(event.target)) lastHumanActionAt = Date.now();
      if (!event.isTrusted || event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
      const composer = api.composer(); if (composer && (event.target === composer || composer.contains(event.target))) intent();
    }, true);
    document.addEventListener('click', event => {
      if (event.isTrusted) lastHumanActionAt = Date.now();
      if (event.isTrusted && api.sendSelectors.some(selector => event.target?.closest?.(selector))) intent();
    }, true);
    new MutationObserver(() => void flush()).observe(document.body, { childList: true, subtree: true });
    setInterval(() => {
      if(!contextAlive)return;
      if (!pulling && Date.now() - pullAt > 4000) {
        pulling = true; pullAt = Date.now();
        void runtimeSend({ type: 'harness-listener-refresh' }).then(result => {
          if (result?.ok && result.config) configure(result.config);
        }).catch(() => {}).finally(() => { pulling = false; });
      }
      if (config?.enabled && Date.now() - heartbeatAt > 15000) notify('Harness connection lost — waiting to reconnect. Local tools cannot run.');
      void flush();
    }, 500);
  }
  globalThis.HarnessTwoWay = { init, configure, take: id => captures.get(id), forget: id => {captures.delete(id);persistCaptures();}, notify,
    suppressNext: text => { suppressed.push({ text: normalize(text), at: Date.now() }); if (suppressed.length > 100) suppressed.shift(); } };
})();
