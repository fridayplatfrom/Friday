(() => {
  // Web-shell branding only. Native package IDs and saved session identities stay intact.
  const brandTitle=()=>{if(typeof document.title!=='string')return;const title=document.title.replace(/DeepSeek\s+Harness/gi,'Friday');if(title!==document.title)document.title=title;};
  brandTitle();if(document.head&&typeof MutationObserver==='function')new MutationObserver(brandTitle).observe(document.head,{subtree:true,childList:true,characterData:true});
  if(document.head){let icon=document.querySelector('link[rel="icon"]');if(!icon){icon=document.createElement('link');icon.rel='icon';document.head.append(icon);}icon.href='/browser-models/brand/friday.png';icon.type='image/png';}
  // Runs outside the native UI plugin lifecycle so a failed reconnect cannot remove it.
  let instance; let pending = false; let banner; let unavailable = false; let reconnectNeeded = false;
  function show(text, reconnect = false) {
    if (!document.body) return;
    if (!banner) { banner = document.createElement('aside'); banner.setAttribute('role', 'status');
      banner.style.cssText = 'position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:2147483600;padding:10px 16px;background:#292b30;color:#fff;border:1px solid #777;border-radius:10px;font:13px system-ui;max-width:90vw'; document.body.append(banner); }
    banner.replaceChildren(document.createTextNode(text));
    if (reconnect) { const button = document.createElement('button'); button.textContent = 'Reconnect Friday';
      button.style.marginLeft = '12px'; button.onclick = () => location.reload(); banner.append(button); }
  }
  async function check() {
    if (pending) return; pending = true;
    try {
      const response = await fetch('/browser-models/status', { credentials: 'same-origin', cache: 'no-store',
        headers: { 'X-Harness-Models': '1' }, signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error('Unavailable');
      const status = await response.json();
      if (instance && status.instanceId !== instance) reconnectNeeded = true;
      if (reconnectNeeded) {
        show('Friday restarted. Reconnect to restore the saved conversation.', true);
        // Recover a blank crashed UI; preserve editors and attachment drafts.
        const editor = document.querySelector('textarea,[contenteditable="true"],[role="textbox"]');
        if (!editor) { location.reload(); return; }
      } else if (unavailable) { banner?.remove(); banner = null; }
      instance = status.instanceId; unavailable = false;
    } catch { unavailable = true; show('Friday is offline — waiting to reconnect. Saved history has not been cleared.'); }
    finally { pending = false; }
  }
  setInterval(() => void check(), 2000); void check();
})();
