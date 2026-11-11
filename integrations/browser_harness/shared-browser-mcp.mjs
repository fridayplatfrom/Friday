import {createConnection} from '@playwright/mcp';
import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
import {readFile,mkdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {homedir} from 'node:os';
import {protectedTaskContext,isModelURL} from './protected-browser.mjs';
import {SharedBrowserWorker} from './shared-browser-worker.mjs';
import {taskOrigins} from './browser-policy.mjs';

// The existing Harness MCP plugin still owns the sole browser process/context.
// Public upstream createConnection keeps the native MCP tool schemas/behavior.
const args=process.argv.slice(2),option=name=>{const at=args.indexOf(name);return at<0?undefined:args[at+1];};
for(let i=0;i<args.length;i+=2)if(!['--executable-path','--allowed-origins','--user-data-dir','--image-responses'].includes(args[i])||!args[i+1])throw new Error('Unexpected shared browser option; existing configuration needs review.');
const directory=join(homedir(),'.dsh','browser-connector');
const profile=resolve(option('--user-data-dir')||join(directory,'friday-browser-profile'));
if(profile!==resolve(join(directory,'friday-browser-profile')))throw new Error('Friday requires its dedicated browser profile; personal Chrome profiles are never opened.');
const connection=JSON.parse(await readFile(join(directory,'connection.json'),'utf8'));
await mkdir(profile,{recursive:true});
const context=await chromium.launchPersistentContext(profile,{executablePath:option('--executable-path'),headless:false,viewport:null,chromiumSandbox:true,acceptDownloads:true});
const protectedPages=new Set();
context.on('page',page=>{if(protectedPages.creatingModel)protectedPages.add(page);});
// Block task tabs from taking over provider pages, regardless of future allowlist additions.
await context.route('**',route=>{const request=route.request();let page;try{page=request.frame().page();}catch{return route.fallback();}return !protectedPages.has(page)&&request.isNavigationRequest()&&isModelURL(request.url())?route.abort('blockedbyclient'):route.fallback();});
const worker=new SharedBrowserWorker(context,{directory,connection,protectedPages});
await worker.start();
const server=await createConnection({browser:{isolated:false},imageResponses:option('--image-responses')||'omit',network:{allowedOrigins:taskOrigins((option('--allowed-origins')||'').split(';'))}},()=>Promise.resolve(protectedTaskContext(context,protectedPages)));
const {StdioServerTransport}=createRequire(import.meta.url)('playwright-core/lib/utilsBundle');
let closing=false;
async function shutdown(){if(closing)return;closing=true;worker.stop();await server.close().catch(()=>{});await context.close().catch(()=>{});}
context.on('close',()=>{worker.stop();void server.close();});
process.on('SIGINT',()=>void shutdown().finally(()=>process.exit(0)));
process.on('SIGTERM',()=>void shutdown().finally(()=>process.exit(0)));
process.stdin.on('end',()=>void shutdown().finally(()=>process.exit(0)));
await server.connect(new StdioServerTransport());
