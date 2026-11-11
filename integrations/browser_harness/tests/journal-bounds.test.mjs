import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,appendFileSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {DeliveryJournal} from '../journal.mjs';
const directory=t=>{const path=mkdtempSync(join(tmpdir(),'friday-journal-'));t.after(()=>rmSync(path,{recursive:true,force:true}));return path;};

test('bounded journal memory preserves full disk history, interrupted identities and monotonic sequence across restarts',t=>{
 const dir=directory(t);let journal=new DeliveryJournal(dir,{maxMemoryEvents:3,maxMemoryBytes:26000});
 journal.append('old','request',{id:'unfinished',prompt:'Keep this 🐾 original'});
 for(let n=0;n<12;n++)journal.append('recent','reply',{id:'current',text:'x'.repeat(12000)});
 assert.ok(journal.events.length<=3);assert.ok(journal.memoryBytes<=26000);assert.equal(journal.list('old')[0].data.prompt,'Keep this 🐾 original');
 journal=new DeliveryJournal(dir,{maxMemoryEvents:3,maxMemoryBytes:26000});assert.ok(journal.events.length<=3);assert.equal(journal.interrupted()[0].data.id,'unfinished');
 assert.equal(journal.append('recent','complete',{id:'current'}),14);assert.equal(journal.list('recent').length,13);
});
test('streamed UTF-8 recovery preserves a partial tail and normalizes a valid missing delimiter',t=>{
 const dir=directory(t),journal=new DeliveryJournal(dir);journal.append('one','reply',{text:'🐾'.repeat(20000)});
 appendFileSync(journal.file,'{"unfinished":"🐾');const restored=new DeliveryJournal(dir);
 assert.equal(restored.events.length,1);assert.equal(readFileSync(journal.file+'.interrupted-tail','utf8'),'{"unfinished":"🐾');
 restored.append('one','complete',{});assert.equal(new DeliveryJournal(dir).events.length,2);
 writeFileSync(journal.file,readFileSync(journal.file,'utf8').trimEnd());
 const delimited=new DeliveryJournal(dir);delimited.append('one','reply',{text:'Another record'});
 assert.equal(new DeliveryJournal(dir).events.length,3);
 assert.ok(readFileSync(journal.file,'utf8').endsWith('\n'));
});

test('crash recovery retains exact incomplete UTF-8 bytes rather than replacement characters',t=>{
 const dir=directory(t),journal=new DeliveryJournal(dir);journal.append('one','complete',{});
 const tail=Buffer.concat([Buffer.from('{"text":"'),Buffer.from([0xf0,0x9f])]);appendFileSync(journal.file,tail);
 const restored=new DeliveryJournal(dir);assert.equal(restored.events.length,1);
 assert.deepEqual(readFileSync(journal.file+'.interrupted-tail'),tail);
});
