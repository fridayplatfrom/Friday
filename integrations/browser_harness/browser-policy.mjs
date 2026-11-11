import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export const DEFAULT_TASK_ORIGINS=Object.freeze(['http://127.0.0.1:8767','http://127.0.0.1:8010','https://images.unsplash.com','https://fonts.googleapis.com','https://fonts.gstatic.com']);
export function taskOrigins(values){
  if(!Array.isArray(values)||!values.length||values.length>100)throw new Error('Provide 1–100 explicit task website origins.');
  return [...new Set(values.map(value=>{
    let url;try{url=new URL(value);}catch{throw new Error('Task browser origins must be explicit HTTP(S) origins.');}
    if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.pathname!=='/'||url.search||url.hash||url.hostname.includes('*'))throw new Error('Task browser origins cannot contain credentials, wildcards, paths, queries or fragments.');
    return url.origin;
  }))];
}

/** Patch only the existing native browser plugin; retain its engine, mode and other config. */
export function patchTaskBrowser(profile,additions=DEFAULT_TASK_ORIGINS){
  const match=/^([ \t]*)- id: harness-playwright[ \t]*\r?\n/m.exec(profile);
  if(!match)throw new Error('Existing Harness browser plugin not found. No browser was added.');
  const start=match.index,tail=profile.slice(start+match[0].length);
  const next=[...tail.matchAll(/^([ \t]*)(?:- (?:id:|insert:)|# END)/gm)].find(candidate=>candidate[1].length<=match[1].length);
  const end=next?start+match[0].length+next.index:profile.length;
  const block=profile.slice(start,end);
  const option=/(['"])--allowed-origins\1\s*,\s*(['"])([^'"\r\n]*)\2/.exec(block);
  if(!option)throw new Error('Expected native browser origin option was not found; preserve custom config for explicit review.');
  const origins=taskOrigins([...option[3].split(';').filter(Boolean),...additions]);
  const replacement=option[0].replace(option[2]+option[3]+option[2],JSON.stringify(origins.join(';')));
  const patched=block.slice(0,option.index)+replacement+block.slice(option.index+option[0].length);
  return {profile:profile.slice(0,start)+patched+profile.slice(end),origins};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const input=readFileSync(0,'utf8');
  if(process.argv[2]==='origins')process.stdout.write(taskOrigins(process.argv.slice(3)).join(';'));
  else process.stdout.write(patchTaskBrowser(input,process.argv.slice(2).length?process.argv.slice(2):DEFAULT_TASK_ORIGINS).profile);
}
