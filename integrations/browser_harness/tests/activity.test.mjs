import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {SessionStore} from '../session-store.mjs';
import {Activity,captureToolImages} from '../activity.mjs';

test('native results settle the exact tool; website replies cannot finish the task',()=>{
 const sessions=new SessionStore(),activity=new Activity(sessions);
 activity.ensure('one');const run=activity.get('one').runId;
 assert.equal(activity.get('one').events[0].runId,run);
 activity.native('one',{seq:1,type:'tool/call',data:{callId:'a',name:'pwsh',arguments:'{}'}});
 activity.status('one','reply-received','Website replied','request-1');
 assert.equal(activity.get('one').tools[0].status,'requested');
 assert.equal(activity.get('one').events.some(e=>e.type==='RUN_FINISHED'),false);
 const result={seq:2,type:'tool/result',data:{message:{id:'result',toolCallId:'a',isError:true,content:[{type:'text',text:'Access denied'}]}}};
 assert.equal(activity.native('one',result),true);const revision=activity.get('one').revision;
 assert.equal(activity.native('one',result),false);assert.equal(activity.get('one').revision,revision);
 assert.equal(activity.get('one').tools[0].status,'error');
 assert.equal(activity.get('one').tools[0].result,'Access denied');
 activity.native('one',{seq:3,type:'turn/end',data:{reason:{kind:'completed'}}});
 assert.equal(activity.get('one').phase,'completed');
 assert.equal(activity.get('one').events.at(-1).type,'RUN_FINISHED');
 assert.equal(activity.get('two').revision,0);
});

test('refresh and restart restore activity without replay; cursors recover from gaps',t=>{
 const directory=mkdtempSync(join(tmpdir(),'friday-activity-'));t.after(()=>rmSync(directory,{recursive:true,force:true}));
 let sessions=new SessionStore(directory),activity=new Activity(sessions);
 activity.ensure('one');activity.native('one',{seq:4,type:'tool/call',data:{callId:'saved',name:'browser',arguments:'{}'}});
 const revision=activity.get('one').revision;
 for(let i=0;i<220;i++)activity.status('one','waiting',`Status ${i}`,'request');
 assert.equal(activity.snapshot('one',revision).reset,true);
 assert.equal(activity.snapshot('one',99999).events.length,180);
 sessions=new SessionStore(directory);activity=new Activity(sessions);activity.interrupted('one');
 assert.equal(activity.get('one').phase,'interrupted');
 assert.match(activity.get('one').message,/Nothing was replayed/);
 assert.equal(activity.get('one').tools[0].id,'saved');
 assert.equal(activity.native('one',{seq:4,type:'tool/call',data:{callId:'saved'}}),false);
 const cursor=activity.get('one').revision;assert.deepEqual(activity.snapshot('one',cursor).events,[]);
 activity.native('one',{seq:5,type:'turn/end',data:{reason:{kind:'aborted'}}});
 assert.equal(activity.get('one').phase,'cancelled');
});

test('screenshots use admitted native references, retain previews and do not fetch model URLs',async()=>{
 const sessions=new SessionStore(),activity=new Activity(sessions);let reads=0;
 const bridge={sessions,activity,readImage:async ref=>{reads++;assert.equal(ref.attachmentId,'verified');return {data:Buffer.from('89504e470d0a1a0a','hex'),mediaType:'image/png'};}};
 const event={type:'tool/result',seq:7,data:{message:{toolCallId:'screen',content:[{type:'text',text:'https://example.invalid/private.png'},{type:'image',attachment:{attachmentId:'verified'}}]}}};
 await captureToolImages(bridge,'one',event);await captureToolImages(bridge,'one',event);
 assert.equal(reads,1);const screenshot=activity.snapshot('one').screenshots[0];
 assert.equal(screenshot.callId,'screen');assert.match(screenshot.url,/^\/browser-models\/media\//);
 assert.equal(sessions.readImage(screenshot.id).mime,'image/png');
});
