/** Keep the native API settings implementation, but give Models one visible entry. */
export function hideModelsSettingsNavigation({document,slots,observe=callback=>new MutationObserver(callback)}){
 const hidden=new Map();let openRequested=false,timer;
 const update=()=>{
  const entry=slots.entries?.('settings.section')?.find(entry=>entry.options.id==='models');
  const value=entry?.options.label;const label=typeof value==='function'?value():value||'Models';
  for(const button of document.querySelectorAll('[data-shortcut-modal="settings"] nav button')){
   if(button.textContent.trim()!==label)continue;
   if(!hidden.has(button))hidden.set(button,{display:button.style.getPropertyValue('display'),priority:button.style.getPropertyPriority('display'),aria:button.getAttribute('aria-hidden')});
   button.style.setProperty('display','none','important');button.setAttribute('aria-hidden','true');
   if(openRequested){openRequested=false;clearTimeout(timer);button.click();}
  }
 };
 // Older Harness builds open Settings without honoring a section argument.
 // Its existing Models row remains the native navigation action for Advanced.
 const open=()=>{openRequested=true;clearTimeout(timer);timer=setTimeout(()=>{openRequested=false;},2000);update();};
 document.addEventListener('friday-open-api-models',open);
 const observer=observe(update);observer.observe(document.body,{childList:true,subtree:true,characterData:true});update();
 return()=>{observer.disconnect();clearTimeout(timer);document.removeEventListener('friday-open-api-models',open);for(const [button,old]of hidden){if(old.display)button.style.setProperty('display',old.display,old.priority);else button.style.removeProperty('display');if(old.aria===null)button.removeAttribute('aria-hidden');else button.setAttribute('aria-hidden',old.aria);}};
}
