import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {prepareInstalledProfile} from '../desktop/backend-runtime.mjs';
function fixture(t){const home=mkdtempSync(join(tmpdir(),'friday-install-test-'));t.after(()=>rmSync(home,{recursive:true,force:true}));const resources=join(home,'resources');mkdirSync(join(resources,'harness'),{recursive:true});writeFileSync(join(resources,'harness','friday-default-patch.yml'),'[]');return {home,resources,provider:join(resources,'provider'),executable:join(home,'Friday.exe')};}
test('clean installed setup creates a local secret once and uses bundled tools without external dependencies',t=>{
 const options=fixture(t),one=prepareInstalledProfile(options),secret=one.connection.token;
 assert.equal(one.fresh,true);assert.equal(one.connection.port,8766);assert.equal(Buffer.from(secret,'base64').length,32);
 const overlay=JSON.parse(readFileSync(one.overlayFile,'utf8'));const tool=overlay.flatMap(p=>p.insert||[]).find(p=>p.id==='harness-playwright');assert.equal(tool.config.command,options.executable);assert.equal(tool.config.args[0],'--expose-internals');assert.ok(!JSON.stringify(overlay).includes('Google/Chrome'));assert.ok(!JSON.stringify(overlay).includes('Program Files/nodejs'));
 const two=prepareInstalledProfile(options);assert.equal(two.connection.token,secret);assert.equal(two.fresh,false);
});
test('upgrade retains login files, native receipts, custom plugins and selected models byte for byte',t=>{
 const options=fixture(t),one=prepareInstalledProfile(options),profile=join(one.dsh,'profiles','web');
 const patch='- insert:\n    - id: harness-browser-provider\n      name: C:/old/index.mjs\n    - id: harness-playwright\n      name: mcp\n- id: agent-default-model\n  config:\n    provider: browser-web\n    model: gemini-web\n';writeFileSync(join(profile,'cordis.patch.yml'),patch);
 const files=[join(profile,'package.json'),join(profile,'cordis.patch.yml'),join(one.dsh,'friday-desktop','state.json'),join(one.dsh,'friday-desktop','profile','Cookies')];
 mkdirSync(join(one.dsh,'friday-desktop','profile'),{recursive:true});writeFileSync(files[2],JSON.stringify({tabs:[{url:'https://chatgpt.com/c/saved'}],receipts:{job:{submitted:true}}}));writeFileSync(files[3],'synthetic-cookie-store');
 const before=files.map(file=>readFileSync(file));const updated=prepareInstalledProfile({...options,provider:join(options.resources,'provider-v2')});assert.equal(updated.defaults,null);files.forEach((file,i)=>assert.deepEqual(readFileSync(file),before[i]));
 const overlay=JSON.parse(readFileSync(updated.overlayFile,'utf8'));assert.ok(overlay.some(p=>p.id==='harness-browser-provider'));assert.ok(!overlay.some(p=>p.id==='agent-default-model'));
});
test('invalid pre-existing connection is preserved and blocks setup instead of silently replacing credentials',t=>{
 const options=fixture(t),folder=join(options.home,'.dsh','browser-connector');mkdirSync(folder,{recursive:true});const path=join(folder,'connection.json'),value=JSON.stringify({port:9999,token:'existing-secret'});writeFileSync(path,value);assert.throws(()=>prepareInstalledProfile(options),/not replaced/);assert.equal(readFileSync(path,'utf8'),value);
});

test('an interrupted clean bootstrap resumes, while unmarked incomplete user profiles are preserved',t=>{
 const options=fixture(t),profile=join(options.home,'.dsh','profiles','web');mkdirSync(profile,{recursive:true});const patch=join(profile,'cordis.patch.yml');writeFileSync(patch,'user configuration');
 assert.throws(()=>prepareInstalledProfile(options),/no profile data was replaced/);assert.equal(readFileSync(patch,'utf8'),'user configuration');
 writeFileSync(join(profile,'.friday-bootstrap.json'),JSON.stringify({version:1,complete:false}));assert.equal(prepareInstalledProfile(options).fresh,true);assert.equal(JSON.parse(readFileSync(join(profile,'.friday-bootstrap.json'),'utf8')).complete,true);
});
