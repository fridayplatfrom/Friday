import { mkdirSync, readFileSync, writeFileSync, renameSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { SITES,INTRODUCTION_VERSION } from './protocol.mjs';
import {PROVIDERS} from './providers.mjs';

export function websiteURL(site, value) {
  try {
    const url = new URL(value);
    if (url.protocol!=='https:'||!PROVIDERS[site]?.selectors.hosts.includes(url.host)||url.username||url.password) return null;
    return url.origin + url.pathname; // Never persist login tokens or search parameters.
  } catch { return null; }
}

/** Session metadata and generated raster assets, local to the authenticated Harness owner. */
export class SessionStore {
  constructor(directory,{autoTwoWay=false}={}) {
    this.directory = directory; this.autoTwoWay=autoTwoWay;this.sessions = Object.create(null); this.media = new Map();
    if (directory) {
      mkdirSync(join(directory, 'media'), { recursive: true });
      const saved=join(directory,'sessions.json');
      if(existsSync(saved)){
        try {const parsed=JSON.parse(readFileSync(saved,'utf8'));if(!parsed||Array.isArray(parsed)||typeof parsed!=='object'||Object.values(parsed).some(value=>!value||typeof value!=='object'))throw new Error('Invalid saved state');Object.assign(this.sessions,parsed);}
        catch {throw new Error('Saved connector state is damaged. Preserve sessions.json and restore its backup; no state was erased.');}
      }
      for (const state of Object.values(this.sessions)) if (['queued','generating','waiting','receiving','uploading','reconnecting','executing','approval','question'].includes(state.phase)) {
        state.phase = 'interrupted'; state.message = 'Harness restarted. Review the last task before continuing; no action was automatically replayed.';
      }
      if(autoTwoWay)for(const state of Object.values(this.sessions))if(state.pairs?.['chatgpt-web']&&state.introductions?.['chatgpt-web']?.version===INTRODUCTION_VERSION)state.twoWay=true;
    }
  }
  get(id) { return this.sessions[id] || null; }
  introductionReady(id, site, version) { return this.get(id)?.introductions?.[site]?.version === version; }
  acknowledgeIntroduction(id, site, version) {
    this.update(id, { ...(this.autoTwoWay&&site==='chatgpt-web'?{twoWay:true}:{}),introductions: { ...this.get(id)?.introductions,
      [site]: { version, url: this.get(id)?.pairs?.[site]?.url || null, acknowledgedAt: Date.now() } } });
  }
  update(id, changes) {
    if (typeof id !== 'string' || !id || id.length > 200) throw new Error('Invalid Harness session ID.');
    const state = this.sessions[id] = { ...this.sessions[id], ...changes, sessionId: id, updatedAt: Date.now() };
    if (this.directory) {
      const file = join(this.directory, 'sessions.json');
      writeFileSync(file + '.tmp', JSON.stringify(this.sessions));
      if(existsSync(file))writeFileSync(file+'.bak',readFileSync(file));
      renameSync(file + '.tmp', file);
    }
    return state;
  }
  bind({ sessionId, site, url, tabId }) {
    const safe = websiteURL(site, url);
    if (!safe || !Number.isInteger(tabId)) throw new Error('Invalid website tab binding.');
    const previous = this.get(sessionId)?.pairs?.[site];
    if (previous?.url === safe && previous.tabId === tabId) return;
    const pairs = { ...this.get(sessionId)?.pairs, [site]: { site, url: safe, tabId } };
    const introductions = { ...this.get(sessionId)?.introductions };
    const introduction = introductions[site];
    if (site === 'chatgpt-web' && introduction) {
      const current = new URL(safe).pathname;
      const initialized = introduction.url && new URL(introduction.url).pathname;
      if (current.startsWith('/c/')) {
        if (!initialized || initialized === '/') introductions[site] = { ...introduction, url: safe };
        else if (introduction.url !== safe) delete introductions[site];
      } else if (current === '/' && initialized?.startsWith('/c/')) delete introductions[site];
    }
    if(site!=='chatgpt-web'&&introduction){
      const base=new URL(SITES[site].url).pathname,initialized=introduction.url&&new URL(introduction.url).pathname,current=new URL(safe).pathname;
      if(!initialized||initialized===base)introductions[site]={...introduction,url:safe};
      else if(initialized!==current)delete introductions[site];
    }
    this.update(sessionId, { pairs, introductions,
      ...(previous&&previous.url!==safe?{providerContexts:Object.fromEntries(Object.entries(this.get(sessionId)?.providerContexts||{}).filter(([key])=>key!==site)),...(this.get(sessionId)?.contextCheckpoint?.site===site?{contextCheckpoint:null}:{})}:{}),
      ...(introduction && !introductions[site] ? { twoWay: false,contextCheckpoint:null } : {}),
      ...(!this.get(sessionId)?.site ? { site, phase: 'paired' } : {}) });
  }
  saveImage(bytes, mime, alt = 'Generated image') {
    const png = bytes.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex'));
    const jpg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
    const webp = bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP';
    const ext = mime === 'image/png' && png ? 'png' : mime === 'image/jpeg' && jpg ? 'jpg' : mime === 'image/webp' && webp ? 'webp' : null;
    if (!ext || bytes.length > 16 * 1024 * 1024) throw new Error('Invalid or oversized raster image.');
    const id = `${randomUUID()}.${ext}`;
    if (this.directory) writeFileSync(join(this.directory, 'media', id), bytes);
    else this.media.set(id, bytes);
    return { id, url: `/browser-models/media/${id}`, mime, alt: String(alt).slice(0, 160) };
  }
  readImage(id) {
    if (!/^[a-f0-9-]{36}\.(png|jpg|webp)$/.test(id)) return null;
    try {
      const bytes = this.directory ? readFileSync(join(this.directory, 'media', id)) : this.media.get(id);
      return bytes ? { bytes, mime: id.endsWith('.png') ? 'image/png' : id.endsWith('.jpg') ? 'image/jpeg' : 'image/webp' } : null;
    } catch { return null; }
  }
  imagePath(id){return this.directory&&/^[a-f0-9-]{36}\.(png|jpg|webp)$/.test(id)?join(this.directory,'media',id):null;}
}
