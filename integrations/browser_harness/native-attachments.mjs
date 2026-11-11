import { MAX_FILE_BYTES } from './file-store.mjs';

// Harness deliberately projects file blocks to local-path text before adapter
// dispatch. Capture only its admitted references before that projection, then
// match the exact host-generated placeholder and message identity afterwards.
export function captureNativeFiles(bridge,options,llm) {
  if(options.provider!=='browser-web')return;
  bridge.nativeFileOccurrences??=new Map();
  for(const message of options.messages||[]) {
    if(typeof message.id!=='string')continue;
    const entries=[];
    for(const [index,block] of (message.content||[]).entries())if(block.type==='file') {
      entries.push({index,ref:block.attachment,text:llm.fileRequestText(block.attachment)});
    }
    if(entries.length)bridge.nativeFileOccurrences.set(`${options.sessionId||'unscoped'}:${message.id}`,entries);
  }
  while(bridge.nativeFileOccurrences.size>512)bridge.nativeFileOccurrences.delete(bridge.nativeFileOccurrences.keys().next().value);
}

export function restoreNativeFiles(bridge,options) {
  if(!bridge.nativeFileOccurrences?.size)return options;
  let changed=false;
  const messages=(options.messages||[]).map(message=>{
    const entries=bridge.nativeFileOccurrences.get(`${options.sessionId||'unscoped'}:${message.id}`);
    if(!entries)return message;
    const content=[...(message.content||[])];let restored=false;
    for(const {index,ref,text}of entries)if(content[index]?.type==='text'&&content[index].text===text){content[index]={type:'file',attachment:ref};restored=true;}
    if(!restored)return message;changed=true;return {...message,content};
  });
  return changed?{...options,messages}:options;
}

/** Read only Harness-admitted durable references, using its verified file stream. */
export async function readNativeFile(attachments, ref, signal) {
  if (!ref || !Number.isSafeInteger(ref.bytes) || ref.bytes < 0 || ref.bytes > MAX_FILE_BYTES) {
    throw new Error('The browser website transfer limit is 32 MB per attachment. The original remains saved in Harness.');
  }
  const chunks=[];let size=0;
  for await (const chunk of attachments.readFileStream(ref,signal)) {
    signal?.throwIfAborted();const bytes=Buffer.from(chunk);size+=bytes.length;
    if(size>MAX_FILE_BYTES||size>ref.bytes)throw new Error('Native attachment size mismatch. Nothing was submitted.');
    chunks.push(bytes);
  }
  signal?.throwIfAborted();
  if(size!==ref.bytes)throw new Error('Native attachment is incomplete. Nothing was submitted.');
  return Buffer.concat(chunks,size);
}
