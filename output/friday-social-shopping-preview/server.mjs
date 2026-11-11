import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const root = import.meta.dirname;
http.createServer((req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname;
  const file = path.resolve(root, '.' + (name === '/' ? '/index.html' : name));
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(file, (error, data) => {
    if (error) { res.writeHead(404).end(); return; }
    res.setHeader('Content-Type', ({'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript'})[path.extname(file)] || 'application/octet-stream');
    res.end(data);
  });
}).listen(8987, '127.0.0.1', () => console.log('Friday concept: http://127.0.0.1:8987'));
