import {readFileSync,writeFileSync} from 'node:fs';
import {PROVIDERS} from './providers.mjs';
// Standalone content entry remains usable if an older manifest did not load
// the new catalog script. Both copies are generated from the same contract.
const path=new URL('./extension/content.js',import.meta.url),source=readFileSync(path,'utf8');
const selectors=Object.fromEntries(Object.entries(PROVIDERS).map(([id,p])=>[id,p.selectors]));
const block='  // BEGIN FRIDAY GENERATED PRESETS\n  const presets = globalThis.FridayProviderCatalog ? Object.fromEntries(Object.entries(globalThis.FridayProviderCatalog).map(([id,p])=>[id,p.selectors])) : '+JSON.stringify(selectors)+';\n  // END FRIDAY GENERATED PRESETS';
if(!source.includes('// BEGIN FRIDAY GENERATED PRESETS'))throw new Error('Content contract build marker missing.');
writeFileSync(path,source.replace(/  \/\/ BEGIN FRIDAY GENERATED PRESETS[\s\S]*?  \/\/ END FRIDAY GENERATED PRESETS/,block));
