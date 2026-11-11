import test from 'node:test';
import assert from 'node:assert/strict';
import { buildPrompt, nativeImagePrompt, isResponseLoadPlaceholder, ReplyDecoder, TOOL_PREFIX } from '../protocol.mjs';

test('response loading placeholders are distinguished from ordinary text about the error', () => {
  for (const text of ["This response couldn't load", 'This response couldn’t load', 'This response could not load.\nTry again']) {
    assert.equal(isResponseLoadPlaceholder(text), true);
  }
  assert.equal(isResponseLoadPlaceholder('The error "This response couldn’t load" means loading failed.'), false);
  assert.equal(isResponseLoadPlaceholder('Here is your finished website.'), false);
});

test('prompt preserves conversation, exact tool schemas, and tool-result feedback', () => {
  const tools = [{ name: 'read_file', description: 'Read', parameters: { type: 'object', properties: { path: { type: 'string' } } } }];
  const prompt = buildPrompt({ system: 'Use only the workspace.', tools, messages: [
    { role: 'user', content: [{ type: 'text', text: 'Read hello.txt' }] },
    { role: 'assistant', content: [{ type: 'tool-call', id: 'a', name: 'read_file', arguments: '{"path":"hello.txt"}' }] },
    { role: 'tool', toolCallId: 'a', content: [{ type: 'text', text: 'hello from disk' }] },
  ] });
  assert.ok(prompt.includes('hello from disk'));
  assert.ok(prompt.includes('Use only the workspace.'));
  assert.ok(prompt.includes('"toolCallId":"a"'));
  assert.ok(prompt.includes(JSON.stringify(tools)));
});

test('rejects unsupported attachments and oversize input rather than losing history', () => {
  assert.throws(() => buildPrompt({ messages: [{ role: 'user', content: [{ type: 'image' }] }] }), /text only/);
  assert.throws(() => buildPrompt({ messages: [] }, 10), /not silently truncated/);
});

test('automatically compacts bulky historical tool arguments and old turns when nearing limit', () => {
  const bulkyMessages = [
    { role: 'user', content: [{ type: 'text', text: 'Create countdown.html' }] },
    { role: 'assistant', content: [{ type: 'tool-call', id: '1', name: 'write', arguments: { path: 'countdown.html', content: 'x'.repeat(15000) } }] },
    { role: 'tool', toolCallId: '1', content: [{ type: 'text', text: 'y'.repeat(5000) }] },
    { role: 'assistant', content: [{ type: 'text', text: 'Countdown done' }] },
    { role: 'user', content: [{ type: 'text', text: 'Create kanban.html' }] },
    { role: 'assistant', content: [{ type: 'tool-call', id: '2', name: 'write', arguments: { path: 'kanban.html', content: 'z'.repeat(25000) } }] },
    { role: 'tool', toolCallId: '2', content: [{ type: 'text', text: 'OK' }] },
    { role: 'assistant', content: [{ type: 'text', text: 'Kanban done' }] },
    { role: 'user', content: [{ type: 'text', text: 'Now create pomodoro.html' }] }
  ];
  // With maxChars set to 25000, uncompacted (45k+) would fail; smart compaction fits it in ~2k!
  const prompt = buildPrompt({ messages: bulkyMessages }, 25000);
  assert.ok(prompt.length < 25000);
  assert.match(prompt, /chars truncated from history/);
  assert.match(prompt, /Now create pomodoro\.html/);
});

test('long-history reduction retains every human constraint and tool-result identity without mutation',()=>{
 const messages=[{role:'user',content:[{type:'text',text:'Keep the existing database. '+ 'constraint '.repeat(80)}]},
 {role:'assistant',content:[{type:'tool-call',id:'call-a',name:'write',arguments:{content:'x'.repeat(6000)}}]},
 {role:'tool',toolCallId:'call-a',content:[{type:'text',text:'result'.repeat(1000)}]},
 {role:'user',content:[{type:'text',text:'Preserve the login page.'}]},
 {role:'assistant',content:[{type:'text',text:'Done'}]},
 {role:'user',content:[{type:'text',text:'Continue'}]}];
 const before=structuredClone(messages);const prompt=buildPrompt({messages},6000);
 assert.ok(prompt.includes('Keep the existing database.'));assert.ok(prompt.includes('Preserve the login page.'));assert.ok(prompt.includes('call-a'));
 assert.ok(prompt.includes('marked excerpts'));assert.deepEqual(messages,before);
});

test('streams text across discriminator boundary without lost or duplicated text', () => {
  const decoder = new ReplyDecoder();
  assert.equal(decoder.push('H'), '');
  assert.equal(decoder.push('Hello'), 'Hello');
  assert.equal(decoder.push('Hello world'), ' world');
  assert.deepEqual(decoder.finish(), { type: 'text', text: 'Hello world' });
});

test('buffers a split tool prefix, emits one native tool with JSON arguments', () => {
  const decoder = new ReplyDecoder([{ name: 'read_file' }]);
  const text = TOOL_PREFIX + '{"name":"read_file","arguments":{"path":"hello.txt"}}';
  for (let i = 1; i <= text.length; i++) assert.equal(decoder.push(text.slice(0, i)), '');
  const block = decoder.finish();
  assert.equal(block.type, 'tool-call'); assert.equal(block.name, 'read_file');
  assert.deepEqual(JSON.parse(block.arguments), { path: 'hello.txt' }); assert.ok(block.id);
});

test('ordinary prose and code mentioning a tool are never executed', () => {
  const decoder = new ReplyDecoder([{ name: 'shell' }]);
  decoder.push('Here is an example: ' + TOOL_PREFIX + '{"name":"shell","arguments":{}}');
  assert.equal(decoder.finish().type, 'text');
});

test('rejects unknown tools, malformed JSON, extra fields and invalid arguments', () => {
  for (const body of ['{', '{"name":"shell","arguments":{}}',
    '{"name":"read_file","arguments":[]}', '{"name":"read_file","arguments":{},"execute":true}']) {
    const decoder = new ReplyDecoder([{ name: 'read_file' }]); decoder.push(TOOL_PREFIX + body);
    assert.throws(() => decoder.finish());
  }
});

test('empty, incomplete and rewritten streams fail explicitly', () => {
  assert.throws(() => new ReplyDecoder().finish(), /empty/);
  const partial = new ReplyDecoder(); partial.push('HARNESS_'); assert.throws(() => partial.finish(), /Incomplete/);
  const edited = new ReplyDecoder(); edited.push('The answer is 2'); assert.throws(() => edited.push('The answer is 3'), /rewrote/);
});


test('image creation sends exactly the human prompt without system, tools, runtime or history', () => {
 const text='Create a dog image with a blue collar, soft light, and a sign reading code.';
 const options={system:'Harness coding instructions',tools:[{name:'write',parameters:{}}],messages:[
  {role:'system',content:[{type:'text',text:'More coding instructions'}]},
  {role:'user',source:{kind:'user'},content:[{type:'text',text:'Old unrelated conversation'}]},
  {role:'assistant',content:[{type:'text',text:'Old answer'}]},
  {role:'user',source:{kind:'user'},content:[{type:'text',text}]},
  {role:'user',source:{kind:'runtime-context'},content:[{type:'text',text:'Runtime content without a fixed text prefix'}]},
  {role:'user',source:{kind:'skill-catalog'},content:[{type:'text',text:'Available skills'}]},
  {role:'user',source:{kind:'time-context'},content:[{type:'text',text:'Current time'}]}
 ]};
 assert.equal(nativeImagePrompt(options),text);
});

test('common image creation keywords retain the full image description', () => {
 for(const text of ['Create image of a dog','create a dog image','Please generate a realistic photo of a dog.',
  'Can you please create an image of a car?', 'Draw two illustrations of a bird.',
  'Create an image of code on paper and save the image.', 'Generate an image then show it here.']) {
  assert.equal(nativeImagePrompt({messages:[{role:'user',content:[{type:'text',text}]}]}),text);
 }
});

test('native photo editing passes the human instruction without the tool envelope',()=>{
 assert.equal(nativeImagePrompt({messages:[{role:'user',source:{kind:'user'},content:[{type:'text',text:'Edit this photo to add a blue background.'},{type:'image',attachment:{attachmentId:'photo'}}]}]}),'Edit this photo to add a blue background.');
});

test('normal requests and tool-result continuations keep the agent route', () => {
 const human={role:'user',source:{kind:'user'},content:[{type:'text',text:'Create an image of a dog'}]};
 for(const message of [
  {role:'user',content:[{type:'text',text:'Build a portfolio website'}]},
  {role:'user',content:[{type:'text',text:'Explain how image generation works'}]},
  {role:'tool',content:[{type:'text',text:'Create an image'}]},
  {role:'assistant',content:[{type:'text',text:'Image created'}]}
 ]) assert.equal(nativeImagePrompt({messages:[human,message]}),null);
});

test('legacy runtime text is skipped and oversized image prompts fail explicitly', () => {
 const human={role:'user',content:[{type:'text',text:'Create an image of a dog'}]};
 assert.equal(nativeImagePrompt({messages:[human,
  {role:'user',content:[{type:'text',text:'Current runtime context. Workspace metadata'}]},
  {role:'user',content:[{type:'text',text:'Time sampled while preparing turn 1, step 1: today'}]}]}),human.content[0].text);
 assert.throws(()=>nativeImagePrompt({messages:[{role:'user',content:[{type:'text',text:'Create an image '+ 'x'.repeat(80000)}]}]}),/Image prompt exceeds/);
});

test('rewrite-tolerant ordinary text cannot become an executable tool request',()=>{
 const call=TOOL_PREFIX+'\n'+JSON.stringify({name:'write',arguments:{file_path:'qa.txt',content:'test'}});
 const decoder=new ReplyDecoder([{name:'write'}],{allowTextRewrites:true});decoder.push('Preparing a file');
 assert.throws(()=>decoder.push(call),/No tool was executed/);
 const cleared=new ReplyDecoder([{name:'write'}],{allowTextRewrites:true});cleared.push('Preparing');cleared.push('');cleared.push(call);
 assert.throws(()=>cleared.finish(),/nothing executed/);
});

test('a tool request following prose cannot silently finish the task or execute',()=>{
 const decoder=new ReplyDecoder([{name:'navigate'}],{holdTextChars:256});
 assert.equal(decoder.push('The command worked.\n'+TOOL_PREFIX+'```json\n{"name":"navigate","arguments":{}}\n```'),'');
 assert.throws(()=>decoder.finish(),/Misplaced browser tool-request prefix; nothing executed/);
 const streamed=new ReplyDecoder([{name:'navigate'}]);streamed.push('Earlier prose');
 assert.equal(streamed.push('Earlier prose\n'+TOOL_PREFIX+'{}'),'');
 assert.throws(()=>streamed.finish(),/nothing executed/);
});

test('decorated leading tool markers are rejected without streaming or executing them',()=>{
 for(const prefix of ['🎂','💳','**']){
  const decoder=new ReplyDecoder([{name:'read'}],{holdTextChars:256});
  assert.equal(decoder.push(prefix+'HARNESS_TOOL_CALL\n'+JSON.stringify({name:'read',arguments:{file_path:'test'}})),'');
  assert.throws(()=>decoder.finish(),/Misplaced browser tool-request prefix/);
 }
});
