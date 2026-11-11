import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
import {randomBytes} from 'node:crypto';
import {workspaceControlServer} from './workspace-browser-http.mjs';
import {mkdirSync,writeFileSync,renameSync,unlinkSync,readFileSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {homedir} from 'node:os';
import {WorkspaceBrowserManager} from './workspace-browser-manager.mjs';
import {upstreamConnection} from './workspace-browser-upstream.mjs';
import {controlFile} from './workspace-browser-control.mjs';
import {taskOrigins} from './browser-policy.mjs';
const sdk=createRequire(import.meta.url)('playwright-core/lib/utilsBundle');
const args=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){if(!['--executable-path','--allowed-origins','--image-responses'].includes(args[i])||!args[i+1])throw new Error('Unsupported workspace browser option.');options[args[i]]=args[i+1];}
const origins=taskOrigins((options['--allowed-origins']||'').split(';'));
const configuration={browser:{isolated:false},imageResponses:options['--image-responses']||'allow',network:{allowedOrigins:origins}};
const root=join(homedir(),'.dsh','browser-connector','workspaces');
const manager=new WorkspaceBrowserManager({root,origins,
 launch:profile=>chromium.launchPersistentContext(profile,{executablePath:options['--executable-path'],headless:false,viewport:null,chromiumSandbox:true,acceptDownloads:true}),
 upstream:(factory,directory)=>upstreamConnection(factory,configuration,directory)});
const discovery=await upstreamConnection(()=>{throw new Error('Discovery cannot launch a browser.');},configuration);
const tools=await discovery.listTools();await discovery.close();
const token=randomBytes(32).toString('hex');
const control=workspaceControlServer(manager,token);
await new Promise(resolve=>control.listen(0,'127.0.0.1',resolve));
mkdirSync(dirname(controlFile),{recursive:true});writeFileSync(controlFile+'.tmp',JSON.stringify({protocolVersion:1,port:control.address().port,token,pid:process.pid}));renameSync(controlFile+'.tmp',controlFile);
const server=new sdk.Server({name:'friday-workspace-browser',version:'1.0'},{capabilities:{tools:{}}});
server.setRequestHandler(sdk.ListToolsRequestSchema,async()=>tools);
server.setRequestHandler(sdk.CallToolRequestSchema,async(request,extra)=>{
 try{return await manager.call(request.params.name,request.params.arguments||{},extra.signal);}
 catch(error){return {isError:true,content:[{type:'text',text:error.message}]};}
});
let closing=false;async function shutdown(){if(closing)return;closing=true;await manager.close();await server.close();control.close();try{if(JSON.parse(readFileSync(controlFile,'utf8')).token===token)unlinkSync(controlFile);}catch{}}
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>void shutdown().finally(()=>process.exit(0)));
process.stdin.on('end',()=>void shutdown().finally(()=>process.exit(0)));
await server.connect(new sdk.StdioServerTransport());
