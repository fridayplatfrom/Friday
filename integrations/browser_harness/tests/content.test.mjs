import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import {PROVIDERS} from '../providers.mjs';

const script = readFileSync(new URL('../extension/provider-catalog.js', import.meta.url), 'utf8')+'\n'+readFileSync(new URL('../extension/content.js', import.meta.url), 'utf8');
const standaloneScript=readFileSync(new URL('../extension/content.js',import.meta.url),'utf8');
test('single-line Kimi wire preserves exact JSON without the multiline clipboard path',async()=>{
 const prompt='FRIDAY_REQUEST_ID sample '+JSON.stringify({requestText:'Original\nrequest with "quotes" and \\ paths'});
 const f=page({host:'www.kimi.ai',lexical:true,prompt});
 const result=await f.run();assert.equal(result.ok,true,result.error);assert.equal(f.composer.innerText,prompt);assert.equal(f.counts().inputEvents,0);assert.equal(f.counts().clickCount,1);
});
function page({ desktopSubmit=false, frozenTimers=false, emptyOnce=false, replacementDraft="", semanticSend=false, disabledDecoy=false, ambiguousSend=false, capacityNotice=null, clipboardAccepted=true, lexical=false, semanticBusyUntil=0, deepseekGenerationUntil=1500, standalone=false, downloadUpdate = null, draft = '', prompt = 'test prompt', host = 'chatgpt.com', completion = true, cancelAt = Infinity, modern = false, imageMode = false, fencedReply = false, mathReply = false, extraReplyText = '', quotedImageProgress = false, thinkingPlaceholder = false, external = false, resume = null, unrelatedTurn = false, editable = false, linkLayout = false, revertDraft = false, verifySubmission = false, wrongSubmission = false, overflowUI = false, renderedAgent = false, remountedHistory = false, remountComposer = false, accountLoadingUntil = 0, loadingFrom = Infinity, loadingUntil = Infinity, loadingText = "This response couldn’t load" } = {}) {
  const deepseek=host==='chat.deepseek.com';
  const site=Object.keys(PROVIDERS).find(id=>PROVIDERS[id].selectors.hosts.includes(host))||'chatgpt-web';
  const contract=PROVIDERS[site].selectors,ordered=contract.correlation==='ordered-user-message';
  let listener; let now = 0; let submitted = !!external||!!resume; let clickCount = 0; let inputEvents = 0;let stopClicks=0;
  let downloadReady=false; let downloadCalls=0; let emptied=false;
  const events = []; const visible = { getClientRects: () => [1], getAttribute: () => null, focus() {} };
  class Textarea {
    constructor() { this._value = draft; Object.assign(this, visible); }
    get value() { return this._value; }
    set value(value) { this._value = value; }
    dispatchEvent() { inputEvents++; }
  }
  const composer = editable||lexical ? {...visible,innerText:draft} : new Textarea();
  if(lexical){composer.getAttribute=name=>name==='data-lexical-editor'?'true':null;composer.dispatchEvent=event=>{if(event.type==='paste'&&clipboardAccepted){inputEvents++;composer.innerText=event.clipboardData.getData('text/plain');return false;}return true;};}
  let submittedText=resume?prompt:'';
  const send = { ...visible, click() { submittedText=composer.value||composer.innerText;submitted = true; clickCount++; if(deepseek)composer.value=''; } };
  if(emptyOnce)Object.defineProperty(send,'disabled',{get:()=>now<600});
  if(deepseek)Object.defineProperty(send,'disabled',{get:()=>submitted?now>=deepseekGenerationUntil:!composer.value.trim()});
  const replacement = new Textarea();
  if(remountComposer)Object.defineProperty(send,'disabled',{get:()=>now<400});
  const stop = { ...visible, click() { stopClicks++;submitted = false; } };
  const literalTool=JSON.stringify({name:'pwsh',arguments:{command:"$job='x'; Write-Output $job"}});
  const response = { ...visible,querySelector:selector=>mathReply&&selector.includes('data-math-source')?{}:null,querySelectorAll:selector=>contract.completionMarker?.includes(selector)?now>=semanticBusyUntil&&completion?[visible]:[]:fencedReply&&selector===(deepseek?'pre':'pre code')?[{textContent:literalTool}]:[], get innerText() { if(downloadReady)return downloadUpdate; return mathReply?'HARNESS_TOOL_CALL\n{"name":"pwsh","arguments":{"command":"corrupted but valid JSON"}}':fencedReply?'HARNESS_TOOL_CALL\n'+(deepseek?'json\nCopy\nDownload\n':host.includes('kimi.')?'JSON\nCopy\n':'JSON\n\n')+literalTool+extraReplyText:thinkingPlaceholder && now < 2000 ? 'Thinking' : now >= loadingFrom && now < loadingUntil ? loadingText : imageMode ? '' : now < 1000 ? 'Hello' : 'Hello world'; },
    closest(selector) { if(ordered&&selector===contract.responseContainer)return {querySelectorAll:()=>completion&&now>=1500?[visible]:[]}; if(deepseek&&selector==='.ds-message')return {parentElement:{querySelectorAll:()=>completion&&now>=1500?[visible]:[]}}; if((external||resume||verifySubmission) && selector==='[data-turn-key]') return {getAttribute:()=>verifySubmission?'submitted-turn':'native-turn'}; return modern && selector.includes('data-talvt-turn-state') && completion && now >= 1500 ? {} : null; } };
  const turn = { ...visible, get innerText() { return now < 1000 ? 'Making the first draft 27%' : now < 2000 ? 'Sketching it out 38%' : now < 2500 ? 'One last tweak 96%' : ''; },
    getAttribute: () => now < 2500 ? 'streaming' : 'complete', querySelector: () => null };
  const image = { ...visible, src: 'blob:https://chatgpt.com/generated', alt: 'Generated image 1',
    get complete() { return now >= 2500; }, naturalWidth: 1024, closest: () => turn };
  const quotedTurn={...visible,innerText:'User source code: Creating image 65%\nHello world',getAttribute:()=>now>=1500?'complete':'streaming',
    querySelector(selector){if(selector.includes('assistant-message'))return response;if(selector.includes('data-user-message-bubble'))return {innerText:'Creating image 65%'};return null;}};
  const document = { querySelectorAll(selector) {
    if(capacityNotice && submitted && contract.errorNotices?.some(item=>selector.includes(item)))return [{...visible,innerText:capacityNotice}];
    if(ordered){
      if(contract.busy?.includes(selector))return submitted&&now<semanticBusyUntil?[contract.stop.includes(selector)?stop:visible]:[];
      if(contract.composer.includes(selector))return [composer];
      if(contract.send.includes(selector))return [send];
      if(!deepseek&&contract.stop.includes(selector))return submitted&&(!completion||now<1500)?[stop]:[];
      if(selector===contract.responses[0])return submitted?[response]:[];
      if(selector===contract.users.join(','))return submitted?[{innerText:wrongSubmission?'wrong turn':submittedText,querySelectorAll:()=>contract.userText?[{innerText:wrongSubmission?'wrong turn':submittedText}]:[],compareDocumentPosition:node=>node===response?4:0}]:[];
    }
    if(selector==='button[aria-label="Open profile menu"][disabled]')return now<accountLoadingUntil?[visible]:[];
    if(selector==='[data-turn-key]'&&resume&&!verifySubmission)return [{getAttribute:()=> 'native-turn',querySelector:()=>({innerText:wrongSubmission?'different request':prompt})}];
    if(selector==='[data-turn-key]')return verifySubmission&&submitted?[...(remountedHistory?[{getAttribute:()=> 'remounted-old-turn',querySelector:()=>({innerText:'old introduction'})}]:[]),{getAttribute:()=> 'submitted-turn',querySelector:()=>({innerText:wrongSubmission?'old introduction':overflowUI?submittedText+' … Show more':renderedAgent?submittedText.slice(0,500)+' [rendered content shortened]':submittedText,querySelector:()=>overflowUI?{innerText:submittedText}:null})}]:[];
    if (imageMode && submitted && selector.includes('generated-image-preview')) return now >= 2000 ? [image] : [];
    if (imageMode && submitted && selector === '[data-talvt-turn-state], article[data-testid^="conversation-turn-"]') return [turn];
    if (quotedImageProgress && submitted && selector === '[data-talvt-turn-state], article[data-testid^="conversation-turn-"]') return [quotedTurn];
    if (selector === (modern ? '[contenteditable="true"][role="textbox"][aria-label="Ask ChatGPT"]' : '#prompt-textarea')) {if(remountComposer&&now>=350){replacement.value=composer.value;return [replacement];}return [composer];}
    if (selector === 'button[data-testid="send-button"]') return disabledDecoy?[{...visible,disabled:true}]:semanticSend?[]:[send];
    if(semanticSend&&selector==='button[aria-label="Send"]')return ambiguousSend?[send,{...visible,click(){throw Error('Wrong control');}}]:[send];
    if (selector === (modern ? '[data-markdown-text-style="assistant-message"]' : '[data-message-author-role="assistant"]')) return submitted ? [response, ...(unrelatedTurn ? [{ ...visible, innerText: 'Wrong later response', closest: () => ({getAttribute:()=> 'other-turn'}) }] : [])] : [];
    if (selector === 'button[data-testid="stop-button"]' && !modern) return submitted && (!completion || now < 1500) ? [stop] : [];
    if (modern && selector === '[data-talvt-turn-state="complete"] [data-markdown-text-style="assistant-message"]') return submitted && completion && now >= 1500 ? [response] : [];
    return [];
  },createRange(){return {selectNodeContents(){}};},execCommand(command,_show,text){composer.innerText=lexical?(command==='insertHTML'?text.replace(/^<span style="white-space:pre-wrap">|<\/span>$/g,'').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&'):text.replace(/\n/g,'')):text;
    if(linkLayout){const [before,after]=text.split('https://example.test/schema');composer.innerText=before+'\nhttps://example.test/schema\n'+after;
      Object.assign(composer,{nodeType:1,nodeName:'DIV',childNodes:[{nodeType:1,nodeName:'P',childNodes:[{nodeType:3,nodeValue:before},{nodeType:1,nodeName:'A',childNodes:[{nodeType:3,nodeValue:'https://example.test/schema'}]},{nodeType:3,nodeValue:after}]}]});}
    return true;} };
  vm.runInNewContext(standalone?standaloneScript:script, { FridayDesktopSubmit:desktopSubmit?async()=>{if(desktopSubmit==='reject')throw Error('Submission uncertain');send.click();}:undefined, HarnessFiles:downloadUpdate?{async collectDownloads(){downloadReady=true;downloadCalls++;return [{id:'fixture-file'}];}}:undefined, HarnessTwoWay: external ? { take: () => external === 'missing' ? null : { turnKey: 'native-turn', baseline: new Set(), baselineImages: new Set(), baselineTurns: new Set() }, forget() {} } : undefined, document, location: { hostname: host, origin: 'https://'+host, pathname: '/c/test' }, HTMLTextAreaElement: Textarea,
    sessionStorage:resume||verifySubmission?{getItem:key=>resume&&key==='harness-job:job'?JSON.stringify(resume):null,setItem() {}}:undefined,
    window:{getSelection:()=>({removeAllRanges(){},addRange(){}})},
    DataTransfer:class{constructor(){this.data={};}setData(type,value){this.data[type]=value;}getData(type){return this.data[type];}},ClipboardEvent:class{constructor(type,props){this.type=type;Object.assign(this,props);}},HTMLInputElement: class {}, getComputedStyle: () => ({ visibility: 'visible' }), Event: class {},
    URL, fetch: async () => ({ ok: true, blob: async () => ({ size: 68, type: 'image/png' }) }),
    FileReader: class { readAsDataURL() { this.result='data:image/png;base64,iVBORw0KGgo='; this.onload(); } },
    Date: { now: () => now }, clearTimeout() {}, setTimeout(callback, ms) {
      if(frozenTimers)return;
      now += ms;
      if(revertDraft)composer.innerText=draft;
      if(emptyOnce&&!emptied&&now>=350){emptied=true;composer.innerText=replacementDraft;}
      if (now >= cancelAt && listener) listener({ type: 'harness-cancel', id: 'job' }, {}, () => {});
      queueMicrotask(callback);
    }, chrome: { runtime: { onMessage: { addListener(fn) { listener = fn; } },
      async sendMessage(message) { events.push(message.event); return { ok: true }; } } },
  });
  const run = (purpose=thinkingPlaceholder&&imageMode?'image':undefined,streamEvents=false) => new Promise(resolve => listener({ type: 'harness-run',streamEvents, resume:!!resume, site, purpose, id: 'job', prompt: external ? '' : prompt, externalMessageId: external ? 'from-website' : undefined, timeoutMs: 6000 }, {}, resolve));
  return { cancel:()=>listener({type:'harness-cancel',id:'job'},{},()=>{}), pulse: (id='job',ms=1200)=>{now+=ms;let result;listener({type:'harness-pulse',id},{},value=>{result=value;});return result;}, run, downloadCounts:()=>downloadCalls, notice: online => new Promise(resolve => listener({type:'harness-connection-notice',online,url:'https://chatgpt.com/c/test'}, {}, resolve)), events, composer, clock: () => now, counts: () => ({ clickCount, inputEvents,stopClicks }) };
}

test('content connector submits through editor input, mirrors deltas and confirms stop transition', async () => {
  const fixture = page(); assert.equal((await fixture.run()).ok, true);
  assert.equal(fixture.composer.value, 'test prompt'); assert.equal(fixture.counts().clickCount, 1);
  assert.ok(fixture.counts().inputEvents > 0);
  assert.deepEqual(fixture.events.map(event => event.type), ['snapshot', 'snapshot', 'done']);
  assert.equal(fixture.events.at(-1).text, 'Hello world');
});
test('desktop submission hook sends once and never falls back after an uncertain host rejection',async()=>{
 const good=page({desktopSubmit:true});assert.equal((await good.run()).ok,true);assert.equal(good.counts().clickCount,1);
 const rejected=page({desktopSubmit:'reject'});assert.equal((await rejected.run()).ok,false);assert.equal(rejected.counts().clickCount,0);
 const resumed=page({desktopSubmit:true,resume:{state:'submitted',turnKey:'native-turn'}});assert.equal((await resumed.run()).ok,true);assert.equal(resumed.counts().clickCount,0);
});

test('owned worker pulses finish background replies even when page timers never fire, without another Send',async()=>{
 for(const host of ['chatgpt.com','gemini.google.com','chat.deepseek.com','www.kimi.ai']){
  const f=page({host,frozenTimers:true,modern:host==='chatgpt.com',verifySubmission:host!=='chatgpt.com'});let finished;
  const pending=f.run().then(result=>{finished=result;});
  assert.equal(f.pulse('another-job').ok,false);await new Promise(resolve=>setImmediate(resolve));assert.equal(f.counts().clickCount,0);
  for(let i=0;i<12&&!finished;i++){f.pulse();await new Promise(resolve=>setImmediate(resolve));}
  await pending;assert.equal(finished.ok,true,`${host}: ${finished.error}`);assert.equal(f.counts().clickCount,1);assert.equal(f.events.filter(e=>e.type==='done').length,1);
 }
});
test('cancellation wakes a frozen editor wait and cannot submit its draft later',async()=>{
 const f=page({frozenTimers:true,cancelAt:0});
 // Cancellation is delivered through the existing message handler, not a timer.
 const pending=f.run();f.pulse();
 // The fixture's cancelAt timer is frozen, so use an explicit cancellation hook.
 f.cancel();const result=await pending;assert.equal(result.ok,true);assert.equal(f.counts().clickCount,0);assert.equal(f.events.some(e=>e.type==='done'),false);
});

test('a verified expired Gemini/Kimi generation is stopped without resubmitting or claiming completion',async()=>{
 for(const host of ['gemini.google.com','www.kimi.ai']){
  const f=page({host,verifySubmission:true,completion:false,semanticBusyUntil:100000});
  assert.match((await f.run()).error,/Could not confirm website completion/);
  assert.equal(f.counts().stopClicks,1);assert.equal(f.counts().clickCount,1);assert.equal(f.events.some(event=>event.type==='done'),false);
 }
});

test('stream-event mode immediately acknowledges start and completes independently of the start-message port',async()=>{
 for(const host of ['chatgpt.com','chat.deepseek.com','gemini.google.com','www.kimi.ai']){
  const f=page({host,verifySubmission:host!=='chatgpt.com'}),ack=await f.run(undefined,true);
  assert.equal(ack.ok,true);assert.equal(ack.started,true);
  assert.equal(f.events.some(event=>event.type==='done'),false,'start ACK must precede completed generation');
  for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.events.at(-1).type,'done');assert.equal(f.events.at(-1).text,'Hello world');assert.equal(f.counts().clickCount,1);
 }
});
test('current ChatGPT semantic Send works without a legacy test ID and skips a disabled decoy',async()=>{
 for(const disabledDecoy of [false,true]){
  const f=page({modern:true,editable:true,semanticSend:true,disabledDecoy});const result=await f.run();
  assert.equal(result.ok,true,result.error);assert.equal(f.counts().clickCount,1);assert.equal(f.events.at(-1).text,'Hello world');
 }
});
test('ambiguous enabled send controls never cause a guessed or repeated submission',async()=>{
 const f=page({modern:true,editable:true,semanticSend:true,ambiguousSend:true});
 assert.match((await f.run()).error,/Multiple enabled send controls/);assert.equal(f.counts().clickCount,0);
});
test('ChatGPT home-editor hydration can empty a draft before Send without causing a second submission',async()=>{
 const f=page({modern:true,editable:true,semanticSend:true,emptyOnce:true});const result=await f.run();
 assert.equal(result.ok,true,result.error);assert.equal(f.counts().clickCount,1);assert.equal(f.composer.innerText,'test prompt');
 const changed=page({modern:true,editable:true,semanticSend:true,emptyOnce:true,replacementDraft:'Human changed this draft'});
 assert.match((await changed.run()).error,/draft changed/);assert.equal(changed.counts().clickCount,0);assert.equal(changed.composer.innerText,'Human changed this draft');
});

test('download collection rechecks the settled reply and does not commit its earlier partial text',async()=>{
 const full='Friday acceptance report: command passed, form filled, screenshot captured.';
 const f=page({modern:true,downloadUpdate:full});assert.equal((await f.run()).ok,true);
 assert.equal(f.events.at(-1).type,'done');assert.equal(f.events.at(-1).text,full);
 assert.equal(f.downloadCounts(),1,'an updated reply must not redownload the same file');
 assert.equal(f.events.filter(e=>e.type==='file').length,1);
 assert.equal(f.events.some(e=>e.type==='snapshot'&&e.text===full),true);
});

test('image-generation words in the user half of a shared turn cannot stall a normal response',async()=>{
 const f=page({quotedImageProgress:true});assert.equal((await f.run()).ok,true);
 assert.equal(f.events.some(event=>event.type==='progress'),false);
 assert.equal(f.events.at(-1).type,'done');assert.equal(f.events.at(-1).text,'Hello world');
});

test('rendered JSON tool code blocks preserve literal commands without language headings',async()=>{
 const f=page({fencedReply:true});assert.equal((await f.run()).ok,true);
 const text=f.events.at(-1).text;assert.ok(text.startsWith('HARNESS_TOOL_CALL\n```json\n'));
 const body=text.slice('HARNESS_TOOL_CALL\n```json\n'.length,-4);
 assert.equal(JSON.parse(body).arguments.command,"$job='x'; Write-Output $job");
 const extra=page({fencedReply:true,extraReplyText:'\nUnexpected outside prose'});await extra.run();
 assert.ok(extra.events.at(-1).text.endsWith('Unexpected outside prose'));
 assert.ok(!extra.events.at(-1).text.includes('```json'),'outside content cannot be stripped to manufacture a valid call');
});

test('math-rendered tool JSON is rejected even when its corrupted visible text could parse',async()=>{
 const f=page({mathReply:true});const result=await f.run();assert.equal(result.ok,false);assert.match(result.error,/rendered as mathematics/);
 assert.equal(f.events.some(event=>event.type==='snapshot'||event.type==='done'),false);
});

test('draft in the paired tab is replaced and submitted exactly once', async () => {
  const fixture = page({ draft: 'private draft' }); const result = await fixture.run();
  assert.equal(result.ok, true); assert.equal(fixture.composer.value, 'test prompt');
  assert.equal(fixture.counts().clickCount, 1);
});

test('a contenteditable draft must retain the new prompt before the send control is used',async()=>{
  const f=page({editable:true,draft:'old introduction'});assert.equal((await f.run()).ok,true);
  assert.equal(f.composer.innerText,'test prompt');assert.equal(f.counts().clickCount,1);
  const reverted=page({editable:true,revertDraft:true,draft:'old introduction'});
  assert.match((await reverted.run()).error,/did not retain/);assert.equal(reverted.counts().clickCount,0);
});
test('inline auto-link layout whitespace does not alter the underlying editor message',async()=>{
 const f=page({editable:true,linkLayout:true,prompt:'{"url":"https://example.test/schema"}'});
 assert.equal((await f.run()).ok,true);assert.equal(f.counts().clickCount,1);
});

test('a different submitted user message is an uncertain failure and never reported delivered',async()=>{
  const wrong=page({verifySubmission:true,wrongSubmission:true});
  assert.match((await wrong.run()).error,/does not match/);assert.equal(wrong.counts().clickCount,1);
  assert.equal(wrong.events.some(event=>event.type==='submitted'||event.type==='done'),false);
  const correct=page({verifySubmission:true});assert.equal((await correct.run()).ok,true);
  assert.equal(correct.events.some(event=>event.type==='submitted'),true);
});
test('message verification ignores the overflow controls outside the actual user message renderer',async()=>{
  const f=page({verifySubmission:true,overflowUI:true});assert.equal((await f.run()).ok,true);
  assert.equal(f.events.some(event=>event.type==='submitted'),true);
});
test('newly remounted history is not mistaken for the submitted turn or its response',async()=>{
 const f=page({verifySubmission:true,remountedHistory:true,unrelatedTurn:true});assert.equal((await f.run()).ok,true);
 assert.equal(f.events.find(event=>event.type==='submitted').turnKey,'submitted-turn');
 assert.equal(f.events.at(-1).text,'Hello world');
});
test('agent envelopes carry a unique visible turn ID despite truncated Markdown rendering; native image prompts stay unchanged',async()=>{
 const f=page({verifySubmission:true,renderedAgent:true,prompt:'You are answering one request for a local Harness agent. '+ 'Context words '.repeat(500)});
 assert.equal((await f.run()).ok,true);assert.match(f.composer.value,/^HARNESS_REQUEST_ID job\n\n/);
 assert.equal(f.events.find(event=>event.type==='submitted').turnKey,'submitted-turn');
 const image=page({verifySubmission:true,prompt:'Create an image of a dog'});
 assert.equal((await image.run()).ok,true);assert.equal(image.composer.value,'Create an image of a dog');
});

test('ChatGPT account hydration completes before sending and an indefinitely loading account is not submitted',async()=>{
  const ready=page({accountLoadingUntil:2000,modern:true});assert.equal((await ready.run()).ok,true);assert.equal(ready.counts().clickCount,1);
  const loading=page({accountLoadingUntil:Infinity});assert.match((await loading.run()).error,/editor is not ready/);assert.equal(loading.counts().clickCount,0);
});

test('introductions and context transfers verify their unique turn marker after Markdown rendering',async()=>{
 for(const purpose of ['introduction','context']){
  const f=page({verifySubmission:true,renderedAgent:true,prompt:'Protocol with code fences. '+ 'Instructions '.repeat(500)});
  assert.equal((await f.run(purpose)).ok,true);
  assert.match(f.composer.value,/^HARNESS_REQUEST_ID job\n\n/);
  assert.equal(f.events.find(event=>event.type==='submitted').turnKey,'submitted-turn');
 }
});

test('current ChatGPT layout works with its observed editor, response and completed-turn selectors', async () => {
  const fixture = page({ modern: true }); assert.equal((await fixture.run()).ok, true);
  assert.equal(fixture.events.at(-1).type, 'done'); assert.equal(fixture.events.at(-1).text, 'Hello world');
});

test('wrong website is rejected before writing', async () => {
  const fixture = page({ host: 'evil.example' }); const result = await fixture.run();
  assert.match(result.error, /mismatch/); assert.equal(fixture.counts().clickCount, 0);
});

test('stable text with generation still active never becomes a successful completion', async () => {
  const fixture = page({ completion: false }); const result = await fixture.run();
  assert.equal(result.ok, false); assert.match(result.error, /confirm website completion/);
  assert.equal(fixture.events.some(event => event.type === 'done'), false);
});

test('cancellation does not return a false successful website answer', async () => {
  const fixture = page({ completion: false, cancelAt: 1500 });
  await fixture.run(); assert.equal(fixture.events.some(event => event.type === 'done'), false);
});


test('image-only reply forwards real percentage and loaded image before completing', async () => {
  const fixture=page({imageMode:true});const result=await fixture.run();
  assert.equal(result.ok,true, result.error);
  const types=fixture.events.map(e=>e.type);
  assert.ok(types.includes('progress'));assert.ok(types.includes('image-chunk'));
  assert.equal(types.at(-1),'done');
  assert.ok(types.indexOf('image-end')<types.indexOf('done'));
  assert.deepEqual(fixture.events.filter(e=>e.type==='progress').map(e=>e.percent),[27,38,96]);
  assert.equal(fixture.events.some(e=>e.type==='progress' && e.percent===100),false);
});

test('native image UI Thinking status is not emitted as the final assistant text',async()=>{
 const f=page({imageMode:true,thinkingPlaceholder:true});assert.equal((await f.run()).ok,true);
 assert.equal(f.events.some(event=>event.type==='snapshot'&&event.text==='Thinking'),false);
 assert.equal(f.events.some(event=>event.type==='image-end'),true);
});

test('ordinary agent turns do not stream the native Thinking placeholder',async()=>{
 const f=page({thinkingPlaceholder:true});assert.equal((await f.run()).ok,true);
 assert.equal(f.events.some(event=>event.type==='snapshot'&&event.text==='Thinking'),false);
 assert.equal(f.events.findLast(event=>event.type==='done').text,'Hello world');
});


test('response loading placeholder waits beyond normal timeout, then resumes the same reply', async () => {
 const fixture=page({loadingFrom:0,loadingUntil:9000,modern:true});const result=await fixture.run();
 assert.equal(result.ok,true,result.error);assert.ok(fixture.clock()>9000);
 assert.ok(fixture.events.some(e=>e.type==='status'&&e.state==='response-loading'));
 assert.ok(fixture.events.some(e=>e.type==='status'&&e.state==='receiving'));
 assert.equal(fixture.events.at(-1).type,'done');assert.equal(fixture.events.at(-1).text,'Hello world');
 assert.equal(fixture.events.some(e=>e.text?.includes('couldn’t load')),false);
 assert.equal(fixture.counts().clickCount,1);
});

test('temporary loading error after partial text never finishes that partial answer', async () => {
 const fixture=page({loadingFrom:2000,loadingUntil:10000});const result=await fixture.run();
 assert.equal(result.ok,true,result.error);assert.ok(fixture.clock()>=12000);
 assert.equal(fixture.events.filter(e=>e.type==='done').length,1);
 assert.equal(fixture.events.some(e=>e.text?.includes('couldn’t load')),false);
 assert.equal(fixture.counts().clickCount,1);
});

test('persistent loading placeholder keeps waiting until user cancels without resubmitting', async () => {
 const fixture=page({loadingFrom:0,loadingUntil:Infinity,cancelAt:12000});await fixture.run();
 assert.ok(fixture.clock()>=12000);
 assert.equal(fixture.events.some(e=>e.type==='done'||e.type==='error'||e.type==='snapshot'),false);
 assert.ok(fixture.events.filter(e=>e.type==='status'&&e.state==='response-loading').length>=2);
 assert.equal(fixture.counts().clickCount,1);
});


test('website-origin response is captured without typing or submitting a second prompt', async () => {
 const fixture=page({external:true});const result=await fixture.run();
 assert.equal(result.ok,true,result.error);assert.equal(fixture.counts().clickCount,0);assert.equal(fixture.counts().inputEvents,0);
 assert.equal(fixture.events.at(-1).text,'Hello world');
});

test('missing native-message capture fails without submitting a replacement prompt', async () => {
 const fixture=page({external:'missing'});const result=await fixture.run();
 assert.equal(result.ok,false);assert.match(result.error,/originating ChatGPT message/);assert.equal(fixture.counts().clickCount,0);
});

test('website-origin capture excludes a later reply belonging to another native turn', async () => {
 const fixture=page({external:true,unrelatedTurn:true}); const result=await fixture.run();
 assert.equal(result.ok,true,result.error); assert.equal(fixture.events.at(-1).text,'Hello world');
 assert.equal(fixture.events.some(event=>event.text?.includes('Wrong later response')),false);
});

test('connection notices inform ChatGPT without overwriting drafts or creating bridge events', async () => {
 const draft=page({draft:'My unsent message'}); assert.equal((await draft.notice(false)).sent,false); assert.equal(draft.composer.value,'My unsent message');
 const idle=page(); assert.equal((await idle.notice(false)).sent,true); assert.match(idle.composer.value,/Harness is OFFLINE/);
 assert.equal(idle.counts().clickCount,1); assert.equal(idle.events.length,0);
 const restored=page(); assert.equal((await restored.notice(true)).sent,true); assert.match(restored.composer.value,/online again/);
});

test('refresh resumes capture of the saved turn without typing or sending the prompt again',async()=>{
 const f=page({resume:{state:'submitted',turnKey:'native-turn'}});assert.equal((await f.run()).ok,true);
 assert.equal(f.counts().clickCount,0);assert.equal(f.counts().inputEvents,0);assert.equal(f.events.at(-1).text,'Hello world');
});

test('fresh-page pulses advertise only this job receipt and do not submit anything',()=>{
 const f=page({resume:{state:'submitted',turnKey:'native-turn'}});
 assert.equal(f.pulse().resumeAvailable,true);assert.equal(f.pulse('other-job').resumeAvailable,false);
 assert.equal(f.counts().clickCount,0);assert.equal(f.counts().inputEvents,0);
 assert.equal(page({resume:{state:'submitting'}}).pulse().resumeAvailable,false);
});

test('resume rejects a mismatched request, another chat and interrupted image transfer without Send',async()=>{
 for(const options of [
  {resume:{state:'submitted',turnKey:'native-turn'},wrongSubmission:true},
  {resume:{state:'submitted',turnKey:'native-turn',url:'https://chatgpt.com/c/other'}},
  {resume:{state:'submitted',turnKey:'native-turn',imageTransferPending:true}},
 ]){
  const f=page(options);assert.equal((await f.run()).ok,false);
  assert.equal(f.counts().clickCount,0);assert.equal(f.counts().inputEvents,0);assert.equal(f.events.some(e=>e.type==='done'),false);
 }
});

test('resuming collected or uncertain downloads does not click Download again',async()=>{
 for(const fields of [{filesCollected:true,artifactPhase:'complete'},{artifactPhase:'started'}]){
  const f=page({resume:{state:'submitted',turnKey:'native-turn',...fields},downloadUpdate:'New content from another download'});
  assert.equal((await f.run()).ok,true);assert.equal(f.downloadCounts(),0);assert.equal(f.events.some(e=>e.type==='file'),false);
  if(!fields.filesCollected)assert.ok(f.events.some(e=>e.type==='artifact-warning'));
 }
});

test('refresh during an unconfirmed submission fails for review without replaying it',async()=>{
 const f=page({resume:{state:'submitting'}});const result=await f.run();assert.equal(result.ok,false);
 assert.match(result.error,/uncertain/);assert.equal(f.counts().clickCount,0);assert.equal(f.events.some(event=>event.type==='done'),false);
});

 test('equivalent composer remount while Send enables is verified and submitted once',async()=>{ const f=page({remountComposer:true}); const result=await f.run(); assert.equal(result.ok,true,result.error); assert.equal(f.counts().clickCount,1); });

test('DeepSeek uses its verified user message and explicit completion controls without ChatGPT turn attributes',async()=>{const f=page({host:'chat.deepseek.com'});assert.equal((await f.run()).ok,true);assert.equal(f.counts().clickCount,1);assert.equal(f.events.filter(e=>e.type==='submitted').length,1);assert.equal(f.events.at(-1).text,'Hello world');});
test('DeepSeek mismatched submission fails for review without a second send',async()=>{const f=page({host:'chat.deepseek.com',wrongSubmission:true});assert.equal((await f.run()).ok,false);assert.equal(f.counts().clickCount,1);assert.equal(f.events.some(e=>e.type==='done'),false);});

test('standalone content bootstrap survives a stale manifest without the catalog preload',async()=>{for(const host of ['chatgpt.com','chat.deepseek.com']){const f=page({host,standalone:true});assert.equal((await f.run()).ok,true);assert.equal(f.counts().clickCount,1);}});

test('DeepSeek literal tool code excludes only observed toolbar labels and retains exact command bytes',async()=>{const f=page({host:'chat.deepseek.com',fencedReply:true});assert.equal((await f.run()).ok,true);const text=f.events.at(-1).text;assert.ok(text.startsWith('HARNESS_TOOL_CALL\n```json\n'));assert.ok(text.includes("$job='x'; Write-Output $job"));assert.ok(!text.includes('Download'));});

test('DeepSeek does not finish a stable partial reply while its unlabeled generation control is active',async()=>{const f=page({host:'chat.deepseek.com',deepseekGenerationUntil:3500});assert.equal((await f.run()).ok,true);assert.ok(f.clock()>=3500);assert.equal(f.events.at(-1).text,'Hello world');});

test('Kimi Lexical paste preserves multiline agent JSON through editor state before sending once',async()=>{
 const prompt='HARNESS_REQUEST_ID synthetic\n\nFirst line\n```json\n{"literal":"$value"}\n```\nLast line';
 const f=page({host:'www.kimi.ai',lexical:true,prompt});const result=await f.run();assert.equal(result.ok,true,result.error);
 assert.equal(f.composer.innerText,prompt);assert.equal(f.counts().inputEvents,1);assert.equal(f.counts().clickCount,1);
});

test('Lexical fallback inserts escaped literal text when synthetic paste is ignored',async()=>{
 const prompt='First\n<img src=x onerror=alert(1)> & literal\nLast';const f=page({host:'www.kimi.ai',lexical:true,clipboardAccepted:false,prompt});
 const result=await f.run();assert.equal(result.ok,true,result.error);assert.equal(f.composer.innerText,prompt);assert.equal(f.counts().clickCount,1);
});

for(const host of ['gemini.google.com','www.kimi.com','www.kimi.ai']){
 test(host+' waits for semantic busy state even after stop buttons and text stop changing',async()=>{
  const f=page({host,semanticBusyUntil:4500});assert.equal((await f.run()).ok,true);assert.ok(f.clock()>=4500);assert.equal(f.events.at(-1).text,'Hello world');
 });
 test(host+' refresh recovers a confirmed reply without another submission',async()=>{
  const f=page({host,resume:{state:'submitted',turnKey:'provider:job'}});assert.equal((await f.run()).ok,true);
  assert.equal(f.counts().clickCount,0);assert.equal(f.counts().inputEvents,0);assert.equal(f.events.at(-1).text,'Hello world');
  const uncertain=page({host,resume:{state:'submitting'}});assert.equal((await uncertain.run()).ok,false);assert.equal(uncertain.counts().clickCount,0);
 });
 test(host+' cancellation does not report an incomplete answer as complete',async()=>{
  const f=page({host,cancelAt:1600});await f.run();assert.equal(f.events.some(e=>e.type==='done'),false);assert.equal(f.counts().clickCount,1);
 });
 test(host+' verifies its own submitted user turn and returns the completed reply',async()=>{
  const f=page({host,editable:true});assert.equal((await f.run()).ok,true);
  assert.equal(f.counts().clickCount,1);assert.equal(f.events.filter(e=>e.type==='submitted').length,1);assert.equal(f.events.at(-1).text,'Hello world');
 });
 test(host+' preserves literal tool JSON and never accepts a mismatched or still-generating turn',async()=>{
  const fenced=page({host,fencedReply:true});assert.equal((await fenced.run()).ok,true);assert.ok(fenced.events.at(-1).text.includes("$job='x'; Write-Output $job"));
  const wrong=page({host,wrongSubmission:true});assert.equal((await wrong.run()).ok,false);assert.equal(wrong.counts().clickCount,1);assert.equal(wrong.events.some(e=>e.type==='done'),false);
  const busy=page({host,completion:false});assert.equal((await busy.run()).ok,false);assert.equal(busy.events.some(e=>e.type==='done'),false);
 });
}

for(const host of ['www.kimi.ai','www.kimi.com'])test(host+' reports its capacity dialog without completing stale text or resubmitting',async()=>{
 const message='Too many people are chatting with Kimi; a subscription will grant you priority access.';
 const f=page({host,capacityNotice:message});const result=await f.run();
 assert.equal(result.ok,false);assert.match(result.error,/Too many people are chatting with Kimi/);
 assert.equal(f.counts().clickCount,1);assert.equal(f.events.some(e=>e.type==='done'),false);assert.ok(f.clock()<3000);
});
