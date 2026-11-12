import {existsSync,mkdirSync,readFileSync,writeFileSync,renameSync} from 'node:fs';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {createHash} from 'node:crypto';
export const fixtureBytes=Buffer.from('FRIDAY_NATIVE_TRANSFER_TEST_20261112\nSynthetic test data only.\n');
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/** Local fictional account; raw POST counters deliberately do not deduplicate. */
export async function nativeBrowserFixture(req,res,{root=join(homedir(),'.dsh/browser-connector/test-evidence/native-browser')}={}){
 const url=new URL(req.url,'http://127.0.0.1'),match=url.pathname.match(/^\/_browser-test\/([a-z0-9-]{1,64})(\/[^]*)?$/);
 if(!match)return false;
 const [,run,suffix='']=match,base='/_browser-test/'+run,file=join(root,run+'.json');
 const state=existsSync(file)?JSON.parse(readFileSync(file,'utf8')):{run,signIns:0,formSubmissions:0,uploads:[],downloads:0};
 const save=()=>{mkdirSync(root,{recursive:true});writeFileSync(file+'.tmp',JSON.stringify(state,null,2));renameSync(file+'.tmp',file);};
 const signedIn=(req.headers.cookie||'').split(';').some(value=>value.trim()==='friday_native_fixture='+run);
 const reply=(code,type,body)=>{res.writeHead(code,{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(body);return true;};
 const redirect=()=>{res.writeHead(303,{Location:base});res.end();return true;};
 const read=async()=>{const chunks=[];let size=0;for await(const part of req){size+=part.length;if(size>1024*1024)throw Error('Test payload too large');chunks.push(part);}return Buffer.concat(chunks);};
 if(req.method==='POST'&&suffix==='/sign-in'){
  state.signIns++;save();res.setHeader('Set-Cookie',`friday_native_fixture=${run}; HttpOnly; SameSite=Strict; Max-Age=604800; Path=${base}`);return redirect();
 }
 if(req.method==='POST'&&suffix==='/submit'&&signedIn){
  const fields=new URLSearchParams((await read()).toString());
  if(fields.get('name')!=='Friday Test User'||fields.get('email')!=='friday@example.invalid'||fields.get('confirm')!=='yes')return reply(400,'text/plain','Use fictional test values only');
  state.formSubmissions++;state.form=Object.fromEntries(fields);save();return redirect();
 }
 if(req.method==='POST'&&suffix==='/upload'&&signedIn){
  const data=await new Request('http://fixture/upload',{method:'POST',headers:{'Content-Type':req.headers['content-type']||''},body:await read()}).formData();
  const upload=data.get('file');if(!upload||typeof upload.arrayBuffer!=='function')return reply(400,'text/plain','Missing test file');
  const bytes=Buffer.from(await upload.arrayBuffer());state.uploads.push({name:upload.name,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});save();return redirect();
 }
 if(req.method==='GET'&&suffix==='/download'){
  state.downloads++;save();res.setHeader('Content-Disposition','attachment; filename="friday-native-download.txt"');return reply(200,'text/plain',fixtureBytes);
 }
 if(req.method==='GET'&&suffix==='/state')return reply(200,'application/json',JSON.stringify({...state,signedIn,expectedSha256:createHash('sha256').update(fixtureBytes).digest('hex')}));
 if(req.method!=='GET'||!['','/details','/secondary'].includes(suffix))return reply(404,'text/plain','Unknown test operation');
 res.setHeader('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'");
 return reply(200,'text/html; charset=utf-8',`<!doctype html><html lang="en"><meta charset="utf-8"><title>Friday ${suffix==='/secondary'?'second tab':suffix==='/details'?'link details':'native browser test'} · ${run}</title><style>body{font:16px system-ui;background:#202023;color:#eee;max-width:740px;margin:35px auto;padding:20px}a{color:#c4b3f1;margin-right:20px}label{display:block;margin:12px 0}input,select,textarea,button{padding:9px;background:#303035;color:#eee;border:1px solid #777;border-radius:8px}input:not([type=checkbox]),textarea{display:block;width:95%}button{cursor:pointer;background:#b8a2e5;color:#17141d}section{border-top:1px solid #555;margin:20px 0;padding:12px 0}strong{color:#c4b3f1}</style><h1>Friday native browser test</h1><p>Fictional local account. No external posts, purchases, emails or personal files.</p><p role="status">${signedIn?'Signed in as Fictional Friday Tester':'Signed out'}</p><p>Run: ${escape(run)} · Form submissions: <strong>${state.formSubmissions}</strong> · Uploads: <strong>${state.uploads.length}</strong> · Downloads: <strong>${state.downloads}</strong></p>${suffix?`<h2>${suffix==='/secondary'?'Second tab opened':'Link click succeeded'}</h2><a href="${base}">Back to test page</a>`:`<p><a href="${base}/details">Open link details</a><a href="${base}/secondary" target="_blank" rel="noopener">Open second tab</a></p>${!signedIn?`<form action="${base}/sign-in" method="post"><button>Use fictional test account</button></form>`:`<section><form method="post" action="${base}/submit"><label>Name<input name="name" required></label><label>Email<input type="email" name="email" required></label><label>Topic<select name="topic"><option>Browser testing</option><option>Uploads and downloads</option></select></label><label>Notes<textarea name="notes"></textarea></label><label><input type="checkbox" name="confirm" value="yes" required> I confirm this is fictional test data</label><button>Submit test form once</button></form></section><section><form method="post" enctype="multipart/form-data" action="${base}/upload"><label>Test file<input type="file" name="file" required></label><button>Upload test file once</button></form></section><p><a href="${base}/download" download="friday-native-download.txt">Download test file once</a></p>`}`}<p><a href="${base}/state">Inspect saved test counters</a></p></html>`);
}
