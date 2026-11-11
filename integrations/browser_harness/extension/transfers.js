(() => {
  const CHUNK=384*1024,MAX=32*1024*1024;
  const extensions=new Set('png jpg jpeg webp txt md csv json pdf html css js mjs ts tsx jsx py yaml yml xml svg docx xlsx pptx zip mp3 wav m4a mp4 webm'.split(' '));
  const pendingKey='harness-pending-files:'+location.pathname;
  let pendingFiles=[];try{pendingFiles=JSON.parse(sessionStorage.getItem(pendingKey)||'[]');}catch{}
  const persistPending=()=>sessionStorage.setItem(pendingKey,JSON.stringify(pendingFiles));
  let selection=Promise.resolve();
  const hash=async bytes=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  function base64(bytes){let text='';for(const n of bytes)text+=String.fromCharCode(n);return btoa(text);}
  function confirmedNames(files,chips){
    const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const texts=chips.map(node=>node.innerText+' '+node.getAttribute('aria-label')+' '+node.getAttribute('title'));
    const choices=files.map(file=>{
      const dot=file.name.lastIndexOf('.');const stem=dot<0?file.name:file.name.slice(0,dot),ext=dot<0?'':file.name.slice(dot);
      const pattern=new RegExp('(?:^|\\s)('+escape(stem)+'(?: ?\\(\\d+\\))?'+escape(ext)+')(?=$|\\s)','gu');
      return [...new Set(texts.flatMap(text=>[...text.matchAll(pattern)].map(match=>match[1])))];
    }).sort((a,b)=>a.length-b.length);
    const assign=(index,used)=>index===choices.length||choices[index].some(name=>{
      if(used.has(name))return false;used.add(name);const found=assign(index+1,used);used.delete(name);return found;
    });
    return assign(0,new Set());
  }
  async function call(action,input,jobId){const result=await chrome.runtime.sendMessage({type:'harness-file-transfer',action,input,jobId});if(!result?.ok)throw new Error(result?.error||'File bridge unavailable');return result.result;}
  async function save(file,jobId){
    if(file.size>MAX||!extensions.has(file.name.split('.').at(-1).toLowerCase()))throw new Error(`Unsupported file or exceeds 32 MB: ${file.name}`);
    const bytes=new Uint8Array(await file.arrayBuffer());const sha256=await hash(bytes);
    const key=`harness-file:${location.pathname}:${sha256}:${file.name}`;let id=sessionStorage.getItem(key);if(!id){id=crypto.randomUUID();sessionStorage.setItem(key,id);}
    const record=await call('begin',{id,name:file.name,size:file.size,sha256},jobId);
    for(let index=record.next,offset=index*CHUNK;offset<bytes.length;index++,offset+=CHUNK){
      await call('chunk',{id,index,data:base64(bytes.subarray(offset,offset+CHUNK))},jobId);
      globalThis.HarnessTwoWay?.notify(`Transferring ${file.name} · ${Math.min(100,Math.round((offset+CHUNK)/Math.max(1,bytes.length)*100))}%`);
    }
    return call('finish',{id},jobId);
  }
  async function upload(job,sendEvent,sleep){
    if(!job.attachments?.length)return;
    await sendEvent({id:job.id,type:'status',state:'uploading'});
    const supports=input=>{
      const accept=(input.getAttribute?.('accept')||'').split(',').map(value=>value.trim().toLowerCase()).filter(Boolean);
      return !accept.length||job.attachments.every(file=>accept.some(type=>type==='.'+file.name.split('.').at(-1).toLowerCase()||type===file.mime||type.endsWith('/*')&&file.mime.startsWith(type.slice(0,-1))));
    };
    const picker=()=>{
      // ChatGPT retains hidden home-page forms after entering a conversation.
      // Only the form owning the visible editor can confirm this upload.
      let form;
      for(const selector of job.preset?.composer||[]){
        const editor=[...document.querySelectorAll(selector)].find(node=>node.getClientRects().length&&getComputedStyle(node).visibility!=='hidden');
        if(editor){form=editor.closest('form');break;}
      }
      const root=form||document;
      const inputs=[...root.querySelectorAll('input[type="file"]')];
      return inputs.find(supports)||(!inputs.length?root.querySelector('input[type="file"]'):null);
    };
    let input=picker();
    if(!input){document.querySelector('button[aria-label="Add files and more"]')?.click();await sleep(300);input=picker();}
    if(!input)throw new Error('Website file picker unavailable. Files remain saved in Harness; upload them manually in the paired tab.');
    if(input.files?.length)throw new Error('Website already has attached files. Review or remove those before uploading Harness files.');
    const chipSelector='[data-testid*="attachment"], [data-testid*="file"], [aria-label*="Remove"], [aria-label*="file"]';
    const surface=input.closest?.('form')||document;
    const before=new Map([...surface.querySelectorAll(chipSelector)].map(node=>[node,node.innerText+' '+node.getAttribute('aria-label')+' '+node.getAttribute('title')]));
    const data=new DataTransfer();
    for(const file of job.attachments){const parts=[];for(let index=0;index<file.next;index++){
      const result=await chrome.runtime.sendMessage({type:'harness-job-file',jobId:job.id,id:file.id,index});if(!result?.ok)throw new Error(result?.error||'Attachment download interrupted');
      parts.push(Uint8Array.from(atob(result.result.data),c=>c.charCodeAt(0)));
    }const blob=new Blob(parts,{type:file.mime});if(await hash(await blob.arrayBuffer())!==file.sha256)throw new Error('Attachment integrity mismatch; nothing submitted.');data.items.add(new File([blob],file.name,{type:file.mime}));}
    input.files=data.files;input.dispatchEvent(new Event('change',{bubbles:true}));
    // Wait for a visible attachment chip per filename and for processing indicators to disappear.
    for(let attempt=0;attempt<180;attempt++){
      if(job.cancelled)throw new Error('Attachment upload cancelled.');
      const chips=[...surface.querySelectorAll(chipSelector)].filter(node=>before.get(node)!==node.innerText+' '+node.getAttribute('aria-label')+' '+node.getAttribute('title'));
      const accepted=confirmedNames(job.attachments,chips);
      const processing=[...surface.querySelectorAll('[role="progressbar"], [aria-label*="Uploading"], [aria-label*="Processing"], [aria-busy="true"]')].some(node=>node.getClientRects().length);
      const failed=chips.some(node=>/upload failed|unable to upload|unsupported file|couldn.t upload/i.test(node.innerText));
      if(failed)throw new Error('Website rejected an attachment. Review the paired tab; no prompt was submitted.');
      if(accepted&&!processing){await sleep(700);return;}
      await sleep(500);
    }
    throw new Error('Website did not confirm attachment processing. Review the paired tab; no prompt was submitted.');
  }
  async function buttonDownload(button,name){
    if(typeof MutationObserver!=='function')throw new Error('Download button capture unavailable');
    return new Promise((resolve,reject)=>{
      let timer;let observer;
      const finish=(error,value)=>{clearTimeout(timer);observer?.disconnect();document.removeEventListener('click',clicked,true);error?reject(error):resolve(value);};
      const inspect=anchor=>{if(!anchor?.href)return;const url=new URL(anchor.href,location.href);
        if(url.protocol==='blob:'||url.protocol==='https:'&&url.origin===location.origin)finish(null,{href:anchor.href,name:anchor.getAttribute('download')||name});};
      const clicked=event=>inspect(event.target?.closest?.('a[href]'));
      observer=new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes||[]){if(node.matches?.('a[href]'))inspect(node);for(const anchor of node.querySelectorAll?.('a[href]')||[])inspect(anchor);}});
      document.addEventListener('click',clicked,true);observer.observe(document.documentElement||document.body,{childList:true,subtree:true});
      timer=setTimeout(()=>finish(new Error('The website download button did not expose a readable file URL')),10000);
      try{button.click();}catch(error){finish(error);}
    });
  }
  async function collectDownloads(turn,jobId,warn=()=>{},wait=ms=>new Promise(resolve=>setTimeout(resolve,ms))){const files=[];if(!turn)return files;
    const candidates=[...turn.querySelectorAll('a[download], a[href^="blob:"], a[href*="/backend-api/files/"]')];
    if(!candidates.length)for(const button of turn.querySelectorAll('button[aria-label="Download file"]')){
      if(!button.getClientRects().length||button.disabled)continue;
      let name;
      for(let parent=button.parentElement;parent;parent=parent.parentElement){
        const previews=[...parent.querySelectorAll('button[aria-label^="Open preview of "]')];
        if(previews.length===1){name=previews[0].getAttribute('aria-label').slice('Open preview of '.length);break;}
        if(parent===turn)break;
      }
      if(!name||!extensions.has(name.split('.').at(-1).toLowerCase())){await warn('Website download button has no recognized filename. Use its Download control manually.');continue;}
      try{
        let watch;
        for(let attempt=0;attempt<240;attempt++){
          watch=await chrome.runtime.sendMessage({type:'harness-download-watch',jobId,name});
          if(!watch?.busy)break;
          // Another paired tab on this origin owns Chrome's unattributable
          // download stream. Wait before clicking, not after starting a file.
          if(attempt===0)await warn('Waiting for the other paired chat to finish its download transfer.');
          await wait(500);
        }
        if(watch?.busy)throw new Error('Another paired chat still owns the download transfer');
        if(watch?.ok===false)throw new Error(watch.error||'Download job is no longer active');
        if(watch?.ok&&watch.available){button.click();const result=await chrome.runtime.sendMessage({type:'harness-download-result',jobId,watchId:watch.watchId});
          if(!result?.ok)throw new Error(result?.error||'Browser download transfer failed');files.push(result.file);continue;}
      }catch(error){await warn(`${name}: ${error.message}. Use the website Download control manually.`);continue;}
      try{const asset=await buttonDownload(button,name);candidates.push({href:asset.href,innerText:asset.name,getAttribute:()=>asset.name});}
      catch(error){await warn(`${name}: ${error.message}. Use the website Download control manually.`);}
    }
    for(const link of candidates){
      const href=link.href;const url=new URL(href,location.href);
      if(!['blob:','https:'].includes(url.protocol)||url.protocol==='https:'&&url.origin!==location.origin){await warn('A website download is not readable by this connector. Use its Download control manually.');continue;}
      // Fetch only the URL of a visible website-provided download, never guess an endpoint.
      const name=link.getAttribute('download')||link.innerText.trim().replace(/^Download\s+/i,'');
      if(!extensions.has(name.split('.').at(-1).toLowerCase())){await warn('A generated download has an unsupported or unrecognized filename. Download it manually from the paired website.');continue;}
      try{const response=await fetch(href);if(!response.ok)throw new Error('Download unavailable');const length=Number(response.headers.get('content-length'));if(length>MAX)throw new Error('Download exceeds 32 MB');const blob=await response.blob();files.push(await save(new File([blob],name,{type:blob.type}),jobId));}
      catch(error){await warn(`${name}: ${error.message}. Use the website Download control manually.`);}
    }return files;
  }
  function init(){
    const selected=files=>{if(!files.length)return;selection=selection.catch(()=>{}).then(async()=>{
      const selected=[];for(const file of files)selected.push(await save(file));for(const file of selected)if(!pendingFiles.some(item=>item.id===file.id))pendingFiles.push(file);persistPending();
    });selection.catch(error=>globalThis.HarnessTwoWay?.notify(`File transfer failed: ${error.message}. Keep the original file and retry.`));
    };
    document.addEventListener('change',event=>{if(event.isTrusted&&event.target?.type==='file')selected([...event.target.files||[]]);},true);
    document.addEventListener('paste',event=>{if(event.isTrusted)selected([...event.clipboardData?.files||[]]);},true);
    document.addEventListener('drop',event=>{if(event.isTrusted)selected([...event.dataTransfer?.files||[]]);},true);
  }
  globalThis.HarnessFiles={upload,collectDownloads,init,save,async take(){await selection;const files=pendingFiles;pendingFiles=[];persistPending();return files.map(file=>file.id);}};
})();
