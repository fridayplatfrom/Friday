// Public MCP Transport contract; used only between our proxy and upstream MCP.
export function memoryTransports(){
 const endpoints=[{},{}];
 for(let i=0;i<2;i++)Object.assign(endpoints[i],{async start(){},async send(message){if(this.closed)throw new Error('MCP transport closed');const peer=endpoints[1-i];queueMicrotask(()=>peer.onmessage?.(structuredClone(message)));},async close(){if(this.closed)return;this.closed=true;this.onclose?.();const peer=endpoints[1-i];if(!peer.closed){peer.closed=true;peer.onclose?.();}}});
 return endpoints;
}
