import { websiteURL } from './session-store.mjs';
import { INTRODUCTION_VERSION } from './protocol.mjs';

/** Admission and idempotency for human messages from one explicitly enabled paired chat. */
export class TwoWayRelay {
  constructor(bridge) { this.bridge = bridge; this.inFlight = new Map(); this.queues = new Map(); }
  pair(input) {
    const state = this.bridge.sessions.get(input.sessionId);
    const pair = state?.pairs?.['chatgpt-web'];
    if (!state?.twoWay || !this.bridge.sessions.introductionReady(input.sessionId, 'chatgpt-web', INTRODUCTION_VERSION) ||
      input.site !== 'chatgpt-web' || !pair || pair.tabId !== input.tabId ||
      websiteURL(input.site, input.url) !== pair.url) throw new Error('Two-way access requires the enabled paired ChatGPT chat.');
    return state;
  }
  enable(sessionId, enabled) {
    if (typeof enabled !== 'boolean') throw new Error('Invalid two-way setting.');
    const state = this.bridge.sessions.get(sessionId);
    if (!state?.pairs?.['chatgpt-web']) throw new Error('Pair a ChatGPT conversation first.');
    if (enabled && !this.bridge.sessions.introductionReady(sessionId, 'chatgpt-web', INTRODUCTION_VERSION)) {
      throw new Error('Send one task from Harness first to initialize this ChatGPT conversation.');
    }
    const route = this.bridge.resolveAgent?.(sessionId)?.session?.requestHeader?.()?.config;
    if (enabled && route && (route.provider !== 'browser-web' || route.model !== 'chatgpt-web')) throw new Error('Select the ChatGPT browser model in Harness first.');
    this.bridge.sessions.update(sessionId, { twoWay: enabled }); return { ok: true, enabled };
  }
  async stop(input) {
    this.pair(input); const agent = this.bridge.resolveAgent?.(input.sessionId);
    if (input.jobId && this.bridge.jobs.get(input.jobId)?.sessionId !== input.sessionId) return { ok: true, stale: true };
    agent?.cancel({ kind: 'user' });
    this.bridge.sessions.update(input.sessionId, { phase: 'cancelled', message: 'Stopped from the paired ChatGPT chat' });
    return { ok: true };
  }
  accept(input) {
    this.pair(input);
    if (!/^[a-f0-9-]{36}$/i.test(input.id || '') || typeof input.text !== 'string' || !input.text.trim() || input.text.length > 80000) {
      throw new Error('Invalid ChatGPT message.');
    }
    const key = `${input.sessionId}:${input.id}`;
    if(input.fileIds!==undefined&&(!Array.isArray(input.fileIds)||input.fileIds.length>8||input.fileIds.some(id=>typeof id!=='string')))throw new Error('Invalid inbound attachments.');
    const attachments=(input.fileIds||[]).map(id=>{const file=this.bridge.files.get(id,input.sessionId);if(file.direction!=='from-website'||file.status==='uploading')throw new Error('Inbound attachment unavailable.');return this.bridge.files.public(file);});
    if (this.inFlight.has(key)) return this.inFlight.get(key);
    const previous = this.bridge.sessions.get(input.sessionId)?.webReceipts?.find(item => item.id === input.id);
    if (previous) return Promise.resolve({ ok: previous.status !== 'uncertain', duplicate: true, status: previous.status,
      ...(previous.status === 'uncertain' ? { error: 'Submission outcome is uncertain. Check the paired Harness chat; this message will not be submitted twice.' } : {}) });
    const prior = this.queues.get(input.sessionId) || Promise.resolve();
    const run = prior.catch(() => {}).then(async () => {
      this.pair(input);
      if (!this.bridge.resolveAgent?.(input.sessionId) && this.bridge.recoverSession) {
        const restored = await this.bridge.recoverSession(input.sessionId);
        if (restored.provider !== 'browser-web' || restored.model !== 'chatgpt-web') throw new Error('Select the ChatGPT browser model in Harness before receiving ChatGPT tasks. No prompt was submitted.');
      }
      const agent = this.bridge.resolveAgent?.(input.sessionId);
      if (!agent) throw new Error('Open the paired Harness conversation to reconnect its agent.');
      if (agent.status === 'running') { agent.cancel({ kind: 'user' }); await agent.whenIdle(); }
      const state = this.bridge.sessions.get(input.sessionId);
      this.bridge.journal?.append(input.sessionId,'website-user',{id:input.id,text:input.text,attachments});
      const receipts = [...(state.webReceipts || []), { id: input.id, status: 'accepted', at: Date.now() }].slice(-200);
      this.bridge.sessions.update(input.sessionId, { webReceipts: receipts, webPending: { id: input.id }, webActiveId: input.id,
        phase: 'waiting', message: 'Receiving your message from ChatGPT' });
      const stopErrors = agent.ctx?.on('agent/error', ({ error }) => {
        if (this.bridge.sessions.get(input.sessionId)?.webActiveId === input.id) this.bridge.sessions.update(input.sessionId, {
          phase: 'error', message: String(error?.message || 'Harness task failed; check its conversation.').slice(0, 500),
        });
      });
      try {
        agent.followup(Object.freeze({ id: input.id, role: 'user',
          source: Object.freeze({ kind: 'user', rpcId: input.id }),
          content: Object.freeze([Object.freeze({ type: 'text', text: input.text+attachments.map(file=>`\n\n[Website attachment ${file.name}, ${file.size} bytes. Saved copy: ${this.bridge.files.path(file.id,input.sessionId)||file.url}. Use Harness file tools to inspect it; the website already received this attachment.]`).join('') })]) }));
      } catch (error) {
        if (typeof stopErrors === 'function') stopErrors();
        this.bridge.sessions.update(input.sessionId, { webPending: null,
          webReceipts: receipts.map(item => item.id === input.id ? { ...item, status: 'uncertain' } : item),
          phase: 'error', message: 'Submission outcome is uncertain. Check the paired Harness chat before retrying.' });
        throw error;
      }
      if (typeof agent.whenIdle === 'function') void agent.whenIdle().finally(() => {
        if (typeof stopErrors === 'function') stopErrors();
      }).catch(() => {});
      return { ok: true, duplicate: false, status: 'accepted' };
    });
    this.inFlight.set(key, run); this.queues.set(input.sessionId, run);
    void run.finally(() => { this.inFlight.delete(key); if (this.queues.get(input.sessionId) === run) this.queues.delete(input.sessionId); }).catch(() => {});
    return run;
  }
  take(sessionId, messages) {
    const state = this.bridge.sessions.get(sessionId); const pending = state?.webPending;
    const human = messages?.findLast(message => message.role === 'user' && message.source?.kind === 'user');
    if (!pending || human?.source?.rpcId !== pending.id) return null;
    this.bridge.sessions.update(sessionId, { webPending: null }); return pending.id;
  }
  validateRoute(options) {
    const state = this.bridge.sessions.get(options.sessionId);
    const human = options.messages?.findLast(message => message.role === 'user' && message.source?.kind === 'user');
    if (state?.webActiveId && human?.source?.rpcId === state.webActiveId &&
      (options.provider !== 'browser-web' || options.model !== 'chatgpt-web')) {
      throw new Error('Two-way ChatGPT tasks require the ChatGPT browser model in Harness. No model API request was made.');
    }
  }
  listeners(bindings) {
    return bindings.filter(binding => binding.site === 'chatgpt-web').map(binding => {
      const state = this.bridge.sessions.get(binding.sessionId); const pair = state?.pairs?.[binding.site];
      if (!pair || pair.tabId !== binding.tabId) return null;
      const agent = this.bridge.resolveAgent?.(binding.sessionId);
      return { sessionId: binding.sessionId, site: binding.site, tabId: binding.tabId, url: pair.url,
        enabled: !!state.twoWay, status: !agent ? (this.bridge.recoverSession ? 'Harness is online — the saved conversation reconnects when you send a new message' : 'Open the paired Harness conversation to reconnect')
          : agent.status === 'running' ? (['queued','waiting','generating','receiving','uploading','reconnecting'].includes(state.phase) ? state.message : 'Harness is running tools')
          : state.phase === 'error' || state.phase === 'cancelled' ? state.message : 'Harness is ready — new messages here also go to Harness' };
    }).filter(Boolean);
  }
}
