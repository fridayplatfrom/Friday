// Renderer coordinates are accepted only for a known provider in the active session.
export function dockBounds(input, sessionId, width, height) {
 if (!input || input.sessionId !== sessionId || !/^session-[a-f0-9-]{36}$/i.test(sessionId || '') ||
     !['chatgpt-web','gemini-web','deepseek-web','kimi-web'].includes(input.site) ||
     typeof input.tabId !== 'string' || input.tabId.length > 200) return null;
 if (input.visible !== true) return {visible:false};
 const {x,y,width:w,height:h}=input;
 if (![x,y,w,h].every(Number.isFinite) || x<0 || y<0 || w<1 || h<1 || x+w>width+1 || y+h>height+1) return null;
 return {visible:true,x:Math.ceil(x),y:Math.ceil(y),width:Math.max(1,Math.floor(w)-1),height:Math.max(1,Math.floor(h)-1)};
}
