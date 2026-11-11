(() => {
 if(location.hostname!=='chatgpt.com')return;
 // Some ChatGPT layouts expose separate message articles without a turn key.
 // Group each verified user article and following assistant articles under a
 // stable local key. Never replace a website-supplied conversation grouping.
 function sync(){
  let current=null;
  for(const article of document.querySelectorAll('article[data-testid^="conversation-turn-"]')){
   const user=article.querySelector('[data-message-author-role="user"], [data-user-message-bubble="true"]');
   const existing=article.closest('[data-turn-key]');
   const derived=existing===article&&article.getAttribute('data-friday-derived-turn')==='true';
   if(user){
    if(existing&&!derived)current=existing.getAttribute('data-turn-key');
    else{
     const request=String(user.textContent||'').trim().match(/^HARNESS_REQUEST_ID\s+([a-f0-9-]{36})(?:\s|$)/i)?.[1];
     const identity=request||user.getAttribute('data-message-id')||user.querySelector('[data-message-id]')?.getAttribute('data-message-id')||article.getAttribute('data-testid');
     current=identity?'friday-turn:'+identity:null;
    }
   }
   if(current&&(!existing||derived)){
    article.setAttribute('data-friday-derived-turn','true');article.setAttribute('data-turn-key',current);
   }
  }
 }
 globalThis.FridayTurns={sync};sync();
 let scheduled=false;
 new MutationObserver(()=>{if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;sync();});}).observe(document.body,{childList:true,subtree:true,characterData:true});
})();
