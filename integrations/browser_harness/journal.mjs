import {mkdirSync,appendFileSync,existsSync,writeFileSync,openSync,readSync,closeSync,truncateSync} from 'node:fs';
import {StringDecoder} from 'node:string_decoder';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';

/** Stream UTF-8 records without loading a lifetime of context payloads into RAM. */
function* records(file){
 const fd=openSync(file,'r'),buffer=Buffer.alloc(65536),decoder=new StringDecoder('utf8');let pending='',offset=0;
 try{let count;while((count=readSync(fd,buffer,0,buffer.length,null))){
  pending+=decoder.write(buffer.subarray(0,count));let end;
  while((end=pending.indexOf('\n'))>=0){const line=pending.slice(0,end);yield {line,offset,terminated:true};offset+=Buffer.byteLength(line)+1;pending=pending.slice(end+1);}
 }pending+=decoder.end();if(pending)yield {line:pending,offset,terminated:false};}finally{closeSync(fd);}
}

/** Append-only full disk audit; bounded recent memory, with no action replay. */
export class DeliveryJournal {
 constructor(directory,{maxMemoryEvents=2000,maxMemoryBytes=16*1024*1024}={}){
  if(!Number.isSafeInteger(maxMemoryEvents)||maxMemoryEvents<1||!Number.isSafeInteger(maxMemoryBytes)||maxMemoryBytes<1)throw new Error('Invalid journal memory budget.');
  this.events=[];this.sizes=[];this.memoryBytes=0;this.maxMemoryEvents=maxMemoryEvents;this.maxMemoryBytes=maxMemoryBytes;this.sequence=0;this.file=directory&&join(directory,'delivery.jsonl');
  if(!directory)return;mkdirSync(directory,{recursive:true});if(!existsSync(this.file))return;
  let recovery;
  for(const record of records(this.file)){
   if(!record.line)continue;let event;
   try{event=JSON.parse(record.line);}catch{
    if(record.terminated)throw new Error('Delivery journal is damaged; preserve it before recovery.');
    recovery=record;break;
   }
   this.sequence=Math.max(this.sequence+1,Number.isSafeInteger(event.seq)?event.seq:0);this.remember(event,Buffer.byteLength(record.line));
   if(!record.terminated)recovery={...record,valid:true};
  }
  if(recovery?.valid)appendFileSync(this.file,'\n');
  else if(recovery){
   const backup=this.file+'.interrupted-tail'+(existsSync(this.file+'.interrupted-tail')?'.'+randomUUID():'');
   const fd=openSync(this.file,'r'),buffer=Buffer.alloc(65536);let position=recovery.offset,count;
   try{writeFileSync(backup,Buffer.alloc(0),{flag:'wx'});while((count=readSync(fd,buffer,0,buffer.length,position))){appendFileSync(backup,buffer.subarray(0,count));position+=count;}}finally{closeSync(fd);}
   truncateSync(this.file,recovery.offset);
  }
 }
 remember(event,bytes){
  this.events.push(event);this.sizes.push(bytes);this.memoryBytes+=bytes;
  while(this.events.length>this.maxMemoryEvents||this.memoryBytes>this.maxMemoryBytes&&this.events.length>1){this.events.shift();this.memoryBytes-=this.sizes.shift();}
 }
 append(sessionId,type,data={}){const event={seq:++this.sequence,at:Date.now(),sessionId,type,data},line=JSON.stringify(event);if(this.file)appendFileSync(this.file,line+'\n');this.remember(event,Buffer.byteLength(line));return event.seq;}
 *all(){if(this.file){if(!existsSync(this.file)&&this.sequence===0)return;for(const {line}of records(this.file))if(line)yield JSON.parse(line);}else yield* this.events;}
 list(sessionId){const result=[];for(const event of this.all())if(event.sessionId===sessionId)result.push(event);return result;}
 interrupted(){const jobs=new Map();for(const event of this.all()){if(event.type==='request')jobs.set(event.data.id,event);if(['complete','failed','cancelled'].includes(event.type))jobs.delete(event.data.id);}return [...jobs.values()];}
}
