import { mkdirSync, readFileSync, writeFileSync, renameSync, existsSync } from 'node:fs';
import { join, extname, basename } from 'node:path';
import { createHash, randomUUID } from 'node:crypto';

export const CHUNK_BYTES = 384 * 1024;
export const MAX_FILE_BYTES = 32 * 1024 * 1024;
export const FILE_TYPES = Object.freeze({
  png:'image/png', jpg:'image/jpeg', jpeg:'image/jpeg', webp:'image/webp',
  txt:'text/plain', md:'text/markdown', csv:'text/csv', json:'application/json', pdf:'application/pdf',
  html:'text/html', css:'text/css', js:'text/javascript', mjs:'text/javascript', ts:'text/plain', tsx:'text/plain', jsx:'text/plain',
  py:'text/plain', yaml:'text/plain', yml:'text/plain', xml:'application/xml', svg:'image/svg+xml',
  docx:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xlsx:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', pptx:'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  zip:'application/zip', mp3:'audio/mpeg', wav:'audio/wav', m4a:'audio/mp4', mp4:'video/mp4', webm:'video/webm',
});
export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const validId = value => /^[a-f0-9-]{36}$/i.test(value || '');
const cleanName = value => {
  if (typeof value !== 'string' || value !== basename(value) || /[\\/:\x00-\x1f]/.test(value) || value.length > 180) throw new Error('Invalid attachment filename.');
  if (!FILE_TYPES[extname(value).slice(1).toLowerCase()]) throw new Error('Unsupported attachment format. Choose an image, document, source file, archive, audio or video from the supported list.');
  return value;
};

function validateIndex(records) {
  if(!records||typeof records!=='object'||Array.isArray(records))throw new Error('Invalid file index.');
  for(const [id,r] of Object.entries(records)) {
    if(!r||typeof r!=='object'||Array.isArray(r)||!validId(id)||r.id!==id||typeof r.sessionId!=='string'||!r.sessionId||r.sessionId.length>200)throw new Error('Invalid file identity.');
    cleanName(r.name);
    if(!Number.isSafeInteger(r.size)||r.size<0||r.size>MAX_FILE_BYTES||!Number.isSafeInteger(r.received)||r.received<0||r.received>r.size||
      !/^[a-f0-9]{64}$/.test(r.sha256)||!Array.isArray(r.chunks)||r.chunks.some(hash=>typeof hash!=='string'||!/^[a-f0-9]{64}$/.test(hash))||
      r.chunks.length>r.received||r.received>0&&!r.chunks.length||!['uploading','ready','delivered','cancelled'].includes(r.status)||
      !['to-website','from-website'].includes(r.direction)||r.mime!==FILE_TYPES[extname(r.name).slice(1).toLowerCase()]||
      ['ready','delivered'].includes(r.status)&&r.received!==r.size)throw new Error('Invalid file transfer metadata.');
  }
  return records;
}

/** Durable, ordered, idempotent chunk transfers. Files are data, never executed or extracted. */
export class FileStore {
  constructor(directory) {
    this.directory = directory; this.memory = new Map(); this.records = {};
    if (directory) { mkdirSync(directory,{recursive:true});
      if (existsSync(join(directory,'index.json'))) {
        try{this.records=validateIndex(JSON.parse(readFileSync(join(directory,'index.json'),'utf8')));}
        catch{throw new Error('Saved file index is invalid or damaged. Preserve index.json for recovery; no file data was erased.');}
      } }
  }
  persist() { if(this.directory){const path=join(this.directory,'index.json');writeFileSync(path+'.tmp',JSON.stringify(this.records));renameSync(path+'.tmp',path);} }
  begin({id=randomUUID(),sessionId,name,size,sha256,direction='to-website',sourceId=null}) {
    if (!validId(id) || typeof sessionId!=='string' || !sessionId || sessionId.length>200) throw new Error('Invalid attachment identity.');
    cleanName(name);
    if (!Number.isSafeInteger(size)||size<0||size>MAX_FILE_BYTES||!/^[a-f0-9]{64}$/.test(sha256)||!['to-website','from-website'].includes(direction)) throw new Error('Invalid attachment size, digest or direction.');
    const old=this.records[id];
    if(old){if(old.sessionId!==sessionId||old.name!==name||old.size!==size||old.sha256!==sha256||old.direction!==direction)throw new Error('Transfer identity conflict.');return old;}
    const active=Object.values(this.records).filter(r=>r.sessionId===sessionId);
    if(active.length>=100||active.reduce((n,r)=>n+r.size,0)+size>256*1024*1024)throw new Error('Session attachment storage limit reached.');
    const record=this.records[id]={id,sessionId,name,size,sha256,direction,sourceId,mime:FILE_TYPES[extname(name).slice(1).toLowerCase()],chunks:[],received:0,status:'uploading',at:Date.now()};
    try{this.persist();}catch(error){delete this.records[id];throw error;}return record;
  }
  get(id,sessionId) {const r=this.records[id];if(!r||r.sessionId!==sessionId)throw new Error('Attachment not found in this session.');return r;}
  chunk({id,sessionId,index,data}) {
    const r=this.get(id,sessionId);
    if(!Number.isSafeInteger(index)||index<0||typeof data!=='string'||data.length>CHUNK_BYTES*4/3+4||!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(data))throw new Error('Invalid attachment chunk.');
    const bytes=Buffer.from(data,'base64');const hash=digest(bytes);
    if(bytes.length>CHUNK_BYTES)throw new Error('Invalid attachment chunk size.');
    if(index<r.chunks.length){if(r.chunks[index]!==hash)throw new Error('Conflicting duplicate chunk.');return {next:r.chunks.length,received:r.received};}
    if(r.status!=='uploading'||index!==r.chunks.length||!bytes.length||r.received+bytes.length>r.size)throw new Error('Out-of-order or oversized attachment chunk.');
    const key=`${id}.${index}`;if(this.directory)writeFileSync(join(this.directory,key),bytes);else this.memory.set(key,bytes);
    r.chunks.push(hash);r.received+=bytes.length;
    try{this.persist();}catch(error){r.chunks.pop();r.received-=bytes.length;throw error;}
    return {next:r.chunks.length,received:r.received};
  }
  bytes(r) {return Buffer.concat(r.chunks.map((_,i)=>this.directory?readFileSync(join(this.directory,`${r.id}.${i}`)):this.memory.get(`${r.id}.${i}`)));}
  finish({id,sessionId}) {
    const r=this.get(id,sessionId);const bytes=this.bytes(r);
    if(bytes.length!==r.size||digest(bytes)!==r.sha256)throw new Error('Attachment integrity check failed. Resume the missing chunks.');
    if(r.status==='cancelled')throw new Error('Attachment was removed. Select it again as a new transfer.');
    if(r.status==='uploading'){
      if(this.directory)writeFileSync(join(this.directory,`${r.id}-${r.name}`),bytes);
      r.status='ready';try{this.persist();}catch(error){r.status='uploading';throw error;}
    }return this.public(r);
  }
  public(r) {return {id:r.id,name:r.name,size:r.size,mime:r.mime,sha256:r.sha256,status:r.status,direction:r.direction,received:r.received,next:r.chunks.length,url:`/browser-models/files/${r.id}`};}
  path(id,sessionId){const r=this.get(id,sessionId);if(r.status==='uploading')throw new Error('File is incomplete.');return this.directory?join(this.directory,`${r.id}-${r.name}`):null;}
  list(sessionId) {return Object.values(this.records).filter(r=>r.sessionId===sessionId).map(r=>this.public(r));}
  readChunk(id,sessionId,index) {const r=this.get(id,sessionId);if(r.status==='uploading')throw new Error('Attachment incomplete.');if(!Number.isSafeInteger(index)||index<0||index>=r.chunks.length)throw new Error('Invalid chunk index.');return {data:(this.directory?readFileSync(join(this.directory,`${id}.${index}`)):this.memory.get(`${id}.${index}`)).toString('base64')};}
  mark(ids,sessionId,status) {
    if(!['delivered','cancelled'].includes(status))throw new Error('Invalid attachment status change.');
    const records=[...new Set(ids)].map(id=>this.get(id,sessionId)),previous=records.map(r=>r.status);
    for(const r of records)r.status=status;
    try{this.persist();}catch(error){records.forEach((r,index)=>{r.status=previous[index];});throw error;}
  }
  put(sessionId,name,bytes,direction='to-website') {const r=this.begin({sessionId,name,size:bytes.length,sha256:digest(bytes),direction});for(let i=0;i<bytes.length;i+=CHUNK_BYTES)this.chunk({id:r.id,sessionId,index:i/CHUNK_BYTES,data:bytes.subarray(i,i+CHUNK_BYTES).toString('base64')});return this.finish({id:r.id,sessionId});}
}
