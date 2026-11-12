import {readFileSync,writeFileSync} from 'node:fs';
// Embed the tested adapter in the existing client bundle: no extra startup fetch.
const file=new URL('./client.js',import.meta.url);
const source=readFileSync(new URL('./layout-preferences.mjs',import.meta.url),'utf8').replaceAll('export function ','function ');
const client=readFileSync(file,'utf8');
const start=client.indexOf('    // BEGIN GENERATED LAYOUT PREFERENCES'),end=client.indexOf('    // END GENERATED LAYOUT PREFERENCES',start);
if(start<0||end<0)throw Error('Missing client layout markers');
const next=client.slice(0,start)+'    // BEGIN GENERATED LAYOUT PREFERENCES\n'+source+'\n'+client.slice(end);
if(process.argv.includes('--check')){if(next!==client)throw Error('Run node build-layout-client.mjs');}else writeFileSync(file,next);
