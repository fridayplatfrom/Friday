import {createServer} from 'node:http';
import {readFileSync,realpathSync,statSync} from 'node:fs';
import {resolve,relative,extname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomBytes} from 'node:crypto';
const types={'.html':'text/html','.htm':'text/html','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml','.gif':'image/gif','.ico':'image/x-icon','.woff':'font/woff','.woff2':'font/woff2','.txt':'text/plain','.pdf':'application/pdf'};
export function webTarget(value){
 const input=String(value||'').trim();if(!input||input.length>8192)throw Error('Enter a website address.');
 if(/\s/.test(input))return 'https://www.google.com/search?q='+encodeURIComponent(input);
 const url=new URL(/^[a-z][a-z0-9+.-]*:/i.test(input)?input:'https://'+input);
 if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw Error('Only HTTP and HTTPS website addresses are supported. Use the Files tab for other files. No browser action was sent.');
 return url.href;
}
export function checkTaskOrigin(value,origins){const url=new URL(value);if(!origins.includes('*')&&!origins.includes(url.origin))throw Error('This website is not enabled in the task browser. No browser action was sent.');return url.href;}
export class WorkspacePreview{
 constructor(directory){this.directory=realpathSync(directory);this.secret=randomBytes(24).toString('hex');}
 path(urlPath){let decoded;try{decoded=decodeURIComponent(urlPath);}catch{throw Error('Invalid preview path.');}if(decoded.split('/').some(x=>x.startsWith('.')))throw Error('Hidden workspace files are not served.');const file=realpathSync(resolve(this.directory,'.'+decoded));const part=relative(this.directory,file);if(part.startsWith('..'+sep)||part==='..'||resolve(file)===resolve(this.directory)||!types[extname(file).toLowerCase()]||!statSync(file).isFile())throw Error('Preview file is outside this workspace or has an unsupported type.');return file;}
 async url(value){
  const file=realpathSync(fileURLToPath(value)),part=relative(this.directory,file).split(sep).join('/');this.path('/'+part);
  if(!this.server){this.server=createServer((req,res)=>{try{const url=new URL(req.url,'http://localhost');const prefix='/'+this.secret;if(!['GET','HEAD'].includes(req.method)||!url.pathname.startsWith(prefix+'/')){res.writeHead(404);return res.end();}const path=this.path(url.pathname.slice(prefix.length));const bytes=readFileSync(path);res.writeHead(200,{'Content-Type':types[extname(path).toLowerCase()]+'; charset=utf-8','X-Content-Type-Options':'nosniff','Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:bytes);}catch{res.writeHead(404);res.end('Preview file unavailable.');}});await new Promise((resolve,reject)=>{this.server.once('error',reject);this.server.listen(0,'127.0.0.1',resolve);});}
  return 'http://127.0.0.1:'+this.server.address().port+'/'+this.secret+'/'+part.split('/').map(encodeURIComponent).join('/');
 }
 close(){const server=this.server;this.server=null;return server?new Promise(resolve=>server.close(resolve)):Promise.resolve();}
}
