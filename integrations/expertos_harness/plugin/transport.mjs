/** Loopback-only token-authenticated transport to the Python expert bridge. */
export class ExpertBridgeClient {
  constructor({ baseUrl = 'http://127.0.0.1:8765', token, fetchImpl = globalThis.fetch, timeoutMs = 10000 } = {}) {
    const url = new URL(baseUrl);
    if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
      throw new Error('ExpertOS bridge may only use an explicit 127.0.0.1 HTTP endpoint');
    }
    if (typeof token !== 'string' || token.length < 32) throw new Error('EXPERTOS_BRIDGE_TOKEN must have 32+ characters');
    this.baseUrl = url.origin;
    this.token = token;
    this.fetchImpl = fetchImpl;
    this.timeoutMs = timeoutMs;
  }
  async request(path, payload = undefined, signal = undefined) {
    if (!/^\/(health|v1\/(experts|route|plan|recover|action\/propose|form\/(map|verify)|source\/read))$/.test(path)) {
      throw new Error('Unknown ExpertOS API route');
    }
    const body = payload === undefined ? undefined : JSON.stringify(payload);
    if (body && Buffer.byteLength(body, 'utf8') > 96000) throw new Error('Request too large');
    const controller = new AbortController();
    const stop = () => controller.abort();
    signal?.addEventListener?.('abort', stop, { once: true });
    const timeout = setTimeout(stop, this.timeoutMs);
    try {
      const response = await this.fetchImpl(this.baseUrl + path, {
        method: body === undefined ? 'GET' : 'POST',
        headers: {
          Authorization: `Bearer ${this.token}`,
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        },
        body,
        signal: controller.signal,
        redirect: 'error',
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`ExpertOS bridge returned HTTP ${response.status}`);
      const text = await response.text();
      if (text.length > 262144) throw new Error('Bridge returned excessive data');
      const result = JSON.parse(text);
      if (!result || typeof result !== 'object' || Array.isArray(result)) throw new Error('Invalid bridge response');
      return result;
    } finally {
      clearTimeout(timeout);
      signal?.removeEventListener?.('abort', stop);
    }
  }
}
