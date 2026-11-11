import {openSync,readSync,closeSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** Static inventory only: never load or execute installed application code. */
export function remoteDeclarations(source){
 const namespaces=[...new Set([...source.matchAll(/namespace:\s*"([^"]+)"/g)].map(match=>match[1]))];
 const methods=[];
 for(const match of source.matchAll(/_(\w+)_decorators\s*=\s*\[Remote\(([\s\S]*?)\)\];/g)){
   const declaration=match[2];
   methods.push({method:match[1],exportName:declaration.match(/^\s*"([^"]+)"/)?.[1]||declaration.match(/name:\s*"([^"]+)"/)?.[1]||match[1],mode:/mode:\s*"stream"/.test(declaration)?'stream':'unary'});
 }
 return {namespaceCandidates:namespaces,methods};
}

export function auditArchive(archive){
 const fd=openSync(archive,'r');
 try{
   const prefix=Buffer.alloc(16);readSync(fd,prefix,0,16,0);
   const length=prefix.readUInt32LE(12);
   if(length<2||length>64*1024*1024)throw new Error('Invalid ASAR header budget.');
   const header=Buffer.alloc(length);readSync(fd,header,0,length,16);
   const tree=JSON.parse(header.toString('utf8'));const dataOffset=8+prefix.readUInt32LE(4);
   const entries=[];
   function walk(node,path=''){for(const [name,entry]of Object.entries(node.files||{})){const p=path+'/'+name;if(entry.files)walk(entry,p);else entries.push({path:p,...entry});}}
   walk(tree);
   function text(entry){if(entry.unpacked||!Number.isFinite(Number(entry.offset))||entry.size>8*1024*1024)return null;const bytes=Buffer.alloc(entry.size);readSync(fd,bytes,0,bytes.length,dataOffset+Number(entry.offset));return bytes.toString('utf8');}
   const packages=entries.filter(entry=>/^\/dsh\/node_modules\/@deepseek-ai\/[^/]+\/package\.json$/.test(entry.path)).map(entry=>{
     const raw=text(entry);if(!raw)return null;const meta=JSON.parse(raw);return {name:meta.name,version:meta.version};
   }).filter(Boolean);
   const services=[];
   for(const entry of entries.filter(entry=>/^\/dsh\/node_modules\/@deepseek-ai\/[^/]+\/lib\/[^/]+\.js$/.test(entry.path))){
     const source=text(entry);if(!source||!source.includes('Remote('))continue;
     const declarations=remoteDeclarations(source);
     if(declarations.methods.length)services.push({package:entry.path.split('/')[4],file:entry.path,...declarations});
   }
   return {formatVersion:1,scope:'Static installed-bundle declarations; not a live gateway discovery or an assertion that every service is enabled. Namespace candidates are file-scoped; runtime Typert metadata is authoritative.',packages,services,methodDeclarations:services.reduce((sum,service)=>sum+service.methods.length,0)};
 }finally{closeSync(fd);}
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const archive=process.argv[2]||join(process.env.LOCALAPPDATA,'Programs','DeepSeek Harness','resources','app.asar');
 const output=process.argv[3];const result=auditArchive(archive);
 if(output)writeFileSync(output,JSON.stringify(result,null,2)+'\n');
 process.stdout.write(JSON.stringify({packages:result.packages.length,serviceFiles:result.services.length,methodDeclarations:result.methodDeclarations,output:output||null})+'\n');
}
