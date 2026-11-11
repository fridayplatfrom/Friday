import { chromium } from 'playwright-core';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { SITES, isResponseLoadPlaceholder } from './protocol.mjs';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const UI = {
  'chatgpt-web': { composer: ['#prompt-textarea', '#mobile-composer-prompt', '[contenteditable="true"][role="textbox"][aria-label="Ask ChatGPT"]'],
    send: ['button[aria-label="Send"]', 'button[data-testid="send-button"]', 'button[aria-label="Send prompt"]', 'button[aria-label="Send message"]'],
    response: ['[data-message-author-role="assistant"]', '[data-markdown-text-style="assistant-message"]'],
    stop: ['button[data-testid="stop-button"]', 'button[aria-label="Stop generating"]', 'button[aria-label="Stop streaming"]'] },
  'gemini-web': { composer: ['rich-textarea [contenteditable="true"]'], send: ['button.send-button', 'button[aria-label="Send message"]'],
    response: ['model-response .model-response-text', 'model-response message-content'], stop: ['button[aria-label="Stop response"]'] },
  'deepseek-web': { composer: ['textarea'], send: ['button[aria-label="Send"]', '[role="button"][aria-label="Send"]'],
    response: ['.ds-markdown'], stop: ['button[aria-label="Stop"]', '[role="button"][aria-label="Stop"]'] },
  'kimi-web': { composer: ['.chat-input-editor[contenteditable="true"]', '[contenteditable="true"][role="textbox"]', 'textarea'],
    send: ['button[aria-label="Send"]', '.send-button'], response: ['.segment-assistant .markdown', '[data-role="assistant"]'], stop: ['button[aria-label="Stop"]', '.stop-button'] },
};

/** First-party application worker. Uses only visible page controls, never cookies or private APIs. */
export class BrowserDriver {
  constructor({ profileDir = join(homedir(), '.dsh', 'browser-connector', 'browser-profile'),
    executablePath = process.platform === 'win32' ? join(process.env.ProgramFiles || 'C:/Program Files', 'Google', 'Chrome', 'Application', 'chrome.exe') : undefined,
    preferencesFile = join(homedir(), '.dsh', 'browser-connector', 'preferences.json') } = {}) {
    Object.assign(this, { profileDir, executablePath, preferencesFile }); this.context = null; this.page = null;
    this.site = null; this.enabled = false; this.busy = false; this.requests = 0; this.characters = 0;
    this.sessionId = null; this.phase = 'Disconnected'; this.lastError = ''; this.generation = 0;
    this.autoConnect = true; this.opening = false;
    this.verified = false; this.testReply = '';
  }
  async savePreferences() {
    await mkdir(dirname(this.preferencesFile), { recursive: true });
    await writeFile(this.preferencesFile, JSON.stringify({ site: this.site, autoConnect: this.autoConnect }) + '\n');
  }
  async start() {
    let preferred = 'chatgpt-web';
    try {
      const saved = JSON.parse(await readFile(this.preferencesFile, 'utf8'));
      if (Object.hasOwn(SITES, saved.site)) preferred = saved.site;
      this.autoConnect = saved.autoConnect !== false;
    } catch (error) { if (error.code !== 'ENOENT') { this.lastError = 'Could not read saved connection preferences.'; return; } }
    if (!this.autoConnect) return;
    try { await this.open(preferred); }
    catch { /* Failure stays visible in Models; never prevent Harness startup. */ }
  }
  async checkReady() {
    if (!this.autoConnect || this.busy || this.opening || !this.page || this.page.isClosed()) return false;
    if (new URL(this.page.url()).origin !== new URL(SITES[this.site].url).origin) {
      this.enabled = false; this.phase = 'Website sign-in or navigation needs attention'; return false;
    }
    const ready = !!await this.first(UI[this.site].composer, { editable: true });
    this.enabled = ready;
    this.phase = ready ? (this.lastError ? 'Needs attention' : this.verified ? 'Connected' : 'Chat editor ready · reply untested') : 'Waiting for the website chat editor';
    return ready;
  }
  watchReadiness() {
    clearInterval(this.readinessTimer);
    this.readinessTimer = setInterval(() => { void this.checkReady().catch(() => {}); }, 2000);
    this.readinessTimer.unref?.();
  }
  async disconnect() {
    this.autoConnect = false; await this.savePreferences(); return this.close();
  }
  async testConnection() {
    let reply = '';
    await this.run({ id: 'connection-check', site: this.site, sessionId: this.sessionId || 'connection-check',
      prompt: 'Reply exactly HARNESS_CONNECTION_OK. Do not use any tools.' }, event => {
      if (event.type === 'done') reply = event.text;
    }, AbortSignal.timeout(45000));
    this.testReply = reply.slice(0, 500);
    return this.status();
  }
  status() { return { transport: 'builtin', site: this.site, enabled: this.enabled, busy: this.busy || this.opening, autoConnect: this.autoConnect,
    verified: this.verified, testReply: this.testReply,
    phase: this.phase, lastError: this.lastError, requests: this.requests, characters: this.characters,
    tabs: this.context?.pages().filter(page => !page.isClosed()).length || 0,
    browserOpen: !!this.page && !this.page.isClosed() }; }
  isConnected(site) { return this.enabled && this.site === site && !!this.page && !this.page.isClosed(); }
  async open(site) {
    if (!Object.hasOwn(SITES, site)) throw new Error('Choose a supported website.');
    if (this.busy || this.opening) throw new Error('Finish or cancel the current task first.');
    this.opening = true;
    this.enabled = false; this.lastError = ''; this.phase = 'Opening browser';
    try {
      if (!this.context) {
        this.context = await chromium.launchPersistentContext(this.profileDir, { executablePath: this.executablePath,
          headless: false, chromiumSandbox: true, viewport: null, args: ['--start-maximized'] });
        this.context.on('close', () => { this.context = null; this.page = null; this.enabled = false; this.phase = 'Browser closed'; });
      }
      if (!this.page || this.page.isClosed()) this.page = this.context.pages()[0] || await this.context.newPage();
      this.site = site; this.autoConnect = true; await this.savePreferences();
      this.verified = false; this.testReply = '';
      this.requests = 0; this.characters = 0; this.sessionId = null;
      await this.page.goto(SITES[site].url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await this.page.bringToFront(); this.phase = 'Waiting for the website chat editor';
      this.opening = false; this.watchReadiness(); await this.checkReady();
      return this.status();
    } catch (error) { this.lastError = error.message; this.phase = 'Could not open browser'; throw error; }
    finally { this.opening = false; }
  }
  async first(selectors, { editable = false } = {}) {
    for (const selector of selectors) {
      const locator = this.page.locator(selector).filter({ visible: true }).first();
      if (await locator.count() && (!editable || await locator.isEditable())) return locator;
    }
    return null;
  }
  async waitForSend(signal, timeoutMs = 15000) {
    const until = Date.now() + timeoutMs;
    while (Date.now() < until) {
      signal?.throwIfAborted();
      const button = await this.first(UI[this.site].send);
      if (button && await button.isEnabled()) return button;
      await sleep(100);
    }
    throw new Error('Website send control not ready. Draft left visible.');
  }
  async connect(site) {
    if (this.busy) throw new Error('Finish or cancel the current task first.');
    if (site !== this.site || !this.page || this.page.isClosed()) throw new Error('Open this website first.');
    if (new URL(this.page.url()).origin !== new URL(SITES[site].url).origin) throw new Error('Return to the provider chat page. Complete sign-in only if the website requires it.');
    if (!await this.first(UI[site].composer, { editable: true })) throw new Error('Chat editor not detected yet. The page may still be loading, show a dialog, or use an unsupported layout. Login is required only if the website asks for it.');
    this.enabled = true; this.phase = this.verified ? 'Connected' : 'Chat editor ready · reply untested'; this.lastError = ''; return this.status();
  }
  async resetConversation() {
    if (this.busy) throw new Error('Finish or cancel the current task first.');
    if (!this.page || this.page.isClosed()) throw new Error('Open a website first.');
    await this.fresh(); return this.status();
  }
  async fresh() {
    const composer = await this.first(UI[this.site].composer, { editable: true });
    if (composer && (await composer.evaluate(e => e.value || e.innerText || '')).trim()) throw new Error('The website has an unsent draft. Clear it yourself before starting a fresh conversation.');
    const button = this.page.getByRole('button', { name: 'New chat', exact: true }).filter({ visible: true }).first();
    if (await button.count()) await button.click({ timeout: 10000 });
    else await this.page.goto(SITES[this.site].url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    this.requests = 0; this.characters = 0; this.generation++;
    await sleep(1000);
  }
  async pageState() {
    const state = await this.page.evaluate(preset => {
      const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
      const matching = selectors => { for (const selector of selectors) { const nodes = [...document.querySelectorAll(selector)].filter(visible); if (nodes.length) return nodes; } return []; };
      return {
        responses: matching(preset.response).map((node, index) => ({
          key: node.closest('[data-chatgpt-selection-message-id]')?.getAttribute('data-chatgpt-selection-message-id') || node.getAttribute('data-message-id') || String(index),
          text: (node.innerText || '').trim(),
          complete: !!node.closest('[data-talvt-turn-state="complete"]') || !!node.closest('article,model-response,.segment-assistant')?.querySelector('button[aria-label*="Copy"],button[data-testid="copy-turn-action-button"]'),
        })),
        stopped: matching(preset.stop).length === 0,
        error: [...document.querySelectorAll('[role="alert"],[role="status"]')].filter(visible).map(node => node.innerText || '')
          .find(text => /your account changed|something went wrong|too many requests|reached.{0,30}limit|try again later/i.test(text)) || '',
      };
    }, UI[this.site]);
    if (this.site === 'chatgpt-web') {
      // Signed-out /uc chats use named regions inside UUID list items, rather
      // than the older assistant-message attributes. Read only the response
      // region, excluding the user prompt and surrounding action labels.
      const mobile = await this.page.getByRole('region', { name: 'DIL content', exact: true }).evaluateAll(nodes =>
        nodes.filter(node => node.getClientRects().length).map((node, index) => {
          const turn = node.closest('li');
          return { key: turn?.id || `mobile-${index}`, text: (node.innerText || '').trim(),
            complete: !!turn && [...turn.querySelectorAll('button')].some(button =>
              button.getClientRects().length && /Copy response/i.test(button.getAttribute('aria-label') || button.textContent || '')) };
        }));
      if (mobile.length) state.responses = mobile;
    }
    return state;
  }
  async run(job, publish, signal) {
    if (!this.isConnected(job.site)) throw new Error('Open Settings → Models, open the website, and click Connect.');
    if (this.busy) throw new Error('The managed browser is busy.');
    this.busy = true; this.stopRequested = false;
    const start = Date.now();
    try {
      if ((this.sessionId && this.sessionId !== job.sessionId) || this.requests >= 6 || this.characters >= 160000) await this.fresh();
      this.sessionId = job.sessionId; this.phase = 'Preparing request';
      let composer;
      while (Date.now() - start < 45000) {
        signal?.throwIfAborted();
        composer = await this.first(UI[this.site].composer, { editable: true });
        if (composer) break;
        await sleep(500);
      }
      if (!composer) throw new Error('Website chat editor unavailable. Check the page for a dialog, verification, or changed layout.');
      if ((await composer.evaluate(e => e.value || e.innerText || '')).trim()) throw new Error('Website has an unsent draft. Nothing was overwritten.');
      const before = await this.pageState();
      if (!before.stopped) throw new Error('Website is already generating.');
      const baseline = new Set(before.responses.map(response => response.key));
      await composer.fill(job.prompt, { timeout: 15000 });
      const send = await this.waitForSend(signal);
      await send.click({ timeout: 15000 }); this.phase = 'Waiting for website';
      let text = ''; let changed = Date.now(); let observedStop = false; let retriedAccount = false; let accountRetryAt = 0;
      let loadingSince = null; let loadingPausedMs = 0; let loadingStatusAt = 0;
      while (Date.now() - start - loadingPausedMs - (loadingSince === null ? 0 : Date.now() - loadingSince) < 300000) {
        signal?.throwIfAborted();
        if (this.stopRequested || !this.enabled) throw new Error('Browser connection stopped.');
        const state = await this.pageState();
        const latest = state.responses.findLast(response => !baseline.has(response.key));
        const placeholder = isResponseLoadPlaceholder(latest?.text);
        if (placeholder || (loadingSince !== null && !latest?.text && state.stopped)) {
          const firstWait = loadingSince === null;
          if (firstWait) loadingSince = Date.now();
          this.phase = 'Response couldn’t load — waiting to load';
          if (firstWait || Date.now() - loadingStatusAt >= 5000) {
            publish({ id: job.id, type: 'status', state: 'response-loading' }); loadingStatusAt = Date.now();
          }
          await sleep(500); continue;
        }
        if (loadingSince !== null) {
          loadingPausedMs += Date.now() - loadingSince; loadingSince = null; changed = Date.now();
          publish({ id: job.id, type: 'status', state: 'receiving' });
        }
        if (state.error) {
          if (/your account changed/i.test(state.error) && retriedAccount && Date.now() - accountRetryAt < 8000) { await sleep(500); continue; }
          if (/your account changed/i.test(state.error) && !retriedAccount && !text) {
            retriedAccount = true; this.phase = 'Recovering website account refresh';
            const retry = this.page.getByRole('button', { name: 'Retry', exact: true }).filter({ visible: true }).first();
            if (await retry.count()) await retry.click({ timeout: 10000 });
            await sleep(2000);
            const draft = await this.first(UI[this.site].composer, { editable: true });
            const value = draft && await draft.evaluate(e => e.value || e.innerText || '');
            if (value?.trim()) {
              if (value.replace(/\s/g, '') !== job.prompt.replace(/\s/g, '')) throw new Error('Website draft changed during recovery. Nothing was resubmitted.');
              const retrySend = await this.waitForSend(signal);
              await retrySend.click({ timeout: 10000 });
            }
            accountRetryAt = Date.now(); await sleep(1000); continue;
          }
          throw new Error(`Website reported: ${state.error.slice(0, 350)}`);
        }
        if (!state.stopped) observedStop = true;
        if (latest?.text && latest.text !== text) {
          text = latest.text; changed = Date.now(); this.phase = 'Receiving reply';
          publish({ id: job.id, type: 'snapshot', text });
        }
        if (text && state.stopped && Date.now() - changed > 1800 && (observedStop || latest?.complete)) {
          this.requests++; this.characters += job.prompt.length; this.phase = 'Connected'; this.lastError = ''; this.verified = true;
          publish({ id: job.id, type: 'done', text }); return;
        }
        await sleep(500);
      }
      throw new Error('Website request timed out. Check the visible browser.');
    } catch (error) { this.lastError = error.message; this.phase = 'Needs attention'; throw error; }
    finally {
      if (signal?.aborted || this.stopRequested) {
        try { await (await this.first(UI[this.site].stop))?.click({ timeout: 2000 }); } catch {}
      }
      this.busy = false;
    }
  }
  async close() {
    clearInterval(this.readinessTimer);
    this.enabled = false; this.stopRequested = true;
    const closing = this.context;
    if (closing) await closing.close();
    if (this.context === closing) { this.context = null; this.page = null; }
    this.phase = 'Disconnected'; return this.status();
  }
}
