import {listPackage,statFile,getRawHeader} from '@electron/asar';
import {readFileSync,mkdirSync,writeFileSync,linkSync,copyFileSync} from 'node:fs';
import {join,resolve,normalize,dirname,sep} from 'node:path';
import {spawnSync} from 'node:child_process';
/** Materialize the official prepared Node runtime; never patch its loader. */
export function materializeHarness(archive,target){
 const root=resolve(target),data=readFileSync(archive),start=8+getRawHeader(archive).headerSize;
 const dsh=join(root,'dsh');mkdirSync(dsh,{recursive:true});
 // Build-space optimization only. Never change compression on source files or
 // existing hard links. Installed bytes are archived and extracted normally.
 if(process.platform==='win32')spawnSync('compact.exe',['/C','/I','/Q',dsh],{windowsHide:true});
 let files=0;
 for(const full of listPackage(archive)){
  const filename=full.slice(1);if(!filename.replaceAll('\\','/').startsWith('dsh/'))continue;
  const destination=resolve(root,filename);if(!destination.startsWith(root+sep))throw Error('Runtime archive path escaped its destination');
  const entry=statFile(archive,normalize(filename));if('files'in entry){mkdirSync(destination,{recursive:true});continue;}
  if('link'in entry)throw Error('Unexpected unresolved runtime link');mkdirSync(dirname(destination),{recursive:true});
  if(entry.unpacked){const source=join(archive+'.unpacked',filename);try{linkSync(source,destination);}catch(error){if(error.code==='EXDEV'||error.code==='EPERM')copyFileSync(source,destination);else throw error;}}
  else writeFileSync(destination,data.subarray(start+Number(entry.offset||0),start+Number(entry.offset||0)+entry.size));
  files++;
 }
 return files;
}
