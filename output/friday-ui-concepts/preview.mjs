// Local static preview only: no API, persistence, provider connection or actions.
import http from 'node:http';
import fs from 'node:fs';
const root = new URL('./', import.meta.url);
const names = new Set(['kimi-recovered.html','chatgpt.html','gemini.html','deepseek.html','index.html']);
http.createServer((req,res)=>{
  const name = new URL(req.url,'http://localhost').pathname.slice(1)||'index.html';
  if(!['GET','HEAD'].includes(req.method)||!names.has(name)) { res.writeHead(404);res.end('Not found');return; }
  try {
    const bytes=fs.readFileSync(new URL(name,root));
    res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'; frame-src 'self'; form-action 'none'; base-uri 'none'",'X-Content-Type-Options':'nosniff'});
    res.end(req.method==='HEAD'?undefined:bytes);
  } catch {res.writeHead(404);res.end('This concept is not available yet.');}
}).listen(8768,'127.0.0.1',()=>console.log('UI-only previews: http://127.0.0.1:8768/kimi-recovered.html'));
