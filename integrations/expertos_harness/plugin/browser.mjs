/** Isolated, no-submit browser workflow powered by Playwright.
 * A fresh browser/context is created per task. No session cookies are shared.
 */
import net from 'node:net';

const PUBLIC_SCHEMES = new Set(['https:']);
const UNSAFE_LABEL = /(password|passcode|otp|captcha|cvv|credit card|bank account|aadhaar|social security|upi pin)/i;
const SAFE_TYPES = new Set(['text','textarea','search','email','tel','url','number','select']);

export function assertAllowedUrl(input, allowHosts = [], allowTestLoopback = false) {
  let url;
  try { url = new URL(input); } catch { throw new Error('Invalid URL'); }
  if (url.username || url.password || url.hash || !url.hostname) throw new Error('URL credentials/fragments are forbidden');
  if (url.protocol === 'http:' && allowTestLoopback && url.hostname === '127.0.0.1' && ['80','3000','3080','8000','8001',''].includes(url.port)) {
    return url;
  }
  if (!PUBLIC_SCHEMES.has(url.protocol) || (url.port && url.port !== '443')) throw new Error('Only HTTPS port 443 is permitted');
  if (url.hostname === 'localhost' || net.isIP(url.hostname) || !allowHosts.includes(url.hostname)) {
    throw new Error('Blocked hostname; add the exact hostname to EXPERTOS_ALLOWED_HOSTS');
  }
  return url;
}

export async function observeControls(page) {
  // Page content is untrusted; this function returns data, never instructions.
  return page.locator('input, textarea, select').evaluateAll((elements) => elements.slice(0, 200).map((element, index) => {
    const html = element;
    const id = html.id || '';
    let label = html.getAttribute('aria-label') || '';
    if (!label && id) {
      const lab = [...document.querySelectorAll('label[for]')].find(x => x.htmlFor === id);
      label = lab?.textContent?.trim() || '';
    }
    if (!label) label = html.closest('label')?.textContent?.trim() || '';
    return { index, id, name: html.getAttribute('name') || '',
      label: label.slice(0, 250), placeholder: (html.getAttribute('placeholder') || '').slice(0, 250),
      aria_label: html.getAttribute('aria-label') || '',
      type: (html.getAttribute('type') || html.tagName.toLowerCase()).toLowerCase(),
      tag: html.tagName.toLowerCase(), disabled: html.disabled || false,
      visible: !!(html.getClientRects().length),
    };
  }));
}

function sameIdentity(a, b) {
  return ['id', 'name', 'type', 'label'].every(key => (a?.[key] || '') === (b?.[key] || ''));
}

export async function runBrowserWorkflow({ url, kind = 'extract', values = {}, allowHosts = [],
  allowTestLoopback = false, client, playwrightLoader = () => import('playwright'), signal }) {
  const parsed = assertAllowedUrl(url, allowHosts, allowTestLoopback);
  if (kind !== 'extract' && kind !== 'fill_form') throw new Error('Supported browser tasks are extract and fill_form only');
  if (kind === 'fill_form' && (!values || typeof values !== 'object' || Array.isArray(values) || Object.keys(values).length > 50)) {
    throw new Error('Invalid form values');
  }
  const planned = await client.request('/v1/plan', { kind, url: parsed.href, values }, signal);
  if (planned.status !== 'planned') return { status: 'abstained', reason: 'plan_rejected' };
  let browser;
  try {
    const { chromium } = await playwrightLoader();
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ acceptDownloads: false, serviceWorkers: 'block',
      permissions: [], javaScriptEnabled: true });
    await context.route('**/*', async (route) => {
      try { assertAllowedUrl(route.request().url(), allowHosts, allowTestLoopback); await route.continue(); }
      catch { await route.abort(); }
    });
    const page = await context.newPage();
    if (signal?.aborted) throw new Error('Cancelled before navigation');
    await page.goto(parsed.href, { waitUntil: 'domcontentloaded', timeout: 15000 });
    if (page.url() !== parsed.href) assertAllowedUrl(page.url(), allowHosts, allowTestLoopback);
    if (kind === 'extract') {
      const text = (await page.locator('body').innerText({ timeout: 8000 })).slice(0, 8000);
      return { status: 'extracted', source_url: page.url(), text, verified: false,
        note: 'Untrusted page text; extraction is not fact verification.' };
    }
    const controls = await observeControls(page);
    const mapped = await client.request('/v1/form/map', { controls, values }, signal);
    const filled = [], blocked = [], actualFilled = {};
    for (const match of mapped.matches || []) {
      if (signal?.aborted) throw new Error('Cancelled');
      const before = controls[match.index];
      const current = (await observeControls(page))[match.index];
      const key = match.key;
      if (!before || !sameIdentity(before, current) || !SAFE_TYPES.has(current.type)
          || UNSAFE_LABEL.test([current.label, current.name, current.id, current.placeholder, key].join(' '))) {
        blocked.push({ key, reason: 'control_changed_or_sensitive' });
        continue;
      }
      const control = page.locator('input, textarea, select').nth(match.index);
      if (current.tag === 'select') {
        // Select only an explicit option value; no fuzzy auto-selection.
        await control.selectOption({ value: values[key] }, { timeout: 4000 });
      } else {
        await control.fill(values[key], { timeout: 4000 });
      }
      const stored = await control.inputValue();
      if (stored !== values[key]) blocked.push({ key, reason: 'verification_mismatch' });
      else { filled.push(key); actualFilled[key] = stored; }
    }
    const result = await client.request('/v1/form/verify', {
      expected: Object.fromEntries(filled.map(k => [k, values[k]])),
      actual: actualFilled,
    }, signal);
    return { status: blocked.length || (mapped.unmatched || []).length ? 'partial' : 'verified',
      verified: result.verified && !blocked.length && !(mapped.unmatched || []).length,
      filled_keys: filled, blocked, unmatched: mapped.unmatched || [],
      form_submitted: false, screenshot_saved: false, page_url: page.url(),
      note: 'Input values were checked after fill; no submit/click action is available.' };
  } finally {
    if (browser) await browser.close();
  }
}
