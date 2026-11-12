// Styles only the trusted Harness webContents; provider pages are never touched.
export function fridayTheme({webContents,css,allowed,enabled=true,onError=()=>{},onChange=()=>{}}) {
  let key=null, pending=Promise.resolve();
  const apply=()=>{
    pending=pending.catch(()=>{}).then(async()=>{
      if(webContents.isDestroyed())return;
      if(key){try{await webContents.removeInsertedCSS(key);}catch{}key=null;}
      if(enabled&&allowed(webContents.getURL()))key=await webContents.insertCSS(typeof css==='function'?css():css,{cssOrigin:'user'});
    }).catch(onError);
    return pending;
  };
  webContents.on('did-start-navigation',(_event,_url,inPlace,main)=>{if(main&&!inPlace)key=null;});
  webContents.on('did-finish-load',()=>void apply());
  return {apply,set(value){enabled=!!value;onChange(enabled);return apply();},get enabled(){return enabled;}};
}
