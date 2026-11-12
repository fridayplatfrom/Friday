import {readFileSync} from 'node:fs';
// One stylesheet for the normal web interface and the desktop host.
export const fridayCSS=()=>readFileSync(new URL('./friday.css',import.meta.url),'utf8');
export function fridayThemeScript(){
  return '(()=>{let s=document.getElementById("friday-theme");if(!s){s=document.createElement("style");s.id="friday-theme";document.head.append(s);}s.textContent='+JSON.stringify(fridayCSS()).replaceAll("<", "\\u003c")+';})();'+readFileSync(new URL('./boot-branding.js',import.meta.url),'utf8');
}
