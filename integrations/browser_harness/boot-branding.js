// Runs before client plugins. Only the native boot wordmark and hint are changed.
(()=>{
  if(typeof document.querySelector!=='function')return;
  let observer;
  const brand=()=>{
    const boot=document.querySelector('[data-dsh-boot]');if(!boot)return false;
    const mark=boot.querySelector('[class*="_wordmark_"]');if(!mark)return false;
    const logo=document.createElement('img');logo.src='/browser-models/brand/friday.png';logo.alt='Friday';logo.width=180;logo.height=60;logo.style.cssText='display:block;object-fit:cover';
    mark.replaceChildren(logo);mark.setAttribute('aria-label','Friday');
    const hint=boot.querySelector('[class*="_hint_"]');if(hint){hint.hidden=true;hint.textContent='';}
    observer?.disconnect();return true;
  };
  if(!brand()&&typeof MutationObserver==='function'){observer=new MutationObserver(brand);observer.observe(document.documentElement,{childList:true,subtree:true});setTimeout(()=>observer.disconnect(),120000);}
})();
