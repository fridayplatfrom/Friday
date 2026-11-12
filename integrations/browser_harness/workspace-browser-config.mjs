import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const {yaml}=createRequire(import.meta.url)('playwright-core/lib/utilsBundle');
export function workspaceBrowserProfile(profile,entry){
 const match=/^([ \t]*)- id: harness-playwright\s*\r?\n/m.exec(profile);if(!match)throw new Error('Existing native browser plugin not found.');
 const tail=profile.slice(match.index+match[0].length),boundary=[...tail.matchAll(/^([ \t]*)(?:- (?:id:|insert:)|# END)/gm)].find(hit=>hit[1].length<=match[1].length);
 const end=boundary?match.index+match[0].length+boundary.index:profile.length;
 let block=profile.slice(match.index,end);const document=yaml.parseDocument(block);
 if(document.errors.length)throw new Error('Browser configuration needs review.');
 const node=document.getIn([0,'config','args'],true),values=node?.toJSON();
 if(!Array.isArray(values)||!node.range||!values[0]?.replaceAll('\\','/').match(/\/(?:@playwright\/mcp\/cli\.js|workspace-browser-mcp\.mjs)$/))throw new Error('Unsupported browser configuration.');
 const result=[entry];for(let i=1;i<values.length;i++){if(values[i]==='--isolated')continue;if(!['--executable-path','--allowed-origins','--image-responses','--public-web'].includes(values[i])||!values[i+1])throw new Error('Custom browser option requires review.');result.push(values[i],values[++i]);}
 if(!result.includes('--allowed-origins')||!result.includes('--executable-path'))throw new Error('Retain the existing browser executable and origin policy.');
 block=block.slice(0,node.range[0])+JSON.stringify(result)+block.slice(node.range[1]);
 let next=profile.slice(0,match.index)+block+profile.slice(end);
 if(!/workspaceBrowser: true/.test(next))next=next.replace(/(browserMode: extension\b)/,'$1\n        workspaceBrowser: true');
 if(!/workspaceBrowser: true/.test(next))throw new Error('Existing extension transport is required.');
 return next;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))process.stdout.write(workspaceBrowserProfile(readFileSync(0,'utf8'),process.argv[2]));
