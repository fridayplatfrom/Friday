import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const {yaml}=createRequire(import.meta.url)('playwright-core/lib/utilsBundle');

/** Migrate only the existing browser plugin/provider. Never add a second browser. */
export function sharedBrowserProfile(profile,entry,profileDir){
 let next=profile;
 if(!/browserMode: (extension|builtin|shared)\b/.test(next))throw new Error('Existing Friday browser transport not found.');
 next=next.replace(/browserMode: (extension|builtin|shared)\b/,'browserMode: shared');
 const match=/^([ \t]*)- id: harness-playwright\s*\r?\n/m.exec(next);if(!match)throw new Error('Existing native Harness browser plugin not found; no browser added.');
 const tail=next.slice(match.index+match[0].length),boundary=[...tail.matchAll(/^([ \t]*)(?:- (?:id:|insert:)|# END)/gm)].find(hit=>hit[1].length<=match[1].length);
 const end=boundary?match.index+match[0].length+boundary.index:next.length;
 let block=next.slice(match.index,end);
 const document=yaml.parseDocument(block);if(document.errors.length)throw new Error('Existing native browser YAML needs review.');
 const argsNode=document.getIn([0,'config','args'],true),values=argsNode?.toJSON();if(!Array.isArray(values)||values.some(value=>typeof value!=='string')||!argsNode.range)throw new Error('Custom native browser arguments need review.');
 if(!values[0]?.replaceAll('\\','/').endsWith('/@playwright/mcp/cli.js')&&!values[0]?.replaceAll('\\','/').endsWith('/shared-browser-mcp.mjs'))throw new Error('Unexpected existing browser backend; nothing migrated.');
 const allowed=new Set(['--executable-path','--allowed-origins','--image-responses','--user-data-dir']);
 const result=[entry];for(let i=1;i<values.length;i++){if(values[i]==='--isolated')continue;if(!allowed.has(values[i])||i+1>=values.length)throw new Error('Unsupported custom browser option; nothing migrated.');const key=values[i++],value=values[i];if(key!=='--user-data-dir')result.push(key,value);}
 if(!result.includes('--executable-path')||!result.includes('--allowed-origins'))throw new Error('Native executable/origin policy is required.');
 result.push('--user-data-dir',profileDir);
 block=block.slice(0,argsNode.range[0])+JSON.stringify(result)+block.slice(argsNode.range[1]);
 return next.slice(0,match.index)+block+next.slice(end);
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))process.stdout.write(sharedBrowserProfile(readFileSync(0,'utf8'),process.argv[2],process.argv[3]));
