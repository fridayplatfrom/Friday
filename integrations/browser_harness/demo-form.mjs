import http from 'node:http';
import {persistenceFixture} from './browser-persistence-fixture.mjs';

const escape = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const shell = body => `<!doctype html><html lang="en"><meta charset="utf-8"><title>Harness Form Test</title>
<style>body{font:16px system-ui;max-width:650px;margin:50px auto;padding:25px;background:#f6f7fa;color:#182334}label{display:block;margin:18px 0}input:not([type=checkbox]),select,textarea{display:block;width:95%;padding:10px;margin-top:7px;border:1px solid #9caabc;border-radius:5px}button{padding:12px 20px;background:#245ca7;color:white;border:0;border-radius:6px}pre{white-space:pre-wrap;background:white;padding:20px}</style>${body}</html>`;
export class DemoFormServer {
  constructor({ port = 8767 } = {}) { this.port = port; this.result = null; this.submissions = 0; }
  async start() {
    this.server = http.createServer((req, res) => this.handle(req, res).catch(() => { res.writeHead(400); res.end('Invalid demo request'); }));
    await new Promise((resolve, reject) => { this.server.once('error', reject); this.server.listen(this.port, '127.0.0.1', resolve); });
    this.port = this.server.address().port; return this;
  }
  async handle(req, res) {
    if (req.headers.host !== `127.0.0.1:${this.port}`) { res.writeHead(403); return res.end(); }
    if(req.headers.origin&&req.headers.origin!==`http://127.0.0.1:${this.port}`){res.writeHead(403);return res.end();}
    if(persistenceFixture(req,res))return;
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'");
    if (req.method === 'GET' && req.url === '/result') {
      res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ submissions: this.submissions, result: this.result }));
    }
    if (req.method === 'GET' && (req.url === '/' || req.url === '/form')) {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      return res.end(shell(`<h1>Local Harness automation test</h1><p>This demonstration stores fictitious test data only in local memory. It sends no emails.</p>
<form action="/submit" method="post"><label>Name<input name="name" required></label>
<label>Email<input name="email" type="email" required></label>
<label>Topic<select name="topic"><option value="physics">Physics</option><option value="browser-automation">Browser automation</option><option value="coding">Coding</option></select></label>
<label>Notes<textarea name="notes" rows="3"></textarea></label>
<label><input name="testData" type="checkbox" value="yes" required> I confirm this is test data</label>
<button type="submit">Save demo request</button></form>`));
    }
    if (req.method === 'POST' && req.url === '/submit') {
      if (req.headers.origin && req.headers.origin !== `http://127.0.0.1:${this.port}`) { res.writeHead(403); return res.end(); }
      let body = '';
      for await (const part of req) { body += part.toString('utf8'); if (body.length > 4096) throw new Error('Oversize'); }
      const fields = new URLSearchParams(body);
      if (!fields.get('name') || !fields.get('email')?.includes('@') || fields.get('testData') !== 'yes' ||
        !['physics', 'browser-automation', 'coding'].includes(fields.get('topic'))) throw new Error('Invalid fields');
      this.result = Object.fromEntries(['name', 'email', 'topic', 'notes', 'testData'].map(key => [key, fields.get(key) || ''])); this.submissions++;
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      return res.end(shell(`<h1>Demo request saved</h1><p id="status">Submission ${this.submissions} accepted locally.</p><pre>${escape(JSON.stringify(this.result, null, 2))}</pre><a href="/form">Open another demo form</a>`));
    }
    res.writeHead(404); res.end('Not found');
  }
  async close() { this.server.closeAllConnections(); await new Promise(resolve => this.server.close(resolve)); }
}
