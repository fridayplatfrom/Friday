export function requestControls(options) {
  if(options.temperature!==undefined)throw Object.assign(new Error('Friday cannot set website sampling temperature. Remove temperature from this route configuration.'),{code:'UNSUPPORTED_CALL_CONTROL'});
  if(options.reasoningEffort!==undefined)throw Object.assign(new Error('Friday cannot guarantee website reasoning effort. Select the mode on the website; no effort is advertised by this adapter.'),{code:'UNSUPPORTED_REASONING_EFFORT'});
  if(options.maxTokens!==undefined&&(!Number.isSafeInteger(options.maxTokens)||options.maxTokens<1))throw Object.assign(new Error('maxTokens must be a positive integer.'),{code:'INVALID_REQUEST'});
  if(options.stop!==undefined&&(!Array.isArray(options.stop)||options.stop.length>16||options.stop.some(s=>typeof s!=='string'||!s.length||s.length>1024)))throw Object.assign(new Error('stop must contain at most 16 non-empty strings, each at most 1024 characters.'),{code:'INVALID_REQUEST'});
  return {...(options.purpose?{purpose:options.purpose}:{}),...(options.maxTokens?{maxTokens:options.maxTokens,maxTokensEnforcement:'advisory; website token counts are unavailable'}:{}),...(options.stop?.length?{stop:options.stop,stopEnforcement:'local exact string matching'}:{})};
}

export function messageSource(source) {
  if(!source)return undefined;
  const {replayState,...publicSource}=source;return publicSource;
}

/** Resolve only active schemas, never historical/deferred definitions supplied for replay. */
export function activeTools(options) {
  const history=options.toolHistory;
  if(!history)return options.tools||[];
  const ids=new Set((options.messages||[]).filter(m=>m.role==='developer').map(m=>m.id));
  if(history.updates.some(update=>!ids.has(update.messageId)))return options.tools||[];
  const active=new Map(history.tools.filter(tool=>!tool.deferLoading).map(tool=>[tool.name,tool]));
  for(const message of options.messages||[]) {
    if(message.role!=='developer')continue;
    const update=history.updates.find(update=>update.messageId===message.id);
    for(const block of message.content||[]) {
      if(block.type==='tool-removal')active.delete(block.toolName);
      if(block.type==='tool-addition'){
        const schema=update?.additions.find(tool=>tool.name===block.toolName);
        if(schema)active.set(schema.name,schema);
      }
    }
  }
  return [...active.values()].map(({deferLoading,...schema})=>schema);
}

/** Buffer only a possible stop-string suffix so markers never leak as deltas. */
export class StopSequences {
  constructor(stops=[]){this.stops=stops;this.matched=false;this.text='';}
  push(snapshot,final=false){
    if(this.matched)return this.text;
    let at=Infinity;
    for(const stop of this.stops){const index=snapshot.indexOf(stop);if(index>=0)at=Math.min(at,index);}
    if(at!==Infinity){this.matched=true;this.text=snapshot.slice(0,at);return this.text;}
    let hold=0;
    if(!final)for(const stop of this.stops)for(let n=Math.min(stop.length-1,snapshot.length);n>hold;n--)if(snapshot.endsWith(stop.slice(0,n))){hold=n;break;}
    this.text=hold?snapshot.slice(0,-hold):snapshot;return this.text;
  }
}

export function nativeFailure(error,signal) {
  const aborted=signal?.aborted||error?.name==='AbortError';
  const code=aborted?'ABORTED':error?.code==='FRIDAY_CONTEXT_LIMIT'?'CONTEXT_WINDOW_EXCEEDED':error?.code||'FRIDAY_WEBSITE_ERROR';
  return {type:'finish',reason:{kind:aborted?'aborted':'error',failure:{message:String(error?.message||'Website request failed'),code}}};
}
