import {createConnection} from '@playwright/mcp';
import {createRequire} from 'node:module';
import {memoryTransports} from './memory-transport.mjs';
import {pathToFileURL} from 'node:url';
const {Client,ListRootsRequestSchema}=createRequire(import.meta.url)('playwright-core/lib/utilsBundle');
export async function upstreamConnection(factory,configuration,directory){
 const server=await createConnection(configuration,factory),client=new Client({name:'friday-workspace',version:'1.0'},{capabilities:directory?{roots:{}}:{}});
 if(directory)client.setRequestHandler(ListRootsRequestSchema,async()=>({roots:[{uri:pathToFileURL(directory).href,name:'Native workspace'}]}));
 const [a,b]=memoryTransports();await server.connect(a);await client.connect(b);return client;
}
