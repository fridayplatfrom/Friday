import { randomUUID } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync, renameSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

// Server-to-server image requests share the existing extension transport. They
// never grant websites access to local tools, files, credentials or arbitrary URLs.
export class ImageJobs {
  constructor(bridge, directory) {
    this.bridge = bridge; this.records = {}; this.active = null;
    this.sessionId = 'local-image-studio';
    if (directory) {
      mkdirSync(directory, { recursive: true }); this.file = join(directory, 'image-jobs.json');
      if (existsSync(this.file)) this.records = JSON.parse(readFileSync(this.file, 'utf8'));
      for (const job of Object.values(this.records)) if (['queued','running'].includes(job.status)) {
        job.status = 'error'; job.message = 'Harness restarted. This request was not replayed.';
      }
      this.persist();
    }
  }
  persist() {
    if (this.file) { writeFileSync(this.file + '.tmp', JSON.stringify(this.records)); renameSync(this.file + '.tmp', this.file); }
  }
  view(id) {
    const job = this.records[id]; if (!job) return null;
    const live = this.active?.id === id ? this.bridge.sessions.get(this.sessionId) : null;
    return { id, status:job.status, percent:live?.percent ?? job.percent ?? null,
      message:live?.message || job.message, images:job.images.map(({id,mime})=>({id,mime})) };
  }
  create(input) {
    if (!input || typeof input.prompt !== 'string' || !input.prompt.trim() || input.prompt.length > 1500 || Object.keys(input).some(key=>key!=='prompt')) {
      return { status:400, body:{error:'Provide an image prompt of 1–1500 characters.'} };
    }
    if (this.active || this.bridge.jobs.size) return {status:409,body:{error:'Harness is busy. Wait for the active task to finish.'}};
    if (Object.values(this.records).filter(job=>Date.now()-job.createdAt<3600000).length >= 20) return {status:429,body:{error:'Local image limit reached. Try later.'}};
    const id = randomUUID();
    this.records[id] = {id,status:'queued',percent:null,message:'Waiting for the paired browser',images:[],createdAt:Date.now()};
    // Retain the newest 100 receipts. Raster assets stay in the normal media store.
    const entries = Object.values(this.records).sort((a,b)=>b.createdAt-a.createdAt).slice(0,100);
    this.records = Object.fromEntries(entries.map(job=>[job.id,job]));
    this.persist(); this.active = {id,controller:new AbortController()};
    this.running = this.run(id,input.prompt.trim(),this.active.controller.signal);
    return {status:202,body:{id,status:'queued'}};
  }
  async run(id,prompt,signal) {
    const job = this.records[id]; const deadline = setTimeout(()=>this.active?.id===id&&this.active.controller.abort(),960000);
    try {
      job.status='running'; this.persist();
      for await (const event of this.bridge.request('chatgpt-web',`Create an image based on this description:\n${prompt}`,signal,{sessionId:this.sessionId,purpose:'image'})) {
        if(event.type==='image') {job.images.push({id:event.image.id,mime:event.image.mime});this.persist();}
      }
      if (!job.images.length) throw new Error('The website finished without a transferable image. Check its visible reply or usage limits.');
      job.status='complete';job.message='Image ready';
    } catch { job.status='error';job.message='Image generation did not complete. Check Harness and the paired website before retrying.'; }
    finally {
      clearTimeout(deadline);job.percent=this.bridge.sessions.get(this.sessionId)?.percent??null;
      if(this.active?.id===id)this.active=null;this.persist();
    }
  }
  async handle(req,res,path) {
    if(path==='/image-jobs'&&req.method==='POST') {
      const result=this.create(await this.bridge.body(req));this.bridge.json(res,result.status,result.body);return;
    }
    const match=path.match(/^\/image-jobs\/([a-f0-9-]{36})(?:\/images\/([a-f0-9-]{36}\.(?:png|jpg|webp)))?$/);
    if(req.method!=='GET'||!match||!this.records[match[1]])return this.bridge.json(res,404,{error:'Image request not found.'});
    if(!match[2])return this.bridge.json(res,200,this.view(match[1]));
    if(!this.records[match[1]].images.some(image=>image.id===match[2]))return this.bridge.json(res,404,{error:'Image not found in this request.'});
    const image=this.bridge.sessions.readImage(match[2]);
    if(!image)return this.bridge.json(res,404,{error:'Image not available.'});
    res.writeHead(200,{'Content-Type':image.mime,'Content-Length':image.bytes.length,'Cache-Control':'private, no-store',
      'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'"});res.end(image.bytes);
  }
  async close(){this.active?.controller.abort();await this.running;}
}
