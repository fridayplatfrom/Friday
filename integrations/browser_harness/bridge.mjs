import http from 'node:http';
import {readFileSync} from 'node:fs';
import { randomUUID, timingSafeEqual } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';
import { SITES,browserWirePrompt } from './protocol.mjs';
import { SessionStore } from './session-store.mjs';
import { TwoWayRelay } from './two-way.mjs';
import { join } from 'node:path';
import { FileStore } from './file-store.mjs';
import { DeliveryJournal } from './journal.mjs';
import { homedir } from 'node:os';
import { importBrowserDownload } from './download-import.mjs';
import { ImageJobs } from './image-jobs.mjs';
import {BACKEND_VERSION,recentMetrics} from './diagnostics.mjs';
import {Activity} from './activity.mjs';
import {FridayAGUI} from './ag-ui.mjs';
import {publicProvider,PROVIDERS,providerProbe} from './providers.mjs';
import {recoveryDiagnostic} from './diagnostics.mjs';
import {RequestScheduler} from './request-scheduler.mjs';
import {startSetupTest} from './setup-test.mjs';

export class BrowserBridge {
  constructor({ token, port = 8766, timeoutMs = 300000, connectionGraceMs = 45000, controller = null, transportMode='extension',autoTwoWay=false,stateDirectory, extensionManifestPath=join(homedir(),'.dsh/browser-connector/extension/manifest.json'),downloadDirectory=join(homedir(),'Downloads'), now = () => Date.now() } = {}) {
    this.extensionManifestPath=extensionManifestPath;
    if (typeof token !== 'string' || token.length < 32) throw new Error('A local bridge pairing token is required. Run setup.ps1.');
    if(!['extension','shared-browser'].includes(transportMode))throw new Error('Unknown browser transport');
    Object.assign(this, { token, port, timeoutMs, connectionGraceMs, controller, downloadDirectory, now,transportMode });
    this.jobs = new Map(); this.lastSeen = 0; this.enabledSites = []; this.server = null;
    // Old extensions and single-page browser transports remain serial until
    // their capability is positively known. Modern Chrome workers have 2 slots.
    this.scheduler = new RequestScheduler(1);
    this.sessions = new SessionStore(stateDirectory,{autoTwoWay});
    this.activity = new Activity(this.sessions);
    for(const id of Object.keys(this.sessions.sessions))this.activity.interrupted(id);
    this.files = new FileStore(stateDirectory && join(stateDirectory,'files'));
    this.journal = new DeliveryJournal(stateDirectory);
    this.agui = new FridayAGUI(this,stateDirectory);
    this.activity.onEvent=(id,_event,state)=>{try{this.agui.state(id,state);}catch(error){this.agui.lastProjectionError=String(error.message).slice(0,300);}};
    this.eventReceipts=new Set(this.journal.events.filter(event=>event.type==='event-receipt').map(event=>`${event.data.id}:${event.data.eventId}`));
    this.twoWay = new TwoWayRelay(this);
    this.instanceId = randomUUID();
    this.actions = [];
    this.imageJobs = new ImageJobs(this, stateDirectory);
  }
  async start() {
    this.server = http.createServer((req, res) => this.handle(req, res).catch(error => {
      if (!res.headersSent) this.json(res, 400, { error: error.message }); else res.end();
    }));
    this.server.requestTimeout = 10000;
    this.server.headersTimeout = 10000;
    await new Promise((resolve, reject) => { this.server.once('error', reject); this.server.listen(this.port, '127.0.0.1', resolve); });
    this.port = this.server.address().port;
    return this;
  }
  json(res, status, value) {
    res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    res.end(JSON.stringify(value));
  }
  authorized(req) {
    const expected = Buffer.from(`Bearer ${this.token}`); const actual = Buffer.from(req.headers.authorization || '');
    return actual.length === expected.length && timingSafeEqual(actual, expected);
  }
  async body(req) {
    let size = 0; const parts = [];
    for await (const part of req) { size += part.length; if (size > 2100000) throw new Error('Request too large.'); parts.push(part); }
    return JSON.parse(Buffer.concat(parts).toString('utf8') || '{}');
  }
  async handle(req, res) {
    if (req.headers.host !== `127.0.0.1:${this.port}`) return this.json(res, 403, { error: 'Loopback Host required.' });
    const path = new URL(req.url, `http://127.0.0.1:${this.port}`).pathname;
    // A webpage cannot pair with the bridge or read its jobs. Only the extension
    // and local authenticated clients can access it. Never allow website CORS.
    const origin = req.headers.origin;
    const localUI = origin === `http://127.0.0.1:${this.port}` && path.startsWith('/ui/');
    if (origin && !localUI && !/^chrome-extension:\/\/[a-p]{32}$/.test(origin)) return this.json(res, 403, { error: 'Origin denied.' });
    if (origin) {
      res.setHeader('Access-Control-Allow-Origin', origin);
      res.setHeader('Vary', 'Origin');
      res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    }
    if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }
    if (!this.authorized(req)) return this.json(res, 401, { error: 'Pairing token required.' });
    // Explicit desktop ownership prevents the installed extension and Electron
    // from dispatching the same request. No automatic takeover of uncertain work.
    if(req.method==='POST'&&['/desktop/claim','/desktop/release'].includes(path)){
      const input=await this.body(req);
      if(!/^[a-f0-9-]{36}$/i.test(input.clientId||''))throw new Error('Invalid desktop owner.');
      if(this.controller||this.transportMode!=='extension')return this.json(res,409,{error:'Desktop requires the extension profile.'});
      if(this.desktopOwner&&this.desktopOwner!==input.clientId)return this.json(res,409,{error:'Another desktop owns this bridge.'});
      if((path==='/desktop/release'||this.desktopOwner!==input.clientId)&&[...this.jobs.values()].some(job=>!job.terminal))return this.json(res,409,{error:'Finish or cancel active Friday requests before changing transport.'});
      this.desktopOwner=path==='/desktop/claim'?input.clientId:null;
      this.lastSeen=0;this.enabledSites=[];
      return this.json(res,200,{ok:true,transport:this.desktopOwner?'desktop':this.transportMode});
    }
    if(req.method==='POST'&&path==='/desktop/setup-test'){
      return this.json(res,200,startSetupTest(this,await this.body(req)));
    }
    if(req.method==='POST'&&path==='/desktop/setup-default'){
      const input=await this.body(req),test=this.setupTests?.get(input.id)||this.sessions.get('friday-setup-'+input.id)?.setupConnectionTest;
      if(!this.desktopOwner||input.clientId!==this.desktopOwner||test?.status!=='passed'||test.site!==input.site)throw Error('A verified Desktop setup test is required.');
      if(this.schedulingStatus().pending)throw Error('Finish the active task first.');
      if(!this.configureSetupDefault)throw Error('Native default-model settings are not ready. Your connection is verified; try finishing setup again.');
      await this.configureSetupDefault(input.site);return this.json(res,200,{ok:true});
    }
    if(req.method==='GET'&&path.startsWith('/desktop/setup-test/')){
      if(!this.desktopOwner||req.headers['x-friday-client']!==this.desktopOwner)return this.json(res,403,{error:'Friday Desktop ownership required.'});
      const result=this.setupTests?.get(path.split('/').at(-1));return this.json(res,result?200:404,result||{error:'Test unavailable after restart. Inspect the provider chat; no test was resent.'});
    }
    if(req.method==='POST'&&path==='/provider-health'){
      const input=await this.body(req);(this.providerHealth||={})[input.site]=providerProbe(input);return this.json(res,200,{ok:true});
    }
    if(path==='/image-jobs'||path.startsWith('/image-jobs/'))return this.imageJobs.handle(req,res,path);
    if(req.method==='POST'&&path==='/download-file'){
      const input=await this.body(req),job=this.jobs.get(input.jobId);
      const pair=job&&this.sessions.get(job.sessionId)?.pairs?.[job.site];
      const file=importBrowserDownload(this.files,job,input,{directory:this.downloadDirectory,pair});
      this.journal.append(job.sessionId,'download-import',{id:job.id,fileId:file.id,name:file.name,size:file.size});
      return this.json(res,200,file);
    }
    if(req.method==='POST' && path.startsWith('/files/')) {
      const input=await this.body(req);
      if(input.jobId){const job=this.jobs.get(input.jobId);if(!job?.claimed)throw new Error('No active file job.');input.sessionId=job.sessionId;}
      else this.twoWay.pair(input);
      return this.json(res,200,this.fileAction(path.split('/').at(-1),input,'from-website'));
    }
    if(req.method==='POST' && path==='/job-file') {
      const input=await this.body(req);const job=this.jobs.get(input.jobId);
      if(!job||!job.claimed||!job.attachments.some(file=>file.id===input.id))throw new Error('File does not belong to this active job.');
      return this.json(res,200,this.files.readChunk(input.id,job.sessionId,input.index));
    }
    if (req.method === 'POST' && ['/inbound', '/inbound/stop'].includes(path)) {
      try {
        const input = await this.body(req);
        return this.json(res, 200, await (path === '/inbound' ? this.twoWay.accept(input) : this.twoWay.stop(input)));
      } catch (error) { return this.json(res, 409, { error: error.message }); }
    }
    if (req.method === 'GET' && path === '/ui/status') return this.json(res, 200, this.uiStatus());
    if (req.method === 'POST' && ['/ui/open', '/ui/connect', '/ui/disconnect', '/ui/new-chat'].includes(path)) {
      try { return this.json(res, 200, await this.uiAction(path.slice(4), await this.body(req))); }
      catch (error) { return this.json(res, 409, { error: error.message }); }
    }
    if (req.method === 'GET' && path === '/status') return this.json(res, 200, {
      connected: this.controller ? this.controller.status().enabled : Date.now() - this.lastSeen < 15000,
      enabledSites: this.controller ? (this.controller.status().enabled ? [this.controller.status().site] : []) : this.enabledSites,
      transport: this.controller ? 'builtin' : this.desktopOwner?'desktop':this.transportMode,
      ...this.schedulingStatus(), version: 2, backendVersion:BACKEND_VERSION, extensionVersion: this.extensionVersion || null,
      availableExtensionVersion:this.availableExtensionVersion(),
    });
    if (req.method === 'POST' && path === '/poll') {
      const input = await this.body(req);
      if(this.desktopOwner&&(input.transport||'extension')==='extension')return this.json(res,200,{commands:[],actions:[],activeIds:[],listeners:[],parked:true,...this.schedulingStatus()});
      const expectedTransport=this.desktopOwner?'desktop':this.transportMode;
      if((input.transport||'extension')!==expectedTransport||this.desktopOwner&&input.clientId!==this.desktopOwner)return this.json(res,409,{error:'This Harness profile uses a different browser transport. No request was claimed.'});
      this.enabledSites = Array.isArray(input.sites) ? input.sites.filter(site => Object.hasOwn(SITES, site)) : [];
      this.lastSeen = Date.now();
      this.extensionVersion = typeof input.version === 'string' ? input.version.slice(0, 30) : null;
      const [major,minor]=String(this.extensionVersion||'').split('.').map(Number);
      this.scheduler.setLimit(!this.controller&&this.transportMode==='extension'&&(major>0||major===0&&minor>=10)?2:1);
      for (const binding of (Array.isArray(input.bindings) ? input.bindings : []).slice(0, 200)) {
        this.sessions.bind(binding);
      }
      const commands = [];
      for (const job of this.jobs.values()) {
        if (this.controller) break;
        if(job.terminal)continue;
        const recovering=job.claimed&&Array.isArray(input.runningIds)&&!input.runningIds.includes(job.id)&&Date.now()-(job.lastDispatchAt||0)>10000;
        if ((!job.claimed||recovering) && this.enabledSites.includes(job.site)) {
          if(job.attachments.length&&!/^0\.(?:[4-9]|[1-9]\d)\.|^[1-9]\d*\./.test(this.extensionVersion||'')){
            job.claimed=true;this.record(job,{type:'error',message:'Reload Friday v0.4.0 or newer before uploading files. Attachments remain saved; no prompt was sent.'});continue;
          }
          job.claimed = true;
          job.lastDispatchAt=Date.now();
          this.journal.append(job.sessionId,'dispatched',{id:job.id});
          commands.push({ id: job.id, resume:recovering, purpose:job.site==='kimi-web'?'task':job.purpose,site: job.site, sessionId: job.sessionId, conversationUrl:this.sessions.get(job.sessionId)?.pairs?.[job.site]?.url||null,prompt: job.prompt, attachments:job.attachments, url: SITES[job.site].url, timeoutMs: job.timeoutMs,
            ...(job.externalMessageId ? { externalMessageId: job.externalMessageId } : {}) });
          if(commands.length>=this.scheduler.limit)break;
        }
      }
      return this.json(res, 200, { commands, actions: this.actions.splice(0), activeIds: [...this.jobs.keys()], ...this.schedulingStatus(),
        listeners: this.twoWay.listeners(Array.isArray(input.bindings) ? input.bindings.slice(0, 200) : []) });
    }
    if (req.method === 'POST' && path === '/event') {
      const event = await this.body(req); const job = this.jobs.get(event.id);
      if(typeof event.eventId==='string'&&this.eventReceipts.has(`${event.id}:${event.eventId}`))return this.json(res,200,{ok:true,duplicate:true});
      if (!job || !job.claimed) return this.json(res, 410, { error: 'Request expired or cancelled.' });
      if (this.controller) return this.json(res, 409, { error: 'Built-in browser owns this request.' });
      if (typeof event.eventId==='string' && job.receipts.has(event.eventId)) return this.json(res,200,{ok:true,duplicate:true});
      if (job.terminal) return this.json(res, 409, { error: 'Request already finished.' });
      this.record(job, event);
      if(typeof event.eventId==='string'){
        job.receipts.add(event.eventId);this.eventReceipts.add(`${event.id}:${event.eventId}`);
        if(this.eventReceipts.size>8000)this.eventReceipts.delete(this.eventReceipts.values().next().value);
        this.journal.append(job.sessionId,'event-receipt',{id:event.id,eventId:event.eventId});
      }
      return this.json(res, 200, { ok: true });
    }
    return this.json(res, 404, { error: 'Not found.' });
  }
  availableExtensionVersion(){try{const version=JSON.parse(readFileSync(this.extensionManifestPath,'utf8')).version;return /^\d+\.\d+\.\d+$/.test(version)?version:null;}catch{return null;}}
  schedulingStatus(){const activeRequests=Math.max(this.jobs.size,this.scheduler.active.size);return {pending:activeRequests+this.scheduler.queue.length,activeRequests,queuedRequests:this.scheduler.queue.length,maxConcurrentRequests:this.scheduler.limit};}
  uiStatus() {
    return { instanceId: this.instanceId, backendVersion:BACKEND_VERSION, metrics:recentMetrics(this.journal.events),journalWindow:{records:this.journal.events.length,serializedBytes:this.journal.memoryBytes,maxRecords:this.journal.maxMemoryEvents,targetSerializedBytes:this.journal.maxMemoryBytes}, extensionVersion:this.extensionVersion||null, ...(this.controller?.status() || { transport: this.desktopOwner?'desktop':this.transportMode, phase: this.desktopOwner?'Desktop prototype':this.transportMode==='shared-browser'?'Existing Harness browser':'Extension mode',connected:Date.now()-this.lastSeen<15000,enabledSites:[...this.enabledSites] }), ...this.schedulingStatus(),
      providers: Object.keys(SITES).map(id=>publicProvider(id,this.providerHealth?.[id])) };
  }
  fileAction(action,input,direction='to-website') {
    if(action==='begin')return this.files.public(this.files.begin({...input,direction}));
    if(action==='chunk')return this.files.chunk(input);
    if(action==='finish'){
      const file=this.files.finish(input);this.journal.append(input.sessionId,'file-ready',{id:file.id,name:file.name,direction});return file;
    }
    if(action==='cancel'){this.files.mark([input.id],input.sessionId,'cancelled');return {ok:true};}
    throw new Error('Unknown file transfer action.');
  }
  async uiAction(action, input = {}) {
    if(action==='health'||action==='refresh-provider'||action==='pair-provider'){
      if(!Object.hasOwn(PROVIDERS,input.site))throw new Error('Unknown browser website.');
      if(input.sessionId&&!this.sessions.get(input.sessionId))throw new Error('Unknown Friday session.');
      if(action!=='health'&&!input.sessionId)throw new Error('Select the exact Friday conversation first.');
      if(action!=='health'&&this.schedulingStatus().pending)throw new Error('Finish the active or queued website requests before changing their paired tabs.');
      if(this.actions.length>=10)throw new Error('Website actions are busy.');
      this.actions.push({type:action==='health'?'probe-site':action==='pair-provider'?'pair-site':'refresh-site',site:input.site,...(input.sessionId?{sessionId:input.sessionId}:{})});return {ok:true,queued:true};
    }
    if (action === 'two-way') return this.twoWay.enable(input.sessionId, input.enabled);
    if(action==='open'&&!this.controller&&this.transportMode==='shared-browser'){
      if(typeof input.site!=='string'||!Object.hasOwn(SITES,input.site))throw new Error('Unknown browser website.');
      if(this.actions.length>=10)throw new Error('Website actions are busy.');
      this.actions.push({type:'open-site',site:input.site});return {ok:true,queued:true};
    }
    if (action === 'focus' && !this.controller) {
      if (!this.sessions.get(input.sessionId)?.pairs?.[input.site]) throw new Error('No paired website chat yet.');
      if (this.actions.length > 10) throw new Error('Website actions are busy.');
      this.actions.push({ type: 'focus', sessionId: input.sessionId, site: input.site,conversationUrl:this.sessions.get(input.sessionId).pairs[input.site].url }); return { ok: true };
    }
    if(!this.controller&&['connect','disconnect'].includes(action)){
      if(typeof input.site!=='string'||!Object.hasOwn(SITES,input.site))throw new Error('Unknown browser website.');
      if(this.schedulingStatus().pending)throw new Error('Finish or cancel the active website requests and queued requests before changing connections.');
      if(this.actions.length>=10)throw new Error('Connection changes are busy.');
      this.actions.push({type:'configure-site',site:input.site,enabled:action==='connect'});
      return {ok:true,queued:true};
    }
    if (!this.controller) throw new Error('This action requires managed model-browser mode; task browser tools remain available in Harness.');
    return action === 'open' ? this.controller.open(input.site)
      : action === 'connect' ? this.controller.connect(input.site)
      : action === 'test' ? this.controller.testConnection()
      : action === 'new-chat' ? this.controller.resetConversation()
      : this.controller.disconnect ? this.controller.disconnect() : this.controller.close();
  }
  record(job, event) {
    if (job.terminal) throw new Error('Request already finished.');
    if (event.type === 'binding') { this.sessions.bind({ ...event, sessionId: job.sessionId, site: job.site }); return; }
    if(event.type==='artifact-warning'){
      const message=String(event.message||'File could not be transferred. Use manual download.').slice(0,500);
      const state=this.sessions.get(job.sessionId);this.sessions.update(job.sessionId,{warnings:[...(state?.warnings||[]),message].slice(-20)});
      this.journal.append(job.sessionId,'artifact-warning',{id:job.id,message});return;
    }
    if(event.type==='submitted'){
      job.submitted=true;
      this.journal.append(job.sessionId,'submitted',{id:job.id,turnKey:event.turnKey||null});
      if(job.attachments.length)this.files.mark(job.attachments.map(file=>file.id),job.sessionId,'delivered');
      this.sessions.update(job.sessionId,{phase:'receiving',message:'Website accepted the request — receiving its response'});
      this.activity.status(job.sessionId,'receiving','ChatGPT accepted the request — receiving its response',job.id);return;
    }
    if(event.type==='file'){
      if((job.fileCount||0)>=8)throw new Error('Output file limit reached.');
      const file=this.files.public(this.files.get(event.fileId,job.sessionId));
      if(file.status==='uploading')throw new Error('Output file transfer incomplete.');
      if(file.direction!=='from-website')throw new Error('Invalid output file direction.');
      job.fileCount=(job.fileCount||0)+1;
      job.events.push({type:'file',file});return;
    }
    if (event.type === 'status') {
      if (!['response-loading', 'receiving','uploading','reconnecting','executing'].includes(event.state)) throw new Error('Invalid website status.');
      const now = this.now();
      if (event.state === 'response-loading') job.responseLoadingSince ??= now;
      else if (job.responseLoadingSince !== undefined) {
        job.responseLoadingPausedMs = (job.responseLoadingPausedMs || 0) + now - job.responseLoadingSince;
        delete job.responseLoadingSince;
      }
      this.sessions.update(job.sessionId, { phase: event.state==='response-loading'?'waiting':event.state, message: event.state === 'response-loading'
        ? 'Response couldn’t load — waiting to load' : event.state==='uploading'?'Uploading attachments — waiting for website confirmation':event.state==='receiving'?'Response loaded — receiving reply':event.state==='reconnecting'?'Connecting to the paired website — waiting for its chat editor':event.state });
      this.activity.status(job.sessionId,event.state==='response-loading'?'waiting':event.state,this.sessions.get(job.sessionId).message,job.id);
      return;
    }
    if (event.type === 'progress') {
      if (event.percent !== null && (!Number.isFinite(event.percent) || event.percent < 0 || event.percent > 100)) throw new Error('Invalid image progress.');
      const previous = this.sessions.get(job.sessionId);
      job.timeoutMs = Math.max(job.timeoutMs, 900000); // Image rendering can outlast a normal text reply.
      const history = previous?.progress || [];
      if (event.percent !== null && history.at(-1)?.percent !== event.percent) history.push({ percent: event.percent, at: Date.now() });
      if (history.length > 1000) throw new Error('Progress update limit reached.');
      this.sessions.update(job.sessionId, { phase: 'generating', percent: event.percent, progress: history,
        message: String(event.message || 'Creating image').slice(0, 200) });
      this.activity.status(job.sessionId,'generating',String(event.message||'Creating image'),job.id);
      this.journal.append(job.sessionId,'progress',{id:job.id,percent:event.percent,message:String(event.message||'Creating image').slice(0,200)});
      return;
    }
    if (event.type === 'image-start') {
      if (job.upload || !['image/png', 'image/jpeg', 'image/webp'].includes(event.mime)) throw new Error('Invalid image transfer.');
      if ((job.imageCount || 0) >= 8) throw new Error('Image count limit reached.');
      job.upload = { mime: event.mime, alt: event.alt, chunks: [], size: 0 }; return;
    }
    if (event.type === 'image-chunk') {
      const upload = job.upload;
      if (!upload || typeof event.data !== 'string' || event.data.length > 1000000 || !/^[A-Za-z0-9+/=]+$/.test(event.data) || event.index !== upload.chunks.length) throw new Error('Invalid image chunk.');
      if (upload.size + event.data.length > 23000000) throw new Error('Image transfer too large.');
      upload.size += event.data.length; upload.chunks.push(event.data); return;
    }
    if (event.type === 'image-end') {
      if (!job.upload) throw new Error('No image transfer.');
      const { mime, alt, chunks } = job.upload;
      const image = this.sessions.saveImage(Buffer.from(chunks.join(''), 'base64'), mime, alt);
      job.upload = null; job.imageCount = (job.imageCount || 0) + 1;
      const state = this.sessions.get(job.sessionId);
      this.sessions.update(job.sessionId, { images: [...(state?.images || []), { ...image, jobId: job.id,progress:structuredClone(state?.progress||[]) }].slice(-100) });
      job.events.push({ type: 'image', image }); return;
    }
    if (!['snapshot', 'done', 'error'].includes(event.type)) throw new Error('Unknown event type.');
    if (event.type === 'done' && job.upload) throw new Error('Image transfer incomplete.');
    if (event.type === 'error') {
      if (typeof event.message !== 'string' || event.message.length > 2000) throw new Error('Invalid error.');
    } else if (typeof event.text !== 'string' || event.text.length > 500000) throw new Error('Invalid response text.');
    if (job.events.length >= 1000 || job.bytes + (event.text?.length || 0) > 16000000) throw new Error('Response update limit reached.');
    job.bytes += event.text?.length || 0; job.events.push(event);
    if(event.type!=='snapshot'||!job.lastJournalAt||Date.now()-job.lastJournalAt>1000){this.journal.append(job.sessionId,event.type==='done'?'complete':event.type==='error'?'failed':'reply',{id:job.id,text:event.text,message:event.message});job.lastJournalAt=Date.now();}
    if (event.type !== 'snapshot') {
      job.terminal = true;
      this.sessions.update(job.sessionId, { phase: event.type === 'done' ? 'complete' : 'error', message: event.message || 'Reply complete' });
      this.activity.status(job.sessionId,event.type==='done'?'reply-received':'error',event.message||'Website reply received — Harness is processing it',job.id);
    }
  }
  async *request(site, prompt, signal, { sessionId = 'unscoped', purpose = 'task', externalMessageId = null, attachments=[] } = {}) {
    if(attachments.length&&!PROVIDERS[site]?.capabilities.fileTransfer)throw new Error('File transfer is not verified for this provider. Choose ChatGPT for native attachments.');
    if (!Object.hasOwn(SITES, site)) throw new Error('Unknown browser website.');
    signal?.throwIfAborted();
    // A store's asynchronous image tool can return before its browser job ends.
    // Wait for that owned job instead of failing the agent's next model call.
    const imageRun=this.imageJobs.active&&this.imageJobs.running;
    const ownsImageSlot=imageRun&&sessionId!==this.imageJobs.sessionId&&this.jobs.size&&
      [...this.jobs.values()].every(job=>job.sessionId===this.imageJobs.sessionId&&job.purpose==='image');
    if(ownsImageSlot){
      this.sessions.update(sessionId,{site,phase:'waiting',percent:null,message:'Image studio is generating — waiting for the browser connection'});
      this.journal.append(sessionId,'waiting-image-job',{imageJobId:this.imageJobs.active.id});
      let abort;
      try{
        if(signal)await Promise.race([imageRun,new Promise((_,reject)=>{
          abort=()=>reject(signal.reason||new DOMException('Request cancelled','AbortError'));
          signal.addEventListener('abort',abort,{once:true});
        })]);
        else await imageRun;
      }finally{if(abort)signal.removeEventListener('abort',abort);}
      signal?.throwIfAborted();
    }
    if(this.closing)throw Object.assign(new Error('Friday bridge is stopping. No new website request was submitted.'),{code:'FRIDAY_BRIDGE_STOPPED'});
    let release,admitted=false;
    try {
      release=this.scheduler.acquire(sessionId,signal,({position,sameSession})=>{
        // Do not overwrite another active turn's status in this same chat.
        if(sameSession)return;
        const message=`Queued · waiting for a browser slot (position ${position})`;
        this.sessions.update(sessionId,{site,phase:'queued',message,queuePosition:position});
        this.activity.ensure(sessionId);this.activity.status(sessionId,'queued',message);
      });
      if(typeof release!=='function')release=await release;
      admitted=true;
      signal?.throwIfAborted();
      yield* this.runRequest(site,prompt,signal,{sessionId,purpose,externalMessageId,attachments});
    } catch(error) {
      if(![...this.jobs.values()].some(job=>job.sessionId===sessionId)&&(!admitted||this.sessions.get(sessionId)?.phase==='queued')){
        this.sessions.update(sessionId,{phase:signal?.aborted?'cancelled':'error',queuePosition:null,message:String(error.message).slice(0,500)});
        this.activity.status(sessionId,signal?.aborted?'cancelled':'error',String(error.message).slice(0,500));
        this.journal.append(sessionId,'queue-ended',{submitted:false,cancelled:!!signal?.aborted});
      }
      throw error;
    } finally {if(typeof release==='function')release();}
  }
  async *runRequest(site,prompt,signal,{sessionId,purpose,externalMessageId,attachments}) {
    if (this.controller && !this.controller.isConnected(site)) throw new Error('Open Settings → Models, open the website, then click Connect.');
    const job = { id: randomUUID(), site, sessionId, purpose,prompt, externalMessageId, attachments, createdAt:Date.now(), receipts:new Set(), events: [], claimed: false, terminal: false, bytes: 0, timeoutMs: this.timeoutMs };
    job.prompt=browserWirePrompt(site,prompt,job.id);
    this.journal.append(sessionId,'request',{id:job.id,site,prompt:job.prompt,purpose,externalMessageId,attachments});
    this.activity.ensure(sessionId);
    this.activity.status(sessionId,'waiting',purpose==='introduction'?'Connecting the conversation':purpose==='context'?'Transferring task context':purpose==='image'?'Waiting for image generation': 'Waiting for the paired website',job.id);
    const start = this.now(); let cursor = 0;
    this.sessions.update(sessionId, { site, jobId: job.id, phase: 'waiting',queuePosition:null,
      message: purpose === 'introduction' ? 'Introducing Harness to ChatGPT' : 'Waiting for website', percent: null, progress: [] });
    // Publish only after durable setup succeeds: a storage exception must not
    // leave a dispatchable request whose native consumer already failed.
    this.jobs.set(job.id, job);
    const localAbort = new AbortController();
    const abort = () => localAbort.abort(signal?.reason);
    signal?.addEventListener('abort', abort, { once: true });
    let runner;
    if (this.controller) {
      job.claimed = true;
      runner = Promise.resolve().then(() => this.controller.run(job, event => this.record(job, event), localAbort.signal))
        .catch(error => { if (!job.terminal) this.record(job, { type: 'error', message: String(error.message).slice(0, 1800) }); });
    }
    try {
      while (this.now() - start - (job.responseLoadingPausedMs || 0) -
        (job.responseLoadingSince === undefined ? 0 : this.now() - job.responseLoadingSince) < job.timeoutMs) {
        signal?.throwIfAborted();
        while (cursor < job.events.length) {
          const event = job.events[cursor++];
          if (event.type === 'error') throw new Error(event.message);
          yield event;
          if (event.type === 'done') return;
        }
        if (!job.claimed && this.now() - start > this.connectionGraceMs) throw new Error('Browser extension not connected for this website. Load the extension, enable the website in its popup, and log in in Chrome.');
        await delay(100, undefined, { signal });
      }
      throw new Error('Website request timed out. Check the visible browser for login, usage limits, or a verification prompt.');
    } catch (error) {
      const diagnostic=recoveryDiagnostic(error,job);
      this.sessions.update(sessionId,{recovery:[...(this.sessions.get(sessionId)?.recovery||[]),diagnostic].slice(-20)});
      this.journal.append(sessionId,'recovery-diagnostic',diagnostic);
      this.journal.append(sessionId,signal?.aborted?'cancelled':'failed',{id:job.id,message:String(error.message)});
      this.sessions.update(sessionId, { phase: signal?.aborted ? 'cancelled' : 'error', message: String(error.message).slice(0, 500) });
      this.activity.status(sessionId,signal?.aborted?'cancelled':'error',String(error.message).slice(0,500),job.id);
      throw error;
    } finally {
      localAbort.abort(); signal?.removeEventListener('abort', abort);
      try { await runner; } finally { this.jobs.delete(job.id); }
    }
  }
  async close() {
    this.agui.closing=true;
    this.closing=true;
    this.scheduler.close();
    await this.imageJobs.close();
    await this.controller?.close();
    for (const job of this.jobs.values()) { job.events.push({ type: 'error', message: 'Browser bridge stopped.' }); job.terminal = true; }
    if (this.server) { this.server.closeAllConnections(); await new Promise(resolve => this.server.close(resolve)); }
  }
}
