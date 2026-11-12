(() => {
  document.documentElement?.setAttribute('data-friday-content-build','0.10.3-turn-recovery');
  // Visible DOM only. No page scripts, cookie access, private endpoints, or CAPTCHA handling.
  // BEGIN FRIDAY GENERATED PRESETS
  const presets = globalThis.FridayProviderCatalog ? Object.fromEntries(Object.entries(globalThis.FridayProviderCatalog).map(([id,p])=>[id,p.selectors])) : {"chatgpt-web":{"hosts":["chatgpt.com"],"composer":["#prompt-textarea","#mobile-composer-prompt","[contenteditable=\"true\"][role=\"textbox\"][aria-label=\"Ask ChatGPT\"]","textarea[placeholder*=\"Ask\"]"],"send":["button[data-testid=\"send-button\"]","button[aria-label=\"Send prompt\"]","button[aria-label=\"Send message\"]","button[aria-label=\"Send\"]"],"responses":["[data-message-author-role=\"assistant\"]","[data-markdown-text-style=\"assistant-message\"]"],"stop":["button[data-testid=\"stop-button\"]","button[aria-label=\"Stop generating\"]","button[aria-label=\"Stop streaming\"]","button[aria-label=\"Stop\"]"],"complete":["button[data-testid=\"copy-turn-action-button\"]","button[aria-label=\"Copy response\"]","[data-talvt-turn-state=\"complete\"] [data-markdown-text-style=\"assistant-message\"]"]},"deepseek-web":{"hosts":["chat.deepseek.com"],"composer":["textarea[placeholder=\"Message DeepSeek\"]","textarea"],"send":["[role=\"button\"].ds-button--primary.ds-button--circle","button[aria-label=\"Send\"]","[role=\"button\"][aria-label=\"Send\"]"],"responses":[".ds-assistant-message-main-content",".ds-message .ds-markdown"],"stop":["button[aria-label=\"Stop\"]","[role=\"button\"][aria-label=\"Stop\"]",".ds-button--primary.ds-button--circle:has(svg rect)"],"complete":["[aria-label=\"Read aloud\"]","[aria-label*=\"Copy\"]"],"users":[".ds-message:has(.ds-collapsible-text)"],"correlation":"ordered-user-message"},"gemini-web":{"hosts":["gemini.google.com"],"composer":["rich-textarea [contenteditable=\"true\"]","[contenteditable=\"true\"][role=\"textbox\"]"],"send":["button.send-button","button[aria-label=\"Send message\"]"],"responses":["model-response .model-response-text","model-response message-content"],"stop":["button[aria-label=\"Stop response\"]","button[aria-label=\"Stop generating\"]"],"complete":["button[aria-label=\"Copy\"]"],"users":["user-query"],"userText":".query-text-line","busy":["model-response message-content .markdown[aria-busy=\"true\"]"],"completionMarker":[".markdown[aria-busy=\"false\"]"],"responseContainer":"model-response","correlation":"ordered-user-message"},"kimi-web":{"hosts":["www.kimi.ai","www.kimi.com","kimi.com"],"composer":[".chat-input-editor[contenteditable=\"true\"]","[contenteditable=\"true\"][role=\"textbox\"]","textarea"],"send":[".send-button-container","button[aria-label=\"Send\"]","[data-testid=\"send-button\"]",".send-button"],"responses":[".segment-assistant .markdown-container:not(.toolcall-content-text) > .markdown",".segment-assistant .markdown-container:not(.toolcall-content-text)","[data-role=\"assistant\"]"],"stop":[".send-button-container.stop",".send-button-container .stop-icon","button[aria-label=\"Stop\"]",".stop-button"],"complete":["button[aria-label=\"Read aloud\"]","button[aria-label*=\"Copy\"]",".segment-assistant .copy-button"],"accessRequired":["[data-testid=\"login-phone-input\"]"],"users":[".segment-user"],"userText":".user-content__text","toolCodeHeading":"^HARNESS_TOOL_CALL\\s*(?:json)?\\s*(?:Copy)?$","busy":[".send-button-container.loading",".send-button-container.stop"],"errorNotices":["[data-testid=\"confirm-dialog\"] .body"],"responseContainer":".segment-assistant","correlation":"ordered-user-message"}};
  // END FRIDAY GENERATED PRESETS
  let active = null;
  const responseLoadPlaceholder = text => /^(?:this|the) response (?:couldn['’]t|could not) load[.!]?(?:\s*(?:try again|retry))?$/i.test(text);
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  // Background tabs may delay short timers by minutes. An owned extension
  // heartbeat can resume a due wait without focusing, submitting or retrying.
  const pageWait=(job,ms)=>new Promise(resolve=>{
    const due=Date.now()+ms;let timer;
    const wake=(force=false)=>{
      if(!force&&Date.now()<due)return;
      if(typeof clearTimeout==='function')clearTimeout(timer);
      if(job.wake===wake)delete job.wake;resolve();
    };
    job.wake=wake;timer=setTimeout(()=>wake(true),ms);
  });
  const visible = element => !!element && !!(element.getClientRects().length) && getComputedStyle(element).visibility !== 'hidden';
  const normalized = text => String(text||'').replace(/\s+/g,' ').trim();
  const disabled=node=>!node||node.disabled||node.getAttribute('aria-disabled')==='true'||node.classList?.contains('ds-button--disabled')||node.classList?.contains('disabled');
  const textBlocks=new Set(['P','DIV','LI','PRE','BLOCKQUOTE']);
  function messageText(node){
    if(node?.nodeType===3)return node.nodeValue||'';
    if(!node?.childNodes)return node?.innerText||'';
    if(node.nodeType!==1)return '';
    if(node.nodeName==='BR')return '\n';
    return [...node.childNodes].map(messageText).join('')+(textBlocks.has(node.nodeName)?'\n':'');
  }
  const editorText = node => node instanceof HTMLTextAreaElement || node instanceof HTMLInputElement ? node.value : messageText(node);
  const userMessageText = bubble => {
    const preset=Object.values(presets).find(p=>p.hosts.includes(location.hostname));
    const lines=preset?.userText&&bubble?.querySelectorAll?.(preset.userText);
    if(lines?.length)return [...lines].map(messageText).join('\n');
    // The bubble also contains Show more and a decorative ellipsis. Compare
    // only the actual message renderer when this observed layout exposes it.
    return messageText(bubble?.querySelector?.('[data-search-result-target]')||bubble);
  };
  function first(selectors) {
    for (const selector of selectors) for (const element of document.querySelectorAll(selector)) if (visible(element)) return element;
    return null;
  }
  function stopControl(preset){
    const semantic=first(preset.stop);if(semantic)return semantic;
    // DeepSeek's main control has no accessible label. Empty editor + enabled
    // primary control means generation is still active; idle Send is disabled.
    if(preset.hosts.includes('chat.deepseek.com')&&!editorText(first(preset.composer)).trim()){
      const control=first(preset.send);if(!disabled(control))return control;
    }
    return null;
  }
  function responses(preset) {
    for (const selector of preset.responses) {
      const matches = [...document.querySelectorAll(selector)].filter(visible);
      if (matches.length) return matches;
    }
    return [];
  }
  const generationActive=preset=>stopControl(preset)||(preset.busy&&first(preset.busy));
  function responseText(node){
    const raw=(node?.innerText||'').trim();
    if(!/^HARNESS_TOOL_CALL(?:\s|$)/.test(raw))return raw;
    if(node.querySelector?.('[data-math-source], .katex, math'))throw new Error('Tool request was rendered as mathematics. No command was executed. Use a literal JSON code block.');
    // DeepSeek renders highlighted spans directly inside pre, without code.
    const codes=[...(node.querySelectorAll?.(location.hostname==='chat.deepseek.com'?'pre':'pre code')||[])];
    if(codes.length!==1)return raw;
    const literal=(codes[0].textContent||'').trim();if(!literal)return raw;
    const at=raw.indexOf(literal);if(at<0)return raw;
    const before=raw.slice(0,at).trim(),after=raw.slice(at+literal.length).trim();
    // Only the observed language heading may surround this one visible block.
    // Extra prose or another block must remain invalid, never silently removed.
    const contract=Object.values(presets).find(p=>p.hosts.includes(location.hostname));
    const heading=contract?.toolCodeHeading?new RegExp(contract.toolCodeHeading,'i'):location.hostname==='chat.deepseek.com'?/^HARNESS_TOOL_CALL\s*(?:json)?\s*(?:Copy\s+Download)?$/i:/^HARNESS_TOOL_CALL\s*(?:json)?$/i;
    if(!heading.test(before)||after)return raw;
    return 'HARNESS_TOOL_CALL\n```json\n'+literal+'\n```';
  }
  function completedResponse(preset, node) {
    if (!node) return false;
    if(preset.correlation==='ordered-user-message')return !!firstInside(preset.responseContainer?node.closest(preset.responseContainer)||node:node.closest('.ds-message')?.parentElement||node,preset.complete);
    if (node.closest?.('[data-talvt-turn-state="complete"]')) return true;
    const turn = node.closest?.('article,model-response,.segment-assistant');
    return !!turn && !!firstInside(turn, preset.complete);
  }
  const imageSelector = '[data-testid="generated-image-preview"] img, button[aria-label^="Generated image"] img';
  const generatedImages = () => [...document.querySelectorAll(imageSelector)].filter(visible);
  // Read only the visible native image-generation UI, never percentages in user prompts or normal answers.
  function imageProgress(baselineTurns, imageStarted = false, turnKey = null) {
    const turns = [...document.querySelectorAll('[data-talvt-turn-state], article[data-testid^="conversation-turn-"]')]
      .filter(node => !baselineTurns.has(node) && visible(node) && (!turnKey || node.closest?.('[data-turn-key]')?.getAttribute('data-turn-key') === turnKey));
    for (const turn of turns.reverse()) {
      if (turn.getAttribute('data-talvt-turn-state') === 'complete') continue;
      // Current ChatGPT wraps the user prompt and assistant in one turn. A
      // quoted source file mentioning image creation is not generation UI.
      const assistant = turn.querySelector('[data-message-author-role="assistant"], [data-markdown-text-style="assistant-message"]');
      const user = turn.querySelector('[data-user-message-bubble], [data-message-author-role="user"]');
      const text = (assistant ? assistant.innerText : user ? '' : turn.innerText) || '';
      let bar = turn.querySelector('[role="progressbar"]');
      if(bar?.closest?.('[data-user-message-bubble], [data-message-author-role="user"]'))bar=null;
      if(/^\s*HARNESS_TOOL_CALL(?:\s|$)/.test(text))continue;
      const phase = text.match(/creating image|generating image|making the first draft|sketching it out|adding details|finishing touches|rendering image|refining image|one last tweak/i)?.[0];
      if (!phase && !bar && !(imageStarted && text.length < 1000 && /\d\s*%/.test(text))) continue;
      const number = bar?.getAttribute('aria-valuenow');
      const percent = number !== null && number !== undefined ? Number(number) : Number(text.match(/(?:^|\s)(\d{1,3}(?:\.\d+)?)\s*%/)?.[1] ?? NaN);
      return { percent: Number.isFinite(percent) && percent >= 0 && percent <= 100 ? percent : null,
        message: phase || bar?.getAttribute('aria-label') || text.split('\n').find(line => line.trim() && !/^\s*[\d.%]+\s*$/.test(line))?.trim().slice(0, 120) || 'Creating image' };
    }
    return null;
  }
  async function transferImage(job, image) {
    const source = image.currentSrc || image.src;
    // These are bytes of a displayed generated asset, not a private service endpoint.
    const url = new URL(source, location.href);
    if (!['blob:', 'data:'].includes(url.protocol) && url.origin !== location.origin) throw new Error('Generated image is not readable from this website.');
    const response = await fetch(source);
    if (!response.ok) throw new Error('Could not read the displayed generated image.');
    const blob = await response.blob();
    if (blob.size > 16 * 1024 * 1024 || !['image/png', 'image/jpeg', 'image/webp'].includes(blob.type)) throw new Error('Generated image format or size is unsupported.');
    const data = await new Promise((resolve, reject) => {
      const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = reject; reader.readAsDataURL(blob);
    });
    await sendEvent({ id: job.id, type: 'image-start', mime: blob.type, alt: image.alt || 'Generated image' });
    for (let offset = 0, index = 0; offset < data.length; offset += 768000, index++) {
      if (job.cancelled) return;
      await sendEvent({ id: job.id, type: 'image-chunk', index, data: data.slice(offset, offset + 768000) });
    }
    await sendEvent({ id: job.id, type: 'image-end' });
  }
  function firstInside(root, selectors) {
    const candidates=new Set();
    for(const selector of selectors)for(const element of root.querySelectorAll(selector))if(visible(element)&&!disabled(element))candidates.add(element);
    if(candidates.size>1)throw new Error('Multiple enabled send controls found in the paired editor. Nothing was submitted.');
    return [...candidates][0]||null;
  }
  async function sendEvent(event) {
    if(typeof crypto!=='undefined')event.eventId ||= crypto.randomUUID();
    let result;
    for(let attempt=0;attempt<8;attempt++){
      try{result=await chrome.runtime.sendMessage({type:'harness-event',event});if(result?.ok)return;
        if(/expired|cancelled|Unowned/.test(result?.error||''))break;
      }catch(error){result={error:error.message};}
      await sleep(Math.min(4000,250*2**attempt));
    }
    throw new Error(result?.error || 'Local bridge stopped.');
  }
  function fill(element, text) {
    element.focus();
    if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
      const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, text);
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      // execCommand inserts through the editor's input path, preserving React/ProseMirror state.
      const selection = window.getSelection(); const range = document.createRange();
      range.selectNodeContents(element); selection.removeAllRanges(); selection.addRange(range);
      // Lexical's plain insertText handler drops newline characters. Its paste
      // handler preserves the exact text and updates editor state atomically.
      if(text.includes('\n')&&element.getAttribute('data-lexical-editor')==='true'&&typeof DataTransfer==='function'&&typeof ClipboardEvent==='function'){
        const data=new DataTransfer();data.setData('text/plain',text);
        if(!element.dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true})))return;
        // Some Lexical pages ignore synthetic paste. Native HTML insertion can
        // retain literal newline text without creating filtered paragraph nodes.
        const escaped=text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        if(document.execCommand('insertHTML',false,'<span style="white-space:pre-wrap">'+escaped+'</span>'))return;
      }
      if (!document.execCommand('insertText', false, text)) throw new Error('Website editor rejected insertion. No message was sent.');
    }
  }
  async function run(message) {
    const preset = presets[message.site];
    if (!preset || !preset.hosts.includes(location.hostname)) throw new Error('Website mismatch.');
    if (active) throw new Error('This browser tab is already handling a request.');
    if (typeof message.prompt !== 'string' || message.prompt.length > 80000) throw new Error('Invalid prompt.');
    const tracked=message.purpose==='introduction'||message.purpose==='context'||/^(?:You are answering one request for a local Harness agent\.|Harness continuation:|FRIDAY MODEL HANDOFF:|Friday connector feedback)/.test(message.prompt);
    const outgoingPrompt=tracked?`HARNESS_REQUEST_ID ${message.id}\n\n${message.prompt}`:message.prompt;
    const submittedMatches=bubble=>{
      const actual=normalized(userMessageText(bubble)),expected=normalized(outgoingPrompt);
      // ChatGPT truncates long user-message renderers and renders JSON as
      // Markdown. The unique transport ID plus leading text identifies the turn;
      // the entire raw editor contents are checked separately before Send.
      // The rendered bubble can prepend controls or collapse even the leading
      // prose. Correlate its high-entropy request ID, after the complete editor
      // was verified before Send; never relax matching for ordinary user text.
      const marker='HARNESS_REQUEST_ID '+message.id;
      const full=normalized(messageText(bubble));
      const markerAt=full.indexOf(marker);
      const markerMatches=markerAt>=0&&(markerAt===0||/\s/.test(full[markerAt-1]))&&(full.length===markerAt+marker.length||/\s/.test(full[markerAt+marker.length]));
      return actual===expected||tracked&&(actual.startsWith(expected.slice(0,Math.min(240,expected.length)))||markerMatches);
    };
    const job = { id: message.id, attachments:message.attachments||[], cancelled: false, preset }; active = job;
    const start = Date.now();
    try {
      if(preset.accessRequired&&first(preset.accessRequired))throw new Error('Sign in on the paired website before retrying. No prompt was submitted.');
      let external = message.externalMessageId && globalThis.HarnessTwoWay?.take(message.externalMessageId);
      const saved=typeof sessionStorage!=='undefined'&&JSON.parse(sessionStorage.getItem('harness-job:'+message.id)||'null');
      let receipt=saved||{};
      const saveState=state=>{receipt={...receipt,...state,url:location.origin+location.pathname};if(typeof sessionStorage!=='undefined')sessionStorage.setItem('harness-job:'+message.id,JSON.stringify(receipt));};
      if(message.resume||saved){
        if(saved?.imageTransferPending)throw new Error('Image transfer was interrupted. Review saved artifacts before continuing; no generation or transfer was repeated.');
        if(saved?.turnKey)external={turnKey:saved.turnKey,baseline:new Set(),baselineImages:new Set(),baselineTurns:new Set()};
        else throw new Error('Interrupted submission outcome is uncertain. No prompt was resubmitted. Review the paired website before continuing.');
        if(message.site==='chatgpt-web'&&!message.externalMessageId){
          if(saved.url&&saved.url!==location.origin+location.pathname)throw new Error('Saved website turn belongs to another chat. No prompt was resubmitted.');
          let verified;
          while(!job.cancelled&&Date.now()-start<30000){
            const matches=[...document.querySelectorAll('[data-turn-key]')].filter(turn=>{
              const bubble=turn.querySelector('[data-user-message-bubble], [data-message-author-role="user"]');return !!bubble&&submittedMatches(bubble);
            });
            if(matches.length>1)throw new Error('Saved website turn is ambiguous. No prompt was resubmitted.');
            if(matches.length===1){verified=matches[0].getAttribute('data-turn-key');break;}
            await pageWait(job,500);
          }
          if(job.cancelled)return;
          if(!verified)throw new Error('Could not verify the saved website turn after reload. No prompt was resubmitted. Review the paired chat.');
          external.turnKey=verified;
        }
      }
      if (message.externalMessageId && !external) throw new Error('The originating ChatGPT message is no longer available. No prompt was resubmitted.');
      if (external && !external.turnKey) throw new Error('The originating ChatGPT turn could not be identified. Nothing was resubmitted.');
      const inTurn = node => {
        if(!external)return true;
        if(preset.correlation==='ordered-user-message'){
          const users=[...document.querySelectorAll(preset.users.join(','))];
          const user=users.findLast(submittedMatches);if(!user)return false;
          const following=users.find(candidate=>candidate!==user&&(user.compareDocumentPosition(candidate)&4));
          return !!(user.compareDocumentPosition(node)&4)&&!(following&&(following===node||following.compareDocumentPosition(node)&4));
        }
        return node.closest?.('[data-turn-key]')?.getAttribute('data-turn-key') === external.turnKey;
      };
      let composer;
      while (!external && !job.cancelled && Date.now() - start < 45000) {
        if(preset.accessRequired&&first(preset.accessRequired))throw new Error('Sign in on the paired website before retrying. No prompt was submitted.');
        composer = first(preset.composer);
        const accountLoading=message.site==='chatgpt-web'&&first(['button[aria-label="Open profile menu"][disabled]']);
        if (composer && !composer.disabled && composer.getAttribute('aria-disabled') !== 'true' && !accountLoading) break;
        await pageWait(job,500);
      }
      if (job.cancelled) return;
      if (!external && (!composer || composer.disabled || composer.getAttribute('aria-disabled')==='true' || message.site==='chatgpt-web'&&first(['button[aria-label="Open profile menu"][disabled]']))) throw new Error('The paired chat editor is not ready. Wait for the website to finish loading, or complete verification if requested, then retry. No prompt was sent.');
      if (!external && generationActive(preset)) throw new Error('Website is already generating. Nothing was sent.');
      const baseline = external?.baseline || new Set(responses(preset));
      const baselineImages = external?.baselineImages || new Set(generatedImages().map(image => image.currentSrc || image.src));
      const baselineTurns = external?.baselineTurns || new Set(document.querySelectorAll('[data-talvt-turn-state], article[data-testid^="conversation-turn-"]'));
      // This script runs only in a tab paired by the connector. User requested replacement of drafts there.
      if (!external) {
      const oldTurnKeys=new Set([...document.querySelectorAll('[data-turn-key]')].map(node=>node.getAttribute('data-turn-key')));
      if(message.attachments?.length)await globalThis.HarnessFiles.upload(job,sendEvent,ms=>pageWait(job,ms));
      globalThis.HarnessTwoWay?.suppressNext?.(outgoingPrompt);
      let retained=false;
      for(let attempt=0;attempt<3&&!job.cancelled;attempt++){
        composer=first(preset.composer);
        if(!composer||composer.disabled||composer.getAttribute('aria-disabled')==='true')break;
        fill(composer, outgoingPrompt);
        await pageWait(job,150);
        if(composer===first(preset.composer)&&normalized(editorText(composer))===normalized(outgoingPrompt)){retained=true;break;}
      }
      if(job.cancelled)return;
      if(!retained){
        const actual=normalized(editorText(composer)),expected=normalized(outgoingPrompt);let at=0;
        while(at<Math.min(actual.length,expected.length)&&actual[at]===expected[at])at++;
        throw new Error(`Website editor did not retain the intended prompt (expected ${expected.length} characters, found ${actual.length}; first difference ${at}; character codes ${expected.charCodeAt(at)||0}/${actual.charCodeAt(at)||0}). No message was submitted.`);
      }
      let send,emptyRemounts=0;
      for (let i = 0; i < 30 && !job.cancelled; i++) {
        composer=first(preset.composer);
        if(!composer)throw new Error('Website editor disappeared before submission. No message was submitted.');
        if(normalized(editorText(composer))!==normalized(outgoingPrompt)){
          // The new ChatGPT home composer creates a provisional conversation
          // and replaces its editor. Before the only Send click, recover an
          // emptied editor; never overwrite different user text or retry a send.
          if(message.site==='chatgpt-web'&&!editorText(composer).trim()&&!generationActive(preset)&&emptyRemounts++<3){fill(composer,outgoingPrompt);await pageWait(job,200);continue;}
          throw new Error('Website draft changed while waiting for Send. No message was submitted.');
        }
        send = firstInside(composer.closest?.('form')||document,preset.send);
        if (send && !disabled(send)) break;
        await pageWait(job,200);
      }
      if (job.cancelled) return;
      if (disabled(send)) throw new Error('Send control not recognized or disabled. Draft left visible; nothing was auto-submitted.');
      // ChatGPT can remount the composer while enabling Send. Verify its current
      // contents, rather than rejecting an equivalent replacement DOM node.
      composer=first(preset.composer);
      if(!composer||normalized(editorText(composer))!==normalized(outgoingPrompt))throw new Error('Website draft changed before submission. No message was submitted.');
      send=firstInside(composer.closest?.('form')||document,preset.send);
      if(disabled(send))throw new Error('Send control changed before submission. No message was submitted.');
      saveState({state:'submitting',at:Date.now()});
      if(globalThis.FridayDesktopSubmit)await globalThis.FridayDesktopSubmit(job.id,send);
      else send.click();
      if(preset.correlation==='ordered-user-message'){
        let matched=false;
        for(let i=0;i<200&&!job.cancelled;i++){
          if([...document.querySelectorAll(preset.users.join(','))].some(submittedMatches)){matched=true;break;}
          await pageWait(job,150);
        }
        if(job.cancelled)return;
        if(!matched)throw new Error('Website submission could not be identified. Nothing was resubmitted; inspect the paired chat.');
        const turnKey='provider:'+message.id;external={turnKey,baseline,baselineImages,baselineTurns};
        saveState({state:'submitted',turnKey,at:Date.now()});await sendEvent({id:job.id,type:'submitted',turnKey});
      }else if(typeof sessionStorage!=='undefined'){
        let turnKey;let matches=false;
        for(let i=0;i<200&&!job.cancelled;i++){
          globalThis.FridayTurns?.sync();
          const candidates=[...document.querySelectorAll('[data-turn-key]')].filter(node=>!oldTurnKeys.has(node.getAttribute('data-turn-key')));
          // Only website error UI, never the same words quoted in a user prompt.
          if(candidates.some(node=>[...(node.querySelectorAll?.('div, span, p, [role="alert"]')||[])].some(element=>
            !element.closest?.('[data-user-message-bubble], [data-message-author-role="user"]')&&
            /^Your account changed\. Send your message again$/i.test(normalized(element.innerText)))))throw new Error('Website reported: Your account changed. Refresh the paired ChatGPT page, then retry in Harness. Nothing was automatically resubmitted.');
          const turn=candidates.findLast(node=>{
            const bubble=node.querySelector('[data-user-message-bubble], [data-message-author-role="user"]');
            return !!bubble&&submittedMatches(bubble);
          });
          if(turn){
            turnKey=turn.getAttribute('data-turn-key');matches=true;break;
          }
          if(candidates.length)turnKey=candidates.at(-1).getAttribute('data-turn-key');
          await pageWait(job,150);
        }
        if(job.cancelled)return;
        if(!turnKey)throw new Error('Website submission could not be identified. Nothing was resubmitted; inspect the paired chat.');
        if(!matches)throw new Error('Website submitted message does not match the intended prompt. Nothing was resubmitted; inspect the paired chat.');
        saveState({state:'submitted',turnKey,at:Date.now()});
        await sendEvent({id:job.id,type:'submitted',turnKey});
        // Capture only this verified turn; newly remounted history and later
        // unrelated website messages cannot supply its answer.
        external={turnKey,baseline,baselineImages,baselineTurns};
      }else if(message.attachments?.length)await sendEvent({id:job.id,type:'submitted'});
      }
      else saveState({state:'submitted',turnKey:external.turnKey,at:Date.now()});
      let text = ''; let lastChange = Date.now(); let observedStop = false; let lastProgress = ''; let imageSeen = false;
      let loadingSince = null; let loadingPausedMs = 0; let loadingStatusAt = 0;
      const captured = new Set(saved?.capturedImages||[]); const progressQueue = []; let downloadsCollected=!!saved?.filesCollected||saved?.artifactPhase==='started';
      if(saved?.artifactPhase==='started'&&!saved.filesCollected)await sendEvent({id:job.id,type:'artifact-warning',message:'Download transfer was interrupted. Saved files were retained; automatic download was not repeated. Review the paired website for missing files.'});
      const observeProgress = () => {
        const progress = imageProgress(baselineTurns, imageSeen, external?.turnKey);
        const key = progress && JSON.stringify(progress);
        if (key && key !== lastProgress && progressQueue.length < 1000) { imageSeen = true; lastProgress = key; progressQueue.push(progress); }
      };
      const observer = typeof MutationObserver === 'function' ? new MutationObserver(observeProgress) : null;
      observer?.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['aria-valuenow'] });
      try { while (!job.cancelled && Date.now() - start - loadingPausedMs -
        (loadingSince === null ? 0 : Date.now() - loadingSince) < (imageSeen ? 900000 : Math.min(message.timeoutMs || 300000, 900000))) {
        const error = [...document.querySelectorAll(['[role="alert"]','[role="status"]',...(preset.errorNotices||[])].join(','))].filter(visible)
          .map(node => node.innerText || '').find(text => /your account changed|something went wrong|too many requests|too many people are chatting with kimi|reached.{0,30}limit|try again later/i.test(text));
        const stop = generationActive(preset); if (stop) observedStop = true;
        const nodes = responses(preset).filter(inTurn);
        const latest = nodes.findLast(node => !baseline.has(node));
        let next = latest ? responseText(latest) : '';
        // The website mounts its reasoning placeholder inside the same response
        // selector as the answer. It is status UI, including before tool calls.
        if(/^thinking(?:\s*[.…]*)?$/i.test(next)||message.purpose==='image'&&/^(?:creating image|generating image)(?:\s*[.…]*)?$/i.test(next))next='';
        const images = generatedImages().filter(image => inTurn(image) && !baselineImages.has(image.currentSrc || image.src));
        const placeholder = responseLoadPlaceholder(next);
        const recovered = !placeholder && (next || stop || images.some(image => image.complete && image.naturalWidth > 0));
        if (placeholder || (loadingSince !== null && !recovered)) {
          const firstWait = loadingSince === null;
          if (firstWait) loadingSince = Date.now();
          if (firstWait || Date.now() - loadingStatusAt >= 5000) {
            await sendEvent({ id: job.id, type: 'status', state: 'response-loading' }); loadingStatusAt = Date.now();
          }
          // Observe the SAME reply. Never regenerate, resubmit, or emit the placeholder as an answer.
          await pageWait(job,500); continue;
        }
        if (loadingSince !== null) {
          loadingPausedMs += Date.now() - loadingSince; loadingSince = null; lastChange = Date.now();
          await sendEvent({ id: job.id, type: 'status', state: 'receiving' });
        }
        if (error) {
          if(/too many people are chatting with kimi/i.test(error))throw new Error(`Kimi capacity limit: wait and retry later, or select another model in this same task. Paid priority access is optional; Kimi provided no retry time. Website notice: ${error.slice(0,250)}`);
          throw new Error(`Website reported: ${error.slice(0, 350)} Complete the website's recovery and retry in Harness.`);
        }
        observeProgress();
        for (const progress of progressQueue.splice(0)) {
          imageSeen = true; await sendEvent({ id: job.id, type: 'progress', ...progress });
        }
        for (const image of images) {
          const source = image.currentSrc || image.src;
          const turn = image.closest?.('[data-talvt-turn-state]');
          if (!captured.has(source) && image.complete && image.naturalWidth > 0 && (!turn || turn.getAttribute('data-talvt-turn-state') === 'complete')) {
            saveState({imageTransferPending:true});
            await transferImage(job, image); captured.add(source);saveState({imageTransferPending:false,capturedImages:[...captured]});imageSeen = true; lastChange = Date.now();
          }
        }
        if (next && next !== text) {
          text = next; lastChange = Date.now();
          await sendEvent({ id: job.id, type: 'snapshot', text });
        }
        // An idle DOM alone is not proof of completion. Require a visible
        // completion control or an observed generating -> stopped transition.
        const imageBusy = !!imageProgress(baselineTurns, imageSeen, external?.turnKey) || images.some(image => !captured.has(image.currentSrc || image.src));
        if ((text || captured.size) && !stop && !imageBusy && (!preset.completionMarker||latest&&firstInside(latest,preset.completionMarker)) && Date.now() - lastChange > 1800 &&
          (captured.size || (!imageSeen && (observedStop || completedResponse(preset, latest))) || completedResponse(preset, latest))) {
          const turn=latest?.closest?.('[data-turn-key]')||latest?.closest?.('article');
          if(globalThis.HarnessFiles&&!downloadsCollected){
            saveState({artifactPhase:'started'});
            for(const file of await globalThis.HarnessFiles.collectDownloads(turn,job.id,message=>sendEvent({id:job.id,type:'artifact-warning',message}),ms=>pageWait(job,ms)))await sendEvent({id:job.id,type:'file',fileId:file.id});
            downloadsCollected=true;saveState({filesCollected:true,artifactPhase:'complete'});
          }
          // Downloads can outlive the initial idle sample while the page finishes
          // rendering. Re-read this exact turn before committing the final reply.
          const settled=responses(preset).filter(inTurn).findLast(node=>!baseline.has(node));
          const settledText=settled?responseText(settled):text;
          if(settledText!==text){text=settledText;lastChange=Date.now();await sendEvent({id:job.id,type:'snapshot',text});continue;}
          if(stopControl(preset)){lastChange=Date.now();continue;}
          await sendEvent({ id: job.id, type: 'done', text });saveState({state:'complete',turnKey:external?.turnKey,at:Date.now()}); return;
        }
        await pageWait(job,500);
      } } finally { observer?.disconnect(); }
      if (!job.cancelled) {
        // Release only our verified latest provider turn on its normal timeout.
        // A human's later message must never have its generation stopped here.
        if(external&&preset.correlation==='ordered-user-message'){
          const latestUser=[...document.querySelectorAll(preset.users.join(','))].at(-1);
          if(latestUser&&submittedMatches(latestUser))stopControl(preset)?.click();
        }
        throw new Error('Could not confirm website completion. Check usage limits, verification, or changed website controls.');
      }
    } finally {
      for(const resolve of job.waiters||[])resolve({ok:true});
      if (active === job) active = null;
      if (message.externalMessageId) globalThis.HarnessTwoWay?.forget(message.externalMessageId);
    }
  }
  chrome.runtime.onMessage.addListener((message, _sender, respond) => {
    if(message.type==='harness-pulse'){
      if(active?.id!==message.id){
        let saved;try{saved=typeof sessionStorage!=='undefined'&&JSON.parse(sessionStorage.getItem('harness-job:'+message.id)||'null');}catch{}
        respond({ok:false,busy:!!active,resumeAvailable:!active&&document.readyState!=='loading'&&!!saved?.turnKey&&['submitted','complete'].includes(saved.state),url:location.origin+location.pathname});return;
      }
      active.wake?.();respond({ok:true});return;
    }
    if (message.type === 'harness-connection-notice') {
      const preset = presets['chatgpt-web']; const composer = first(preset.composer);
      if (location.origin + location.pathname !== message.url || location.hostname !== 'chatgpt.com' || active ||
        stopControl(preset) || !composer || composer.disabled || (composer.value || composer.innerText || '').trim()) {
        respond({ sent: false }); return;
      }
      // A local connection notice is a programmatic send, never a new human task.
      const notice = message.online
        ? 'Harness connection status: Harness is online again. New local tasks can use the supplied Harness tools. Do not repeat any earlier action automatically; wait for a new request or confirmed tool result. Reply briefly.'
        : 'Harness connection status: Harness is OFFLINE. Local tools cannot execute and no tool success can be confirmed until it reconnects. Do not request local tools or claim local actions completed. Wait for a connection-restored notice or a new confirmed Harness request. Reply briefly.';
      try {
        globalThis.HarnessTwoWay?.suppressNext?.(notice);
        fill(composer, notice);
        (async () => {
          for (let i = 0; i < 20; i++) {
            const button = first(preset.send);
            if (button && !button.disabled) { button.click(); respond({ sent: true }); return; }
            await sleep(100);
          }
          if ((composer.value || composer.innerText || '').trim() === notice) fill(composer, '');
          respond({ sent: false });
        })().catch(() => respond({ sent: false }));
      } catch { respond({ sent: false }); }
      return true;
    }
    if (message.type === 'harness-listen') { globalThis.HarnessTwoWay?.configure(message.config); respond({ ok: true }); return; }
    if (message.type === 'harness-ping') {
      const preset = Object.values(presets).find(p => p.hosts.includes(location.hostname));
      const composer = preset && first(preset.composer);
      respond({ ok: true, url: location.href, readyState: document.readyState,
        provider: Object.entries(presets).find(([,p])=>p===preset)?.[0],adapterRevision:1,
        hasEditor: !!composer && !composer.disabled && composer.getAttribute('aria-disabled') !== 'true' && !(preset.accessRequired&&first(preset.accessRequired)),
        isGenerating: !!preset && !!generationActive(preset),
        hasDraft: !!(composer?.value || composer?.innerText || '').trim(),
        responseCharacters: preset ? responses(preset).reduce((n, node) => n + (node.innerText || '').length, 0) : 0 });
      return;
    }
    if (message.type === 'harness-cancel') {
      if (active?.id === message.id) { active.cancelled = true; active.wake?.(true);stopControl(active.preset)?.click(); }
      respond({ ok: true }); return;
    }
    if (message.type !== 'harness-run') return;
    if(message.streamEvents){
      // The stream has its own acknowledged event channel. Never hold a Chrome
      // response port open for a multi-minute model generation.
      if(active?.id===message.id){respond({ok:true,started:true});return;}
      respond({ok:true,started:true});
      void run(message).catch(async error=>{await sendEvent({id:message.id,type:'error',message:error.message}).catch(()=>{});});
      return;
    }
    if(active?.id===message.id){(active.waiters||=[]).push(respond);return true;}
    run(message).then(() => respond({ ok: true })).catch(async error => {
      await sendEvent({ id: message.id, type: 'error', message: error.message }).catch(() => {});
      respond({ ok: false, error: error.message });
    });
    return true;
  });
  if (location.hostname === 'chatgpt.com' && globalThis.HarnessTwoWay && document.addEventListener) {
    globalThis.HarnessFiles?.init();
    const preset = presets['chatgpt-web'];
    globalThis.HarnessTwoWay.init({ composer: () => first(preset.composer), responses: () => responses(preset), images: generatedImages,
      progressTurns: () => [...document.querySelectorAll('[data-talvt-turn-state], article[data-testid^="conversation-turn-"]')],
      sendSelectors: preset.send, stopWebsite: () => stopControl(preset)?.click(),
      cancelActive: () => { if (!active) return false; const id = active.id; active.cancelled = true; active.wake?.(true); active = null; return id; } });
  }
})();
