// Independent acceptance checks against an isolated store, never the live db.
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import net from 'node:net';import {spawn}from'node:child_process';import {once}from'node:events';import assert from'node:assert/strict';
const root=path.resolve(process.argv[2]||'');if(!fs.existsSync(path.join(root,'server.mjs')))throw new Error('Supply the existing ORBIT project directory.');
await new Promise((resolve,reject)=>{const probe=net.createServer();probe.once('error',reject);probe.listen(8010,'127.0.0.1',()=>probe.close(resolve));});
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'friday-orbit-qa-'));let child;const checks=[];
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function start(){child=spawn(process.execPath,[path.join(root,'server.mjs')],{cwd:temp,stdio:['ignore','pipe','pipe'],windowsHide:true});let log='';child.stdout.on('data',d=>log+=d);child.stderr.on('data',d=>log+=d);for(let n=0;n<70;n++){if(child.exitCode!==null)throw new Error('Test child exited: '+log);try{const r=await fetch('http://127.0.0.1:8010/api/data');if(r.ok)return;}catch{}await pause(100);}throw new Error('Isolated child did not become ready: '+log);}
async function stop(){if(child&&child.exitCode===null){const ended=once(child,'exit');child.kill();await ended;}child=null;}
const api=async(route,method='GET',body)=>{const r=await fetch('http://127.0.0.1:8010'+route,{method,headers:{'Content-Type':'application/json'},...(body!==undefined?{body:JSON.stringify(body)}:{})});const text=await r.text();let data;try{data=JSON.parse(text);}catch{data=text;}return {status:r.status,data};};
async function check(name,fn){try{await fn();checks.push({name,passed:true});}catch(error){checks.push({name,passed:false,error:error.message});}}
let project,task;
try{
 for(const name of ['index.html','app.css','app.js'])if(fs.existsSync(path.join(root,name)))fs.copyFileSync(path.join(root,name),path.join(temp,name));
 await start();
 await check('seed data',async()=>{const r=await api('/api/data');assert.equal(r.data.projects.length,4);assert.equal(r.data.team.length,5);assert.equal(r.data.tasks.length,20);});
 await check('project create/edit/archive/restore',async()=>{let r=await api('/api/projects','POST',{name:'QA isolated project'});assert.equal(r.status,201);project=r.data;for(const archived of [true,false]){r=await api('/api/projects/'+project.id,'PUT',{name:'QA edited',archived});assert.equal(r.status,200);assert.equal(r.data.archived,archived);}});
 await check('task create/status/checklist/comment',async()=>{let r=await api('/api/tasks','POST',{projectId:project.id,title:'QA isolated task',status:'Backlog'});assert.equal(r.status,201);task=r.data;r=await api('/api/tasks/'+task.id,'PUT',{status:'Done',checklist:[{id:'qa-item',label:'Persist this item',checked:true}]});assert.equal(r.status,200);assert.equal(r.data.status,'Done');r=await api('/api/tasks/'+task.id+'/comments','POST',{text:'QA persisted comment'});assert.equal(r.status,201);});
 await check('activity records real changes',async()=>{const {data}=await api('/api/data');assert.ok(data.activity.length>=5);assert.equal(data.tasks.find(t=>t.id===task.id).checklist[0].checked,true);assert.equal(data.tasks.find(t=>t.id===task.id).comments.at(-1).text,'QA persisted comment');});
 await check('persistence across actual child restart',async()=>{await stop();await start();const {data}=await api('/api/data');assert.equal(data.tasks.find(t=>t.id===task.id).status,'Done');assert.equal(data.projects.find(p=>p.id===project.id).name,'QA edited');});
 for(const [name,route,method,body]of [
  ['blank project name','/api/projects','POST',{name:'   '}],
  ['unknown task project','/api/tasks','POST',{title:'Invalid project',projectId:'missing'}],
  ['invalid task status','/api/tasks/'+task?.id,'PUT',{status:'invalid-status'}],
  ['invalid task assignee','/api/tasks/'+task?.id,'PUT',{assignee:'missing'}],
  ['invalid checklist','/api/tasks/'+task?.id,'PUT',{checklist:'not-an-array'}],
  ['empty comment','/api/tasks/'+task?.id+'/comments','POST',{text:'   '}],
 ])await check('reject '+name,async()=>{const r=await api(route,method,body);assert.ok(r.status>=400&&r.status<500,'Expected 4xx, got '+r.status);});
 for(const route of ['/api/not-a-route','/server.mjs','/db.json'])await check('reject private/unknown path '+route,async()=>assert.equal((await api(route)).status,404));
}finally{
 await stop();
 const relative=path.relative(os.tmpdir(),temp);if(relative.startsWith('..')||path.isAbsolute(relative)||!path.basename(temp).startsWith('friday-orbit-qa-'))throw new Error('Unsafe test cleanup path');
 fs.rmSync(temp,{recursive:true,force:true});
}
console.log(JSON.stringify({isolated:true,checks},null,2));if(checks.some(c=>!c.passed))process.exitCode=1;
