import {readFileSync,writeFileSync,existsSync,mkdirSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {homedir} from 'node:os';
/** Fictional loopback-only fixture; no real account, password or external publishing. */
export function persistenceFixture(req,res){
 if(!req.url?.startsWith('/_profile-test'))return false;
 const file=join(homedir(),'.dsh','browser-connector','test-evidence','fictional-posts.json');
 let posts=existsSync(file)?JSON.parse(readFileSync(file,'utf8')).posts:0;
 const signedIn=/(?:^|;\s*)friday_fixture=fictional-account(?:;|$)/.test(req.headers.cookie||'');
 if(req.method==='POST'&&req.url==='/_profile-test/sign-in'){
  res.setHeader('Set-Cookie','friday_fixture=fictional-account; HttpOnly; SameSite=Strict; Max-Age=86400; Path=/_profile-test');res.writeHead(303,{Location:'/_profile-test'});res.end();return true;
 }
 if(req.method==='POST'&&req.url==='/_profile-test/publish'&&signedIn){
  mkdirSync(dirname(file),{recursive:true});writeFileSync(file,JSON.stringify({posts:++posts}));res.writeHead(303,{Location:'/_profile-test'});res.end();return true;
 }
 if(req.method!=='GET'||req.url!=='/_profile-test'){res.writeHead(404);res.end();return true;}
 res.setHeader('Content-Type','text/html; charset=utf-8');res.setHeader('Cache-Control','no-store');
 res.end(`<!doctype html><html lang="en"><meta charset="utf-8"><title>Friday workspace persistence test</title><style>body{font:18px system-ui;background:#18191b;color:#eee;max-width:720px;margin:70px auto}button,a{padding:12px;color:#bdd4ff}button{background:#303848;border:1px solid #68738a;border-radius:8px}p{line-height:1.7}</style><h1>Friday workspace persistence test</h1><p>Fictional local account. Nothing is published outside this computer.</p><p role="status">${signedIn?'Signed in as Fictional Friday Tester':'Signed out'}</p><p>Committed fictional posts: <strong>${posts}</strong></p>${signedIn?'<form method="post" action="/_profile-test/publish"><button>Commit one fictional post</button></form>':'<form method="post" action="/_profile-test/sign-in"><button>Use fictional test account</button></form>'}<p><a href="/_profile-test">Reload test status</a></p></html>`);return true;
}
