import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { BrowserBridge } from './bridge.mjs';
import { SITES, buildPrompt, nativeImagePrompt, ReplyDecoder, HARNESS_INTRODUCTION, INTRODUCTION_ACK, INTRODUCTION_VERSION } from './protocol.mjs';
import { DemoFormServer } from './demo-form.mjs';
import { BrowserDriver } from './browser-driver.mjs';
import { modelsHandler } from './models-route.mjs';
import { prepareContext } from './context.mjs';
import { localSessionTitle } from './session-title.mjs';
import { readNativeFile, captureNativeFiles, restoreNativeFiles } from './native-attachments.mjs';
import { FRIDAY_CONTEXT_WINDOW } from './native-compaction.mjs';
import { activeTools, requestControls, StopSequences, nativeFailure } from './adapter-compatibility.mjs';
import {failureDetails} from './diagnostics.mjs';
import {captureToolImages} from './activity.mjs';
import {providerHandoff,providerCheckpoint,confirmProvider} from './handoff.mjs';
import {sessionRecovery} from './session-recovery.mjs';

export const name = 'harness-browser-provider';
export const inject = ['llm'];
export const PROVIDER = 'browser-web';

export class BrowserAdapter {
  constructor(bridge, { introduction = true, contextWindow = FRIDAY_CONTEXT_WINDOW } = {}) {
    if(!Number.isSafeInteger(contextWindow)||contextWindow<16384||contextWindow>262144)throw new Error('Friday contextWindow must be an integer from 16384 to 262144.');
    this.bridge = bridge; this.introduction = introduction;this.contextWindow=contextWindow;
  }
  providerInfo(provider) { return { id: provider, name: 'Friday' }; }
  providerRetryPolicy() { return {mode:'normal',maxRetries:0,retryableCodes:['TIMEOUT'],initialDelayMs:500,maxDelayMs:10000,jitterRatio:0.1}; }
  imageRequestPricing() { return undefined; }
  imageRequestTarget(_p, _m, image) { return { width: image.width, height: image.height, maxBytes: image.bytes }; }
  async listModels(provider) { return Object.entries(SITES).map(([id, site]) => ({ provider, id, name: site.name, inputModalities: id==='chatgpt-web'?['text','image']:['text'] })); }
  async resolveModel(provider, model) {
    if (!Object.hasOwn(SITES, model)) throw new Error('Unknown browser website.');
    return { provider, id: model, name: SITES[model].name, inputModalities: model==='chatgpt-web'?['text','image']:['text'],
      context: { contextWindow: this.contextWindow }, defaultMaxTokens: 4096, systemPromptUpdate: 'in-history', toolUpdate:'in-history' };
  }
  async prepareCall(provider, model, signal) {
    signal?.throwIfAborted();
    const adapter=this;
    return { model: await this.resolveModel(provider, model), async *stream(options) {
      try { yield* adapter.stream({...options,signal:options.signal||signal}); }
      catch(error) { yield nativeFailure(error,options.signal||signal); }
    } };
  }
  async *stream(options) {
    try { yield* this.streamReply(options); }
    catch (error) {
      this.bridge.sessions?.update(options.sessionId || 'unscoped', {
        phase: options.signal?.aborted ? 'cancelled' : 'error', message: String(error.message).slice(0, 500), failureDetails:failureDetails(error),
        ...(this.bridge.sessions?.get(options.sessionId||'unscoped')?.pendingHandoff?{pendingHandoff:{...this.bridge.sessions.get(options.sessionId||'unscoped').pendingHandoff,status:options.signal?.aborted?'cancelled':'failed'}}:{}),
      });
      throw error;
    }
  }
  async *streamReply(options) {
    options=restoreNativeFiles(this.bridge,options);
    options.signal?.throwIfAborted();
    const title = localSessionTitle(options);
    if (title !== null) {
      yield { type: 'block-start', index: 0, blockType: 'text' };
      yield { type: 'text-delta', index: 0, text: title };
      yield { type: 'block-end', index: 0, block: { type: 'text', text: title } };
      yield { type: 'finish', reason: { kind: 'stop' } };
      return;
    }
    requestControls(options);
    this.bridge.sessions?.update(options.sessionId||'unscoped',{failureDetails:null});
    const lastTool=options.messages?.findLast(message=>message.role==='tool');
    if(lastTool){
      const text=(lastTool.content||[]).filter(block=>block.type==='text').map(block=>block.text).join('\n');
      if(lastTool.isError||/^Error:|^\[sandbox:/.test(text))this.bridge.sessions?.update(options.sessionId||'unscoped',{lastToolIssue:{...failureDetails(text),at:Date.now()}});
    }
    options={...options,tools:options.purpose==='compaction'?[]:activeTools(options)};
    const externalMessageId = this.bridge.twoWay?.take(options.sessionId, options.messages);
    const sessionId=options.sessionId||'unscoped';
    const lastHuman=options.messages?.findLast(message=>message.role==='user'&&message.source?.kind==='user');
    const websiteOrigin=!!externalMessageId||!!lastHuman?.source?.rpcId&&lastHuman.source.rpcId===this.bridge.sessions?.get(sessionId)?.webActiveId;
    const uploadFiles=websiteOrigin?[]:this.bridge.files?.list(sessionId).filter(file=>file.direction==='to-website'&&file.status==='ready')||[];
    let projected=options;
    if(options.messages?.some(message=>message.content?.some(block=>block.type==='image'||block.type==='file'))) {
      if(options.model!=='chatgpt-web')throw new Error('Native attachment transfer is currently supported only for the ChatGPT website. The attachment remains saved in Harness.');
      const messages=[];
      for(const message of options.messages){const content=[];for(const block of message.content||[]){
        if(block.type!=='image'&&block.type!=='file'){content.push(block);continue;}
        const sourceId=block.attachment?.attachmentId;if(!sourceId)throw new Error('Native attachment has no durable identity.');
        const fileKey=block.type==='file'?`${sourceId}:${block.attachment.name}`:null;
        let file=this.bridge.files.list(sessionId).find(file=>block.type==='file'?this.bridge.files.records[file.id].nativeFileId===fileKey:this.bridge.files.records[file.id].sourceId===sourceId);
        if(!file){
          if(block.type==='file'){
            if(!this.bridge.readFile)throw new Error('Harness native file service is unavailable. Nothing was submitted.');
            const bytes=await this.bridge.readFile(block.attachment,options.signal);
            file=this.bridge.files.put(sessionId,block.attachment.name,bytes);this.bridge.files.records[file.id].nativeFileId=fileKey;
          }else{
            if(!this.bridge.readImage)throw new Error('Harness native image service is unavailable. Nothing was submitted.');
            const image=await this.bridge.readImage(block.attachment,options.signal);const ext=image.mediaType==='image/jpeg'?'jpg':image.mediaType==='image/webp'?'webp':'png';file=this.bridge.files.put(sessionId,`screenshot-${sourceId.slice(-10)}.${ext}`,Buffer.from(image.data));this.bridge.files.records[file.id].sourceId=sourceId;
          }
          this.bridge.files.persist();
        }
        if(file.status==='ready'&&!uploadFiles.some(item=>item.id===file.id))uploadFiles.push(file);
        content.push({type:'text',text:`[${block.type==='file'?'File':'Image'} attachment: ${file.name}; ${file.status==='delivered'?'already uploaded in this paired conversation':'upload included with this request'}]`});
      }messages.push({...message,content});}projected={...options,messages};
    }
    if(uploadFiles.length&&(options.model!=='chatgpt-web'||this.bridge.controller))throw new Error('File uploads currently require the ChatGPT Chrome connector. Files remain staged; use manual upload for this provider.');
    if(uploadFiles.length>8)throw new Error('Attach at most eight files to one request. Remove extra staged files.');
    const imagePrompt = !options.purpose && options.model === 'chatgpt-web' ? nativeImagePrompt(options) : null;
    if(uploadFiles.length){projected={...projected,messages:[...(projected.messages||[]),{role:'user',source:{kind:'attachment-context'},content:[{type:'text',text:'The following actual file uploads accompany this request: '+uploadFiles.map(file=>`${file.name} (${file.size} bytes)`).join(', ')+'. Wait for their website processing; do not assume a file can be understood solely from its name.'}]}]};}
    const state=this.bridge.sessions?.get(sessionId);
    const handoff=externalMessageId||imagePrompt!==null?null:providerHandoff(state,projected);
    if(handoff){
      if(this.bridge.jobs?.size)throw new Error('Finish the active website request before switching models.');
      this.bridge.sessions?.update(sessionId,{activeProvider:handoff.from,pendingHandoff:{from:handoff.from,to:handoff.to,returning:handoff.returning,status:'connecting',at:handoff.at},phase:'waiting',message:`Preparing handoff to ${SITES[options.model].name}`});
      this.bridge.activity?.status(sessionId,'waiting',`Preparing handoff: ${SITES[handoff.from]?.name||handoff.from} → ${SITES[handoff.to].name}`);
    }
    const context=externalMessageId||imagePrompt!==null?null:prepareContext(projected,providerCheckpoint(state,options.model),{prefix:handoff?.prompt||''});
    const prompt = externalMessageId ? '' : imagePrompt ?? context.prompt;
    this.bridge.journal?.append(sessionId,'context',{messages:projected.messages,system:options.system,tools:options.tools,incremental:context?.incremental||false,transferParts:context?.parts?.length||0});
    if (!externalMessageId && imagePrompt === null && options.model === 'chatgpt-web' && this.introduction) {
      const sessionId = options.sessionId || 'unscoped';
      if (!this.bridge.sessions.introductionReady(sessionId, options.model, INTRODUCTION_VERSION)) {
        let reply = '';
        const introduction = this.bridge.controller ? HARNESS_INTRODUCTION.replace('A Chrome extension connects', 'A local browser bridge connects') : HARNESS_INTRODUCTION;
        for await (const event of this.bridge.request(options.model, introduction, options.signal,
          { sessionId, purpose: 'introduction' })) {
          if (event.type === 'snapshot' || event.type === 'done') reply = event.text;
        }
        if (reply.trim() !== INTRODUCTION_ACK) throw new Error('ChatGPT did not acknowledge the Harness introduction. No task was submitted; check the paired website and retry.');
        this.bridge.sessions.acknowledgeIntroduction(sessionId, options.model, INTRODUCTION_VERSION);
      }
    }
    for(const [index,part]of (context?.parts||[]).entries()) {
      let reply='';
      this.bridge.sessions?.update(sessionId,{phase:'waiting',message:`Transferring context ${index+1}/${context.parts.length} — no task actions yet`});
      this.bridge.journal?.append(sessionId,'context-part',{part:index+1,total:context.parts.length});
      for await(const event of this.bridge.request(options.model,part.prompt,options.signal,{sessionId,purpose:'context'})) {
        if(event.type==='snapshot'||event.type==='done')reply=event.text;
      }
      if(reply.trim()!==part.ack)throw new Error(`Friday context part ${index+1}/${context.parts.length} was not acknowledged. No local tool was executed from this transfer. Retry or use Harness Compact.`);
    }
    // Image-only requests never authorize Harness tool execution from website text.
    const decoderOptions={allowTextRewrites:true,bufferedRewrites:true,holdTextChars:256};
    let decoder = new ReplyDecoder(imagePrompt === null ? options.tools || [] : [],decoderOptions); let started = false; const images = []; const files=[];
    let block; let recoveryError;
    for (let attempt = 0; attempt < 2; attempt++) {
    const stops=new StopSequences(options.stop);
    const requestPrompt = attempt ? `Friday connector feedback — this turn failed\n${recoveryError}\n\nHarness executed NOTHING from that reply. The error above is connector feedback about the format of your previous reply. Correct that reply now: return HARNESS_TOOL_CALL followed by a json code fence containing one COMPLETE JSON object with name and arguments, using the most recently supplied tool catalog and the same human task. The fence preserves literal dollars and command characters. Do not return the prefix alone. You may choose another available tool or approach if appropriate. Do not claim execution or repeat an operation whose completion was already confirmed. If you cannot provide a valid call, explain the blocker in ordinary text.` : prompt;
    for await (const event of this.bridge.request(options.model, requestPrompt, options.signal, { sessionId: options.sessionId || 'unscoped', purpose:imagePrompt!==null?'image':'task', externalMessageId: attempt ? null : externalMessageId,attachments:attempt||externalMessageId?[]:uploadFiles })) {
      if(event.type==='file'){files.push(event.file);continue;}
      if (event.type === 'image') { images.push(event.image); continue; }
      if (!['snapshot', 'done'].includes(event.type)) continue;
      const delta = decoder.push(stops.push(event.text,event.type==='done'));
      if(decoder.rewritten&&event.type!=='done')this.bridge.sessions?.update(sessionId,{phase:'receiving',message:'Website updated its reply — waiting for the final text'});
      if (delta) {
        if (!started) { yield { type: 'block-start', index: 0, blockType: 'text' }; started = true; }
        yield { type: 'text-delta', index: 0, text: delta };
      }
      if(stops.matched){
        this.bridge.sessions?.update(sessionId,{phase:'complete',message:'Stopped at the requested stop sequence'});
        this.bridge.journal?.append(sessionId,'stop-sequence',{});
        break;
      }
    }
    if (images.length||files.length) {
      const attachments = images.map(image => {
        const path=this.bridge.sessions.imagePath?.(image.id);
        return `\n\n![Generated image](${path?'<'+path.replace(/\\/g,'/')+'>':image.url})`;
      }).join('')+files.map(file=>`\n\n[Download ${file.name.replace(/[\[\]]/g,'')}](${this.bridge.harnessOrigin||''}${file.url})`).join('');
      const delta = decoder.push(decoder.text + attachments);
      if (!started) { yield { type: 'block-start', index: 0, blockType: 'text' }; started = true; }
      if (delta) yield { type: 'text-delta', index: 0, text: delta };
    }
    try { block = decoder.finish(); break; }
    catch (error) {
      if (attempt || started || stops.matched || images.length || imagePrompt !== null || !/^(Incomplete browser tool-request prefix\.|Invalid tool-request JSON; nothing executed\.|Misplaced browser tool-request prefix; nothing executed\.)$/.test(error.message)) throw error;
      recoveryError = error.message;
      decoder = new ReplyDecoder(options.tools || [],decoderOptions);
      this.bridge.sessions?.update(options.sessionId || 'unscoped', { phase: 'waiting', message: 'Correcting an incomplete tool request — no action executed' });
    }
    }
    if(context){
      if(options.purpose)this.bridge.sessions?.update(sessionId,{contextCheckpoint:context.checkpoint});
      else confirmProvider(this.bridge.sessions,sessionId,options.model,context.checkpoint,handoff);
    }
    if (block.type === 'tool-call'||block.type==='tool-calls') {
      const blocks=block.type==='tool-calls'?block.blocks:[block];
      for(const [index,call] of blocks.entries()){
        yield { type: 'block-start', index, blockType: 'tool-call' };
        yield { type: 'tool-call-delta', index, id: call.id, name: call.name, argumentsDelta: call.arguments };
        yield { type: 'block-end', index, block:call };
      }
      yield {type:'finish',reason:{kind:'tool-calls'}};
      return;
    } else if (!started) {
      yield { type: 'block-start', index: 0, blockType: 'text' };
      yield { type: 'text-delta', index: 0, text: block.text };
    }
    yield { type: 'block-end', index: 0, block };
    // Website DOM does not expose authoritative token usage. Do not fabricate it.
    yield { type: 'finish', reason: { kind: 'stop' } };
  }
}

export async function apply(ctx, config = {}) {
  if(config.workspaceBrowser){const {installWorkspaceBrowser}=await import('./workspace-browser-control.mjs');installWorkspaceBrowser(ctx);}
  const configFile = config.connectionFile || join(homedir(), '.dsh', 'browser-connector', 'connection.json');
  const connection = JSON.parse(readFileSync(configFile, 'utf8'));
  const controller = config.browserMode === 'builtin' ? new BrowserDriver() : null;
  const bridge = await new BrowserBridge({ token: connection.token, port: connection.port || 8766, controller,autoTwoWay:true,transportMode:config.browserMode==='shared'?'shared-browser':'extension',
    downloadDirectory:config.downloadDirectory,
    stateDirectory: join(homedir(), '.dsh', 'browser-connector', 'sessions') }).start();
  ctx.on('dispose', () => bridge.close());
  if(config.workspaceBrowser){const {browserControl}=await import('./workspace-browser-control.mjs');bridge.workspaceBrowser=async(action,input)=>{const agent=bridge.resolveAgent?.(input.sessionId),directory=agent?.session?.header?.cwd;if(!directory)throw new Error('Open the native workspace conversation first.');return browserControl(action,{...input,directory});};}
  ctx.inject(['webServer', 'connection'], scope => {
    scope.on('webserver/index-inject', table => table.push({ kind: 'script', placement: 'body-end',
      text: readFileSync(new URL('./recovery-client.js', import.meta.url), 'utf8') }));
    scope.effect(() => scope.webServer.register({ kind: 'prefix', path: '/browser-models',
      handler: modelsHandler(scope.connection, bridge) }));
  });
  if (config.demoForm) {
    const demo = await new DemoFormServer().start();
    ctx.on('dispose', () => demo.close());
  }
  ctx.llm.registerAdapter([PROVIDER], new BrowserAdapter(bridge,{contextWindow:config.contextWindow}));
  // Observe committed native facts. Never intercept, approve, or re-execute a tool.
  ctx.on('session/event',(session,event)=>{
    if(config.workspaceBrowser&&event.type==='tool/result'){
      const id=event.data?.message?.toolCallId||event.data?.message?.callId,directory=session.header?.cwd;
      if(id&&directory)void import('./workspace-browser-control.mjs').then(({browserControl})=>browserControl('acknowledge',{id,sessionId:session.id,directory,success:!event.data.message.isError})).catch(error=>ctx.logger.warn('Friday browser receipt acknowledgement: '+error.message));
    }
    if(!bridge.sessions.get(session.id))return;
    try {
      if(bridge.agui.active(session.id)||event.type==='turn/start'&&bridge.resolveAgent?.(session.id)?.session?.requestHeader?.()?.config?.provider===PROVIDER)bridge.agui.native(session.id,event);
    } catch(error) { ctx.logger.warn('Friday AG-UI projection: '+String(error.message)); }
    try {
      if(bridge.activity.native(session.id,event))void captureToolImages(bridge,session.id,event).catch(error=>
        bridge.activity.emit(session.id,'CUSTOM',{name:'friday.preview-warning',value:{message:String(error.message).slice(0,300)}}));
    } catch(error) { ctx.logger.warn('Friday activity projection: '+String(error.message)); }
  });
  ctx.inject(['attachments'],scope=>scope.effect(()=>{bridge.readImage=(ref,signal)=>scope.attachments.readImageRequest(ref,{width:ref.width,height:ref.height,maxBytes:16*1024*1024},signal);bridge.readFile=(ref,signal)=>readNativeFile(scope.attachments,ref,signal);return()=>{bridge.readImage=null;bridge.readFile=null;};}));
  ctx.on('llm/stream', (options, next) => { bridge.twoWay.validateRoute(options);captureNativeFiles(bridge,options,ctx.llm);
    try{if(options.provider===PROVIDER&&!options.purpose&&bridge.resolveAgent?.(options.sessionId)?.status==='running')bridge.agui.ensure(options.sessionId);}catch(error){ctx.logger.warn('Friday AG-UI admission projection: '+String(error.message));}
    return next(); });
  ctx.on('agent/assistant-stream',({agent,frame})=>{
    try{bridge.agui.stream(agent.id,frame);}catch(error){ctx.logger.warn('Friday AG-UI stream: '+String(error.message));}
  });
  ctx.inject(['agents'], scope => {
    scope.effect(() => { bridge.resolveAgent = id => scope.agents.get(id); return () => { bridge.resolveAgent = null; }; });
  });
  ctx.inject(['sessionController'], scope => {
    scope.effect(() => {
      bridge.recoverSession = sessionRecovery(bridge, scope.sessionController);
      return () => { bridge.recoverSession = null; };
    });
  });
  // Start in the background so a website outage cannot block the Harness UI.
  if (controller) void controller.start();
}
export default { name, inject, apply };
